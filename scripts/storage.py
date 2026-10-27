"""Per-platform collection stores and a separate analysis ledger. No source DB migration."""
import sqlite3
from pathlib import Path
from lite import ROOT, Store, now, digest
from sources import load_config
import json

PLATFORMS = ('rss', 'urls', 'xiaohongshu', 'twitter', 'tiktok', 'hackernews')


def context_directory(explicit=None):
    if explicit:
        return Path(explicit).resolve()
    local = ROOT / 'context/local'
    return local if local.is_dir() else ROOT / 'context'


def analysis_connection(home):
    home = Path(home).resolve()
    home.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(home / 'analysis.sqlite')
    db.execute('PRAGMA foreign_keys=ON')
    db.executescript((ROOT / 'scripts/analysis_schema.sql').read_text())
    if 'scoring_sha256' not in {r[1] for r in db.execute('PRAGMA table_info(processed)')}:
        db.execute("ALTER TABLE processed ADD COLUMN scoring_sha256 TEXT NOT NULL DEFAULT ''")
        db.commit()
    return db


class PlatformStore(Store):
    def __init__(self, home, platform):
        if platform not in PLATFORMS:
            raise ValueError('Unknown platform')
        self.platform = platform
        super().__init__(Path(home) / 'sources' / platform, platform + '.sqlite', 'source_schema.sql')
        self.db.execute('INSERT OR IGNORE INTO source_meta VALUES(?,?,?)',(platform,1,now()))
        self.db.commit()

    def platform_item(self, mid, item, row):
        metrics = {k: row[k] for k in ('likes','plays','views','comments','collects','shares','rank') if k in row}
        self.db.execute('INSERT INTO platform_items VALUES(?,?,?,?,?,?) '
                        'ON CONFLICT(material_id) DO UPDATE SET metrics_json=excluded.metrics_json,last_observed_at=excluded.last_observed_at',
                        (mid,item['source_item_id'],str(row.get('author','')),item.get('content_type','text'),
                         json.dumps(metrics,ensure_ascii=False),now()))
        self.db.commit()


def scoring_hash():
    return digest(json.dumps(load_config(ROOT / 'config/scoring.json'),sort_keys=True,ensure_ascii=False))


def processed_ids(home, ctx):
    with analysis_connection(home) as db:
        return {(r[0],r[1]) for r in db.execute('SELECT material_id,body_sha256 FROM processed WHERE context_sha256=? AND scoring_sha256=?',(ctx,scoring_hash()))}


def save_analysis(home, output, stage, engine, snapshot, result, input_sha, ctx, selection=None, selection_sha=None):
    run_path = str(Path(output).resolve())
    by_id = {m['id']:m for m in snapshot['materials']}
    with analysis_connection(home) as db:
        db.execute('INSERT INTO stage_runs VALUES(?,?,?,?,?,?,?,?)',
                   (run_path,stage,engine,input_sha,ctx,selection_sha,digest((Path(output)/'model.json').read_bytes()),now()))
        if stage == 'filter':
            for row in result['decisions']:
                m = by_id[row['id']]
                db.execute('INSERT INTO scores VALUES(?,?,?,?,?,?,?,?,?)',
                           (run_path,row['id'],m.get('platform','legacy'),m.get('body_sha256'),row['score'],
                            row['decision'],row['reason'],row['evidence'],row['limitations']))
        elif selection:
            for row in selection['decisions']:
                if row['decision'] != 'pending':
                    m = by_id[row['id']]
                    db.execute('INSERT OR REPLACE INTO processed VALUES(?,?,?,?,?,?)',
                               (row['id'],ctx,m.get('body_sha256') or '',run_path,row['decision'],scoring_hash()))
