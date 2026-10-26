PRAGMA user_version=1;
CREATE TABLE IF NOT EXISTS materials (
 id TEXT PRIMARY KEY, url TEXT UNIQUE NOT NULL, title TEXT NOT NULL,
 published TEXT, discovered_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 prefilter TEXT NOT NULL, body_status TEXT NOT NULL DEFAULT 'missing',
 body_path TEXT, body_sha256 TEXT, body_method TEXT, body_scope TEXT, body_version INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS observations (
 id INTEGER PRIMARY KEY, material_id TEXT REFERENCES materials(id), source TEXT NOT NULL,
 source_item_id TEXT, observed_at TEXT NOT NULL, published TEXT, raw_path TEXT NOT NULL,
 UNIQUE(material_id, source, raw_path)
);
CREATE TABLE IF NOT EXISTS body_versions (
 material_id TEXT REFERENCES materials(id), version INTEGER, sha256 TEXT NOT NULL,
 path TEXT NOT NULL, method TEXT NOT NULL, scope TEXT NOT NULL, fetched_at TEXT NOT NULL,
 PRIMARY KEY(material_id,version)
);
CREATE TABLE IF NOT EXISTS attempts (
 id INTEGER PRIMARY KEY, material_id TEXT REFERENCES materials(id), method TEXT NOT NULL,
 attempted_at TEXT NOT NULL, status TEXT NOT NULL, detail TEXT, raw_path TEXT
);
CREATE TABLE IF NOT EXISTS queue (
 url TEXT PRIMARY KEY, title TEXT NOT NULL, added_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'queued'
);
CREATE TABLE IF NOT EXISTS runs (
 id TEXT PRIMARY KEY, command TEXT NOT NULL, started_at TEXT NOT NULL, ended_at TEXT,
 status TEXT NOT NULL, summary TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS decisions (
 run_id TEXT NOT NULL, material_id TEXT REFERENCES materials(id), decision TEXT NOT NULL,
 reason TEXT NOT NULL, evidence TEXT NOT NULL, context_sha256 TEXT NOT NULL,
 PRIMARY KEY(run_id,material_id)
);
