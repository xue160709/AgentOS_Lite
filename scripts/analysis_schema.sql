PRAGMA user_version=1;
CREATE TABLE IF NOT EXISTS stage_runs (
 run_path TEXT PRIMARY KEY, stage TEXT NOT NULL CHECK(stage IN ('filter','daily')),
 engine TEXT NOT NULL, input_sha256 TEXT NOT NULL, context_sha256 TEXT NOT NULL,
 selection_sha256 TEXT, output_sha256 TEXT NOT NULL, completed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scores (
 run_path TEXT NOT NULL REFERENCES stage_runs(run_path), material_id TEXT NOT NULL,
 platform TEXT NOT NULL, body_sha256 TEXT, score INTEGER CHECK(score BETWEEN 1 AND 5),
 decision TEXT NOT NULL CHECK(decision IN ('keep','exclude','pending')),
 reason TEXT NOT NULL, evidence TEXT NOT NULL, limitations TEXT NOT NULL,
 PRIMARY KEY(run_path,material_id)
);
CREATE TABLE IF NOT EXISTS processed (
 material_id TEXT NOT NULL, context_sha256 TEXT NOT NULL, body_sha256 TEXT NOT NULL,
 report_run TEXT NOT NULL REFERENCES stage_runs(run_path), decision TEXT NOT NULL,
 scoring_sha256 TEXT NOT NULL DEFAULT '',
 PRIMARY KEY(material_id,context_sha256,body_sha256)
);
