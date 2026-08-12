"""Immutable SQLite audit storage for read-only scanner lineage."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS runs (
 id TEXT PRIMARY KEY, started_at TEXT NOT NULL, completed_at TEXT, status TEXT NOT NULL,
 parser_version TEXT NOT NULL, policy_version TEXT NOT NULL, counts_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS raw_references (
 id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id), venue TEXT NOT NULL,
 source_url TEXT NOT NULL, snapshot_sha256 TEXT NOT NULL, received_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS normalized_contracts (
 id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id), raw_reference_id TEXT NOT NULL REFERENCES raw_references(id),
 schema_version TEXT NOT NULL, parser_version TEXT NOT NULL, contract_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS books (
 id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id), contract_id TEXT NOT NULL REFERENCES normalized_contracts(id),
 received_at TEXT NOT NULL, source_at TEXT, book_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS decisions (
 id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id), created_at TEXT NOT NULL,
 decision TEXT NOT NULL, pricing_eligible INTEGER NOT NULL CHECK(pricing_eligible IN (0,1)),
 participants_json TEXT NOT NULL, start_utc TEXT NOT NULL, evidence_json TEXT NOT NULL,
 UNIQUE(run_id, participants_json, start_utc)
);
CREATE INDEX IF NOT EXISTS decisions_run ON decisions(run_id);
CREATE TABLE IF NOT EXISTS reviews (
 id TEXT PRIMARY KEY, decision_id TEXT NOT NULL REFERENCES decisions(id), reviewer TEXT NOT NULL,
 reviewed_at TEXT NOT NULL, expires_at TEXT NOT NULL, scenario_proof TEXT NOT NULL,
 snapshot_hashes_json TEXT NOT NULL, outcome TEXT NOT NULL,
 CHECK(outcome IN ('APPROVED_OVERRIDE','REJECTED','NEEDS_MORE_EVIDENCE'))
);
CREATE TABLE IF NOT EXISTS opportunities (
 id TEXT PRIMARY KEY, decision_id TEXT NOT NULL REFERENCES decisions(id), created_at TEXT NOT NULL,
 eligible INTEGER NOT NULL CHECK(eligible IN (0,1)), reason TEXT NOT NULL, evidence_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS resolutions (
 id TEXT PRIMARY KEY, decision_id TEXT NOT NULL REFERENCES decisions(id), venue TEXT NOT NULL,
 resolved_at TEXT NOT NULL, outcome TEXT NOT NULL, evidence_json TEXT NOT NULL,
 UNIQUE(decision_id, venue)
);
CREATE INDEX IF NOT EXISTS raw_run ON raw_references(run_id);
CREATE INDEX IF NOT EXISTS contracts_run ON normalized_contracts(run_id);
CREATE INDEX IF NOT EXISTS books_run ON books(run_id);
CREATE INDEX IF NOT EXISTS opportunities_decision ON opportunities(decision_id);
CREATE INDEX IF NOT EXISTS resolutions_decision ON resolutions(decision_id);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript(SCHEMA)
    return db


def insert_run(db: sqlite3.Connection, run: dict[str, Any]) -> None:
    db.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?)", (
        run["id"], run["started_at"], run.get("completed_at"), run["status"],
        run["parser_version"], run["policy_version"], json.dumps(run.get("counts", {}), sort_keys=True),
    ))


def insert_decision(db: sqlite3.Connection, decision: dict[str, Any]) -> None:
    db.execute("INSERT INTO decisions VALUES (?,?,?,?,?,?,?,?)", (
        decision["id"], decision["run_id"], decision["created_at"], decision["decision"],
        int(decision["pricing_eligible"]), json.dumps(decision["participants"], sort_keys=True),
        decision["start_utc"], json.dumps(decision["evidence"], sort_keys=True),
    ))
