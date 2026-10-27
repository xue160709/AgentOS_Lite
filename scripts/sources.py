"""Configuration and bounded read-only source adapters."""
import json
from pathlib import Path
import subprocess
import re
import time
from urllib.parse import urlsplit
from lite import MAX_BYTES, public_url

_LAST_CALL = {}


def load_config(path):
    path = Path(path)
    local = path.with_name(path.stem + '.local.json')
    return json.loads((local if local.exists() else path).read_text(encoding='utf-8'))


def source_configs(directory):
    directory = Path(directory)
    groups = [('rss', directory / 'rss.json'), ('url', directory / 'urls.json')]
    groups += [('opencli', p) for p in sorted((directory / 'opencli').glob('*.json'))
               if not p.name.endswith('.local.json')]
    seen = set()
    for kind, path in groups:
        for source in load_config(path)['sources']:
            if not isinstance(source.get('enabled'), bool):
                raise ValueError(f'{path}: enabled must be boolean')
            if not isinstance(source.get('id'), str) or not source['id'] or source['id'] in seen:
                raise ValueError(f'{path}: missing or duplicate source id')
            seen.add(source['id'])
            if source['enabled']:
                yield kind, source


def opencli_command(source):
    site, action = source.get('site'), source.get('command')
    allowed = {('xiaohongshu', 'search'): {'sort': {'comprehensive','latest','most-liked','most-commented','most-collected'},
                'publish-time': {'anytime','day','week','half-year'}, 'note-type': {'all','video','image'}},
               ('twitter', 'search'): {'product': {'top','live','photos','videos'}},
               ('tiktok', 'search'): {},
               ('hackernews', 'top'): {}, ('hackernews', 'newest'): {}}
    if (site, action) not in allowed:
        raise ValueError('Only public search and Hacker News top/newest are supported')
    limit = source.get('limit', 2)
    if type(limit) is not int or not 1 <= limit <= 5:
        raise ValueError('OpenCLI limit must be 1..5')
    command = ['opencli', site, action]
    if action == 'search':
        query = source.get('query')
        if not isinstance(query, str) or not query.strip() or query.startswith('-') or len(query) > 300:
            raise ValueError('Search query must be 1..300 characters and not an option')
        command.append(query)
    command += ['--limit', str(limit)]
    for key, value in source.get('options', {}).items():
        if key not in allowed[(site, action)] or value not in allowed[(site, action)][key]:
            raise ValueError(f'Unsupported read-only search option: {key}')
        command += ['--' + key, value]
    return command + ['-f', 'json']


def call_opencli(store, command):
    site = command[1]
    interval = 10 if site == 'xiaohongshu' else 2
    wait = interval - (time.monotonic() - _LAST_CALL.get(site, 0))
    if wait > 0:
        time.sleep(wait)
    _LAST_CALL[site] = time.monotonic()
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=80)
    except subprocess.TimeoutExpired as error:
        for output in (error.stdout, error.stderr):
            if output:
                store.raw(output, 'txt')
        raise RuntimeError('OpenCLI timed out after 80 seconds') from error
    raw_path = store.raw(result.stdout, 'json')
    store.raw(result.stderr, 'txt')
    # OpenCLI's documented sysexits contract: 66 means an empty result, not a failed bridge.
    if result.returncode == 66:
        return [], raw_path
    if result.returncode:
        raise RuntimeError(f'OpenCLI exit {result.returncode}; inspect local raw response {raw_path}')
    if len(result.stdout.encode()) > MAX_BYTES:
        raise ValueError('OpenCLI response exceeds 2 MB')
    value = json.loads(result.stdout)
    if isinstance(value, dict):
        if value.get('ok') is False:
            raise RuntimeError('OpenCLI returned an error: ' + str(value.get('error', {}).get('code', 'unknown')))
        value = value.get('data', value.get('items'))
    if not isinstance(value, list):
        raise ValueError('Unexpected OpenCLI JSON shape')
    return value, raw_path


def social_item(site, row):
    url = row.get('url')
    if not url and site == 'hackernews' and row.get('id'):
        url = f"https://news.ycombinator.com/item?id={row['id']}"
    if not isinstance(url, str):
        raise ValueError('Source item has no URL')
    public_url(url)
    hosts = {'xiaohongshu': {'www.xiaohongshu.com','xiaohongshu.com'},
             'twitter': {'x.com','www.x.com','twitter.com','www.twitter.com'},
             'tiktok': {'www.tiktok.com','tiktok.com'},
             'hackernews': None}
    if site not in hosts or (hosts[site] is not None and urlsplit(url).hostname not in hosts[site]):
        raise ValueError('Unexpected platform URL host')
    text = row.get('text', '') if site == 'twitter' else row.get('desc','') if site == 'tiktok' else ''
    patterns = {'xiaohongshu': r'/(?:search_result|explore|discovery/item)/([0-9a-fA-F]{24})',
                'twitter': r'/status/(\d+)', 'tiktok': r'/video/(\d+)'}
    found = re.search(patterns.get(site, r'(?!)'), url)
    item_id = str(row.get('id') or (found.group(1).lower() if found else ''))
    if site != 'hackernews' and not item_id:
        raise ValueError('Cannot identify platform post ID')
    return {'url': url, 'title': row.get('title') or text[:120] or '(untitled post)',
            'published': row.get('created_at') or row.get('published_at'),
            'source_item_id': item_id, 'body': text,
            'identity_key': site + ':' + item_id if item_id else url,
            'content_type': 'video_description' if site == 'tiktok' else 'post_text',
            'scope': 'platform_text_unverified' if text else 'metadata_only'}


def note_text(rows):
    fields = {str(row.get('field', '')).lower(): row.get('value') for row in rows}
    # Adapter versions use localized field labels. Never treat engagement counts as prose.
    text = next((fields[k] for k in ('desc','description','content','text','正文','内容') if isinstance(fields.get(k), str)), '')
    return text
