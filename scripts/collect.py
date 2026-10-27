#!/usr/bin/env python3
"""Code-only collection into separate platform databases. Exit 2 means partial."""
import argparse
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit
from lite import ROOT, acquire, dump, export, now, parse_feed, request, crawl, body_quality, canonical
from sources import load_config, source_configs, opencli_command, call_opencli, social_item, note_text
from storage import PlatformStore, processed_ids, context_directory, scoring_hash
from run_skills import context_hash


def collect(home, sources, output, body_limit=10, crawl_python=None, context_dir=None):
    home = Path(home).resolve()
    if Path(output).exists():
        raise FileExistsError('Use a new snapshot path; do not overwrite previous input')
    if type(body_limit) is not int or not 1 <= body_limit <= 10:
        raise ValueError('body_limit must be 1..10')
    started = now()
    configs = list(source_configs(sources))
    for kind, source in configs:
        if kind == 'opencli': opencli_command(source)
    rules = load_config(ROOT / 'config/keywords.json')
    ctx, _ = context_hash(context_directory(context_dir))
    processed = processed_ids(home, ctx)
    stores, summary = {}, []
    try:
        # Empty, explicitly disabled platforms don't get a database or any network calls.
        for kind, source in configs:
            platform = source['site'] if kind == 'opencli' else 'urls' if kind == 'url' else 'rss'
            if platform not in stores: stores[platform] = PlatformStore(home, platform)
            store = stores[platform]
            result = {'id': source['id'], 'platform': platform, 'kind': kind, 'status': 'ok',
                      'new': 0, 'duplicate': 0, 'items': 0, 'item_errors': []}
            try:
                if kind == 'rss':
                    limit = source.get('limit',2)
                    if type(limit) is not int or not 1 <= limit <= 10: raise ValueError('RSS limit must be 1..10')
                    raw = request(source['url']); raw_path = store.raw(raw,'xml')
                    items = parse_feed(raw,source['url'])[:limit]
                elif kind == 'url':
                    raw_path = store.raw(json.dumps(source),'json'); items = [source]
                else:
                    rows, raw_path = call_opencli(store,opencli_command(source))
                    items = rows[:source.get('limit',2)]
                for value in items:
                    mid = None
                    try:
                        item = social_item(platform,value) if kind == 'opencli' else value
                        mid, fresh = store.item(item,source['id'],raw_path,rules)
                        result['new' if fresh else 'duplicate'] += 1; result['items'] += 1
                        if kind == 'opencli':
                            store.platform_item(mid,item,value)
                        if platform == 'xiaohongshu':
                            row = store.db.execute('SELECT * FROM materials WHERE id=?',(mid,)).fetchone()
                            if not store.cached(row):
                                # Original signed URL stays inside this code call and local raw archive only.
                                details, detail_path = call_opencli(store,['opencli','xiaohongshu','note',item['url'],'-f','json'])
                                text = note_text(details)
                                if not body_quality(text,'platform_text_unverified')[0]:
                                    raise ValueError('No usable note text; images/video are not transcribed')
                                store.body(mid,text,'opencli','platform_text_unverified')
                                store.attempt(mid,'opencli:note','ok','public platform text; unverified coverage',detail_path)
                    except Exception as error:
                        store.db.rollback()
                        if mid:
                            store.attempt(mid,'opencli:note' if platform == 'xiaohongshu' else 'parse','failed',type(error).__name__)
                        result['item_errors'].append(f'{type(error).__name__}: {error}')
                if result['item_errors']: result['status'] = 'partial' if result['items'] else 'failed'
            except Exception as error:
                result['status'] = 'failed'; result['error'] = f'{type(error).__name__}: {error}'
            summary.append(result)
        bodies, remaining, platform_bodies = {'succeeded':0,'failed':0}, body_limit, {}
        for platform, store in stores.items():
            if platform not in ('rss','urls','hackernews'): continue
            pending = [r for r in store.db.execute('SELECT * FROM materials ORDER BY discovered_at,id') if not store.cached(r)]
            for row in pending[:remaining]:
                # Public URL feeds can also mention social posts: don't send their signatures to Reader.
                if urlsplit(row['url']).hostname in ('www.xiaohongshu.com','xiaohongshu.com','x.com','twitter.com','www.tiktok.com'):
                    continue
                state = acquire(store,row,[('jina',lambda url:request('https://r.jina.ai/'+url).decode('utf-8')),
                                           ('crawl4ai',lambda url:crawl(url,crawl_python or sys.executable))])
                bodies[state] = bodies.get(state,0)+1; remaining -= 1
                counts = platform_bodies.setdefault(platform,{'succeeded':0,'failed':0})
                counts[state] = counts.get(state,0)+1
        by_id = {}
        for platform, store in stores.items():
            for item in export(store)['materials']:
                if (item['id'],item.get('body_sha256') or '') in processed: continue
                item['url'] = canonical(item['url'])
                item['platform'] = platform
                item['source_db'] = str(store.db_path.relative_to(home))
                for observation in item['observations']:
                    observation['source_db'] = item['source_db']
                item['source_databases'] = [item['source_db']]
                metadata = store.db.execute('SELECT platform_item_id,author,content_type,metrics_json '
                                            'FROM platform_items WHERE material_id=?',(item['id'],)).fetchone()
                if metadata:
                    item['platform_metadata'] = dict(metadata)
                    item['platform_metadata']['metrics'] = json.loads(item['platform_metadata'].pop('metrics_json'))
                # Keep raw response references, not the response payload or temporary access URLs.
                previous = by_id.get(item['id'])
                if previous:
                    refs = previous['source_databases'] + item['source_databases']
                    observations = previous['observations'] + item['observations']
                    if item['body'] and not previous['body']:
                        by_id[item['id']] = item
                    by_id[item['id']]['source_databases'] = refs
                    by_id[item['id']]['observations'] = observations
                else:
                    by_id[item['id']] = item
        materials = list(by_id.values())
        failures = sum(s['status'] != 'ok' for s in summary) + bodies['failed']
        successes = sum(s['status'] != 'failed' for s in summary)
        status = 'failed' if not successes else 'partial' if failures else 'ok'
        snapshot = {'exported_at':now(),'data_home':str(home),'context_sha256':ctx,'scoring_sha256':scoring_hash(),'materials':materials,
                    'collection':{'status':status,'sources':summary,'bodies':bodies,
                                  'scope':'unprocessed material versions for this context; source dates may be older or unknown'}}
        dump(output,snapshot)
        for platform,store in stores.items():
            store.receipt('collect',started,{'succeeded':sum(s['status']!='failed' for s in summary if s['platform']==platform),
                                           'failed':sum(s['status']!='ok' for s in summary if s['platform']==platform)+platform_bodies.get(platform,{}).get('failed',0),
                                           'bodies':platform_bodies.get(platform,{}),
                                           'platform':platform,'snapshot':str(output)})
        print(json.dumps({'status':status,'materials':len(materials),'sources':summary,'bodies':bodies},ensure_ascii=False,indent=2))
        return 1 if status == 'failed' else 2 if status == 'partial' else 0
    finally:
        for store in stores.values(): store.db.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home',default=str(ROOT/'data/daily'))
    parser.add_argument('--sources',default=str(ROOT/'config/sources'))
    parser.add_argument('--out',required=True)
    parser.add_argument('--context')
    parser.add_argument('--preview',action='store_true')
    args=parser.parse_args()
    if args.preview:
        for kind,source in source_configs(args.sources):
            print(kind,source['id'],opencli_command(source) if kind=='opencli' else source['url'])
        return 0
    runtime=load_config(ROOT/'config/runtime.json')
    return collect(args.home,args.sources,args.out,runtime.get('body_limit',10),runtime.get('crawl_python'),args.context)


if __name__=='__main__': sys.exit(main())
