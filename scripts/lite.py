#!/usr/bin/env python3
"""Small explicit collection pipeline. Standard library except optional Crawl4AI."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import html
import ipaddress
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode, urljoin
from urllib.request import Request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 2_000_000


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def canonical(url):
    p = urlsplit(url.strip())
    if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
        raise ValueError('Only HTTP(S) URLs without credentials are accepted')
    if p.port not in (None, 80 if p.scheme == 'http' else 443):
        raise ValueError('Only standard HTTP(S) ports are accepted')
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
             if not k.lower().startswith('utm_') and k.lower() not in ('fbclid', 'gclid')]
    host = p.hostname.lower()
    if ':' in host:
        host = '[' + host + ']'
    # Preserve protocol and path semantics; discard fragments and tracking only.
    return urlunsplit((p.scheme.lower(), host, p.path or '/', urlencode(query), ''))


def public_url(url):
    """Reject explicit local URLs; not a sandbox or complete SSRF defense.

    DNS can be synthesized by a local network proxy, so do not classify resolved
    proxy addresses as the destination. Use only with reviewed public URLs.
    """
    canonical(url)
    host = urlsplit(url).hostname
    if host == 'localhost' or host.endswith(('.localhost', '.local')):
        raise ValueError('Local destinations are not supported')
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return
    if not address.is_global:
        raise ValueError('Private/local IP literals are not supported')


def request(url):
    # Resolve and validate redirects ourselves before sending the next request.
    from urllib.request import build_opener, HTTPRedirectHandler
    from urllib.error import HTTPError
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener = build_opener(NoRedirect)
    for _ in range(5):
        public_url(url)
        try:
            with opener.open(Request(url, headers={'User-Agent': 'AgentOS-Lite/1.0 (teaching sample)'}), timeout=20) as r:
                raw = r.read(MAX_BYTES + 1)
                if len(raw) > MAX_BYTES:
                    raise ValueError('Response exceeds 2 MB; not silently truncated')
                return raw
        except HTTPError as e:
            if e.code in (301, 302, 303, 307, 308) and e.headers.get('Location'):
                url = urljoin(url, e.headers['Location'])
                continue
            raise
    raise ValueError('Too many redirects')


def text_only(value):
    value = re.sub(r'<(script|style)\b[^>]*>.*?</\1>', '', value, flags=re.S | re.I)
    value = re.sub(r'</(?:p|div|li|h[1-6])\s*>|<br\s*/?>', '\n', value, flags=re.I)
    return html.unescape(re.sub(r'<[^>]+>', ' ', value)).strip()


def quality(text):
    if re.match(r'\s*(?:<!doctype\s+html\b[^>]*>\s*)?<html(?:\s|>)', text, flags=re.I):
        return False, 'HTML document returned instead of extracted prose'
    lower = text.lower()
    bad = ('verify you are human', 'checking your browser', 'access denied',
           'enable javascript and cookies', 'captcha', 'page not found',
           'subscribe to continue', 'sign in to continue')
    # Conservative: false rejection is pending, never quietly accepted as full text.
    if any(x in lower for x in bad):
        return False, 'challenge/login/error marker; manual review required'
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    prose = [x for x in lines if len(x) >= 70 and not x.startswith(('![', '|'))]
    if len(text.strip()) < 300 or len(prose) < 2:
        return False, 'too short or too little prose (minimum 300 chars, 2 prose lines)'
    if len(set(lines)) < 2:
        return False, 'repeated boilerplate'
    return True, 'heuristic pass; extraction coverage not independently verified'


def prefilter(title, body, rules):
    hay = (title + '\n' + body).casefold()
    hits = [w for w in rules['include'] if w.casefold() in hay]
    exclusions = [w for w in rules['exclude_hints'] if w.casefold() in hay]
    return {'state': 'candidate' if hits else 'needs_review', 'include_hits': hits,
            'exclude_hints': exclusions, 'reason': 'Hints only; no automatic semantic exclusion'}


def parse_feed(raw, base):
    root = ET.fromstring(raw)
    if root.tag not in ('rss', '{http://www.w3.org/2005/Atom}feed'):
        raise ValueError('Not an RSS or Atom feed')
    entries = root.findall('./channel/item')
    if not entries:
        entries = root.findall('{http://www.w3.org/2005/Atom}entry')
    rows = []
    def get(node, names):
        for name in names:
            found = node.find(name)
            if found is not None:
                return ''.join(found.itertext()).strip()
        return ''
    for node in entries:
        atom = '{http://www.w3.org/2005/Atom}'
        url = get(node, ['link'])
        if not url:
            links = node.findall(atom + 'link')
            url = next((x.get('href', '') for x in links if x.get('rel', 'alternate') == 'alternate'), '')
        encoded = get(node, ['{http://purl.org/rss/1.0/modules/content/}encoded', atom + 'content'])
        summary = get(node, ['description', atom + 'summary'])
        rows.append({'url': urljoin(base, url) if url else '', 'title': get(node, ['title', atom + 'title']) or '(untitled)',
                     'source_item_id': get(node, ['guid', atom + 'id']),
                     'published': get(node, ['pubDate', atom + 'published', atom + 'updated']) or None,
                     'body': text_only(encoded), 'summary': text_only(summary),
                     'scope': 'feed_claimed_full' if encoded else 'metadata_only'})
    return rows


class Store:
    def __init__(self, home):
        self.last_status = 'ok'
        self.home = Path(home).resolve()
        self.home.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.home / 'library.sqlite')
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript((ROOT / 'scripts/schema.sql').read_text())

    def raw(self, content, suffix='txt'):
        raw = content if isinstance(content, bytes) else content.encode()
        path = Path('raw') / (digest(raw) + '.' + suffix)
        target = self.home / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and digest(target.read_bytes()) != digest(raw):
            raise ValueError('Raw archive integrity mismatch; preserve for manual investigation')
        if not target.exists():
            target.write_bytes(raw)
        return str(path)

    def item(self, item, source, raw_path, rules):
        url = canonical(item['url'])
        mid = digest(url)[:20]
        fresh = self.db.execute('SELECT 1 FROM materials WHERE id=?', (mid,)).fetchone() is None
        self.db.execute('INSERT OR IGNORE INTO materials(id,url,title,published,discovered_at,updated_at,prefilter) '
                        'VALUES(?,?,?,?,?,?,?)', (mid, url, item['title'], item.get('published'), now(), now(),
                         json.dumps(prefilter(item['title'], item.get('body', '') + item.get('summary', ''), rules))))
        self.db.execute('INSERT OR IGNORE INTO observations(material_id,source,source_item_id,observed_at,published,raw_path) '
                        'VALUES(?,?,?,?,?,?)', (mid, source, item.get('source_item_id'), now(), item.get('published'), raw_path))
        # Only declared full content is eligible for reuse, never RSS description or HN title.
        existing = self.db.execute('SELECT * FROM materials WHERE id=?', (mid,)).fetchone()
        if (not self.cached(existing) and item.get('scope') in ('fixture_full', 'feed_claimed_full')
                and item.get('body') and quality(item['body'])[0]):
            self.body(mid, item['body'], 'feed' if source != 'fixture' else 'fixture', item['scope'])
        self.db.commit()
        return mid, fresh

    def cached(self, row):
        if row['body_status'] != 'ok' or not row['body_path']:
            return False
        p = self.home / row['body_path']
        return p.is_file() and digest(p.read_bytes()) == row['body_sha256'] and quality(p.read_text())[0]

    def body(self, mid, text, method, scope):
        sha = digest(text)
        row = self.db.execute('SELECT * FROM materials WHERE id=?', (mid,)).fetchone()
        if row['body_sha256'] == sha:
            self.db.execute("UPDATE materials SET body_status='ok' WHERE id=?", (mid,))
            return
        version = row['body_version'] + 1
        path = self.raw(text, 'md')
        self.db.execute('INSERT INTO body_versions VALUES(?,?,?,?,?,?,?)',
                        (mid, version, sha, path, method, scope, now()))
        self.db.execute("UPDATE materials SET body_status='ok',body_path=?,body_sha256=?,body_method=?,"
                        'body_scope=?,body_version=?,updated_at=? WHERE id=?',
                        (path, sha, method, scope, version, now(), mid))

    def attempt(self, mid, method, status, detail, raw_path=None):
        self.db.execute('INSERT INTO attempts(material_id,method,attempted_at,status,detail,raw_path) VALUES(?,?,?,?,?,?)',
                        (mid, method, now(), status, str(detail)[:800], raw_path))
        self.db.commit()

    def receipt(self, command, started, summary):
        rid = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        failures = summary.get('failed', 0)
        successes = summary.get('succeeded', 0) + summary.get('reused', 0)
        status = 'partial' if failures and successes else 'failed' if failures else 'ok'
        self.last_status = status
        report = {'id': rid, 'command': command, 'started_at': started, 'ended_at': now(),
                  'status': status, **summary}
        self.db.execute('INSERT INTO runs VALUES(?,?,?,?,?,?)',
                        (rid, command, started, report['ended_at'], status, json.dumps(summary, ensure_ascii=False)))
        self.db.commit()
        dump(self.home / 'receipts' / (rid + '.json'), report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return report


def crawl(url, python):
    public_url(url)
    with tempfile.TemporaryDirectory(prefix='lite-crawl-') as tmp:
        result_path = Path(tmp) / 'body.json'
        p = subprocess.run([python, str(ROOT / 'scripts/crawl_body.py'), url, str(result_path)],
                           capture_output=True, text=True, timeout=45)
        if p.returncode:
            # Diagnostic tails only; credentials are neither used nor requested.
            raise RuntimeError('Crawl4AI unavailable/failed: ' + p.stderr[-600:])
        result = json.loads(result_path.read_text())
        if result.get('status_code') and result['status_code'] >= 400:
            raise RuntimeError(f"HTTP {result['status_code']}")
        return result['text']


def acquire(store, row, fetchers, force=False):
    if not force and store.cached(row):
        store.attempt(row['id'], 'reuse', 'ok', 'hash and quality checked; no network')
        return 'reused'
    for method, fetch in fetchers:
        try:
            text = fetch(row['url'])
            raw_path = store.raw(text, 'md')
            # Reader headers are provenance, not article prose for the quality gate.
            prose = text.split('Markdown Content:', 1)[-1].strip() if method == 'jina' else text
            ok, reason = quality(prose)
            store.attempt(row['id'], method, 'ok' if ok else 'rejected', reason, raw_path)
            if ok:
                store.body(row['id'], prose, method, 'extracted_page_unverified')
                store.db.commit()
                return 'succeeded'
        except Exception as e:
            store.attempt(row['id'], method, 'failed', f'{type(e).__name__}: {e}')
    # A failed refresh retains the previous good version and makes failure explicit.
    state = 'refresh_failed' if row['body_path'] else 'failed'
    store.db.execute('UPDATE materials SET body_status=? WHERE id=?', (state, row['id']))
    store.db.commit()
    return 'failed'


def export(store):
    rows = []
    for r in store.db.execute('SELECT * FROM materials ORDER BY discovered_at,id'):
        d = dict(r)
        d['prefilter'] = json.loads(d['prefilter'])
        d['observations'] = [dict(x) for x in store.db.execute('SELECT * FROM observations WHERE material_id=?', (r['id'],))]
        d['attempts'] = [dict(x) for x in store.db.execute('SELECT * FROM attempts WHERE material_id=?', (r['id'],))]
        d['body'] = (store.home / r['body_path']).read_text() if store.cached(r) else ''
        rows.append(d)
    return {'exported_at': now(), 'data_home': str(store.home), 'materials': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', default=str(ROOT / 'data/demo'), help='isolated SQLite/raw/receipt directory')
    subs = parser.add_subparsers(dest='command', required=True)
    subs.add_parser('init')
    p = subs.add_parser('fixture'); p.add_argument('--file', default=str(ROOT / 'fixtures/materials.json'))
    p = subs.add_parser('add'); p.add_argument('url'); p.add_argument('--title', default='(manual URL; title unverified)')
    subs.add_parser('queue')
    p = subs.add_parser('rss'); p.add_argument('--config', default=str(ROOT / 'config/rss.json'))
    p = subs.add_parser('opencli'); p.add_argument('--feed', choices=['top', 'newest'], default='top'); p.add_argument('--limit', type=int, default=2)
    p = subs.add_parser('bodies'); p.add_argument('--limit', type=int, default=3); p.add_argument('--id'); p.add_argument('--retry', action='store_true'); p.add_argument('--refresh', action='store_true')
    p.add_argument('--crawl-python', default=sys.executable)
    p.add_argument('--offline', action='store_true', help='Cache checks only; missing text stays pending without network')
    p = subs.add_parser('export'); p.add_argument('--out', required=True)
    subs.add_parser('status')
    args = parser.parse_args()
    store = Store(args.home)
    rules = json.loads((ROOT / 'config/keywords.json').read_text())
    started = now()
    if args.command == 'init':
        store.receipt('init', started, {'succeeded': 1, 'failed': 0})
    elif args.command == 'fixture':
        raw = Path(args.file).read_bytes()
        path = store.raw(raw, 'json')
        counts = Counter()
        for item in json.loads(raw):
            _, fresh = store.item(item, 'fixture', path, rules)
            counts['new' if fresh else 'duplicate'] += 1
        store.receipt('fixture (synthetic, no model)', started, {**counts, 'succeeded': 1, 'failed': 0})
    elif args.command == 'add':
        url = canonical(args.url)
        store.db.execute('INSERT OR IGNORE INTO queue(url,title,added_at) VALUES(?,?,?)', (url, args.title, now()))
        store.db.commit()
        store.receipt('add', started, {'queued': url, 'succeeded': 1, 'failed': 0})
    elif args.command == 'queue':
        counts = Counter()
        for q in store.db.execute("SELECT * FROM queue WHERE status='queued'").fetchall():
            path = store.raw(json.dumps(dict(q)), 'json')
            _, fresh = store.item(dict(q), 'manual', path, rules)
            counts['new' if fresh else 'duplicate'] += 1
            store.db.execute("UPDATE queue SET status='imported' WHERE url=?", (q['url'],))
        store.db.commit()
        store.receipt('queue', started, {**counts, 'succeeded': 1, 'failed': 0})
    elif args.command == 'rss':
        result = {'new': 0, 'duplicate': 0, 'succeeded': 0, 'failed': 0, 'sources': []}
        for source in json.loads(Path(args.config).read_text())['sources']:
            if not source['enabled']:
                continue
            try:
                if not 1 <= source.get('limit', 2) <= 10:
                    raise ValueError('Teaching feed limit must be 1..10')
                raw = request(source['url'])
                path = store.raw(raw, 'xml')
                items = parse_feed(raw, source['url'])[:source.get('limit', 2)]
                local = Counter()
                errors = []
                for item in items:
                    try:
                        _, fresh = store.item(item, source['id'], path, rules)
                        local['new' if fresh else 'duplicate'] += 1
                    except Exception as e:
                        store.db.rollback()
                        errors.append({'title': item.get('title'), 'error': f'{type(e).__name__}: {e}'})
                result['new'] += local['new']; result['duplicate'] += local['duplicate']
                result['succeeded'] += 1
                result['failed'] += int(bool(errors))
                result['sources'].append({'id': source['id'], 'status': 'partial' if errors else 'ok',
                                          'items': len(items), 'raw_path': path, 'item_errors': errors, **local})
            except Exception as e:
                result['failed'] += 1
                result['sources'].append({'id': source['id'], 'status': 'failed', 'error': f'{type(e).__name__}: {e}'})
        store.receipt('rss', started, result)
    elif args.command == 'opencli':
        if not 1 <= args.limit <= 5:
            parser.error('OpenCLI teaching limit must be 1..5')
        command = ['opencli', 'hackernews', args.feed, '--limit', str(args.limit), '-f', 'json']
        result = {'command_argv': command, 'new': 0, 'duplicate': 0, 'succeeded': 0, 'failed': 0}
        try:
            p = subprocess.run(command, capture_output=True, text=True, timeout=40)
            result['stdout_path'] = store.raw(p.stdout, 'json')
            result['stderr_path'] = store.raw(p.stderr, 'txt')
            if p.returncode:
                raise RuntimeError(f'OpenCLI exit {p.returncode}; see stderr_path (no account changes attempted)')
            values = json.loads(p.stdout)
            if isinstance(values, dict):
                values = values.get('data', values.get('items', []))
            if not isinstance(values, list):
                raise ValueError('Unexpected OpenCLI JSON shape')
            for row in values[:args.limit]:
                item = {'url': row.get('url') or f"https://news.ycombinator.com/item?id={row['id']}",
                        'title': row['title'], 'source_item_id': str(row.get('id', ''))}
                _, fresh = store.item(item, 'opencli:hackernews:' + args.feed, result['stdout_path'], rules)
                result['new' if fresh else 'duplicate'] += 1
            result['succeeded'] = 1
        except Exception as e:
            result['failed'] = 1; result['error'] = f'{type(e).__name__}: {e}'
        store.receipt('opencli', started, result)
    elif args.command == 'bodies':
        if not 1 <= args.limit <= 10:
            parser.error('Body limit must be 1..10')
        rows = store.db.execute('SELECT * FROM materials ORDER BY discovered_at,id').fetchall()
        if args.id:
            rows = [x for x in rows if x['id'] == args.id]
            if not rows:
                parser.error('Unknown material ID')
        if args.retry:
            rows = [x for x in rows if x['body_status'] in ('failed', 'refresh_failed')]
        fetchers = [('jina', lambda url: request('https://r.jina.ai/' + url).decode('utf-8')),
                    ('crawl4ai', lambda url: crawl(url, args.crawl_python))]
        counts = Counter()
        for row in rows[:args.limit]:
            if args.offline:
                state = 'reused' if store.cached(row) else 'pending'
                store.attempt(row['id'], 'offline', state, 'Cache check only; no network requested')
                counts[state] += 1
            else:
                counts[acquire(store, row, fetchers, args.refresh)] += 1
        store.receipt('bodies', started, dict(counts))
    elif args.command == 'export':
        dump(args.out, export(store))
        print(args.out)
    elif args.command == 'status':
        result = {'materials': [dict(x) for x in store.db.execute('SELECT id,title,url,body_status,body_method,body_scope,body_version FROM materials')],
                  'queue': [dict(x) for x in store.db.execute('SELECT * FROM queue')],
                  'runs': [dict(x) for x in store.db.execute('SELECT * FROM runs ORDER BY started_at DESC LIMIT 8')]}
        print(json.dumps(result, ensure_ascii=False, indent=2))
    store.db.close()
    return 1 if store.last_status in ('failed', 'partial') else 0


if __name__ == '__main__':
    sys.exit(main())
