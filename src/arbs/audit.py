"""Append-only, versioned SQLite audit storage for read-only scanner lineage."""
from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path
from typing import Any

MIGRATIONS=(
(1,"""
CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE runs(id TEXT PRIMARY KEY,started_at TEXT NOT NULL,completed_at TEXT,status TEXT NOT NULL,parser_version TEXT NOT NULL,policy_version TEXT NOT NULL,counts_json TEXT NOT NULL);
CREATE TABLE raw_references(id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES runs(id),venue TEXT NOT NULL,source_url TEXT NOT NULL,snapshot_sha256 TEXT NOT NULL,received_at TEXT NOT NULL);
CREATE TABLE normalized_contracts(id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES runs(id),raw_reference_id TEXT NOT NULL REFERENCES raw_references(id),schema_version TEXT NOT NULL,parser_version TEXT NOT NULL,contract_json TEXT NOT NULL);
CREATE TABLE books(id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES runs(id),contract_id TEXT NOT NULL REFERENCES normalized_contracts(id),received_at TEXT NOT NULL,source_at TEXT,book_json TEXT NOT NULL);
CREATE TABLE decisions(id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES runs(id),created_at TEXT NOT NULL,decision TEXT NOT NULL,pricing_eligible INTEGER NOT NULL CHECK(pricing_eligible IN(0,1)),participants_json TEXT NOT NULL,start_utc TEXT NOT NULL,evidence_json TEXT NOT NULL,UNIQUE(run_id,participants_json,start_utc));
CREATE TABLE reviews(id TEXT PRIMARY KEY,decision_id TEXT NOT NULL REFERENCES decisions(id),reviewer TEXT NOT NULL,reviewed_at TEXT NOT NULL,expires_at TEXT NOT NULL,scenario_proof TEXT NOT NULL,differences_json TEXT NOT NULL,snapshot_hashes_json TEXT NOT NULL,outcome TEXT NOT NULL CHECK(outcome IN('APPROVED_OVERRIDE','REJECTED','NEEDS_MORE_EVIDENCE')));
CREATE TABLE opportunities(id TEXT PRIMARY KEY,decision_id TEXT NOT NULL REFERENCES decisions(id),created_at TEXT NOT NULL,eligible INTEGER NOT NULL CHECK(eligible IN(0,1)),reason TEXT NOT NULL,evidence_json TEXT NOT NULL);
CREATE TABLE resolutions(id TEXT PRIMARY KEY,decision_id TEXT NOT NULL REFERENCES decisions(id),venue TEXT NOT NULL,resolved_at TEXT NOT NULL,outcome TEXT NOT NULL,evidence_json TEXT NOT NULL,UNIQUE(decision_id,venue));
CREATE INDEX raw_run ON raw_references(run_id); CREATE INDEX contracts_run ON normalized_contracts(run_id); CREATE INDEX books_run ON books(run_id); CREATE INDEX decisions_run ON decisions(run_id); CREATE INDEX opportunities_decision ON opportunities(decision_id); CREATE INDEX resolutions_decision ON resolutions(decision_id);
"""),)
IMMUTABLE_TABLES=("raw_references","normalized_contracts","books","decisions","reviews","opportunities","resolutions")


def connect(path:Path)->sqlite3.Connection:
 path.parent.mkdir(parents=True,exist_ok=True);db=sqlite3.connect(path);db.execute("PRAGMA foreign_keys=ON");db.execute("PRAGMA journal_mode=WAL")
 current=db.execute("PRAGMA user_version").fetchone()[0]
 for version,sql in MIGRATIONS:
  if version>current:
   with db: db.executescript(sql);db.execute("INSERT INTO schema_migrations(version) VALUES(?)",(version,));db.execute(f"PRAGMA user_version={version}")
 for table in IMMUTABLE_TABLES:
  for action in ("UPDATE","DELETE"):
   db.execute(f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{action.lower()} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'append-only table'); END")
 return db


def insert_run(db:sqlite3.Connection,run:dict[str,Any])->None:
 db.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?)",(run['id'],run['started_at'],run.get('completed_at'),run['status'],run['parser_version'],run['policy_version'],json.dumps(run.get('counts',{}),sort_keys=True)))


def insert_decision(db:sqlite3.Connection,decision:dict[str,Any])->None:
 db.execute("INSERT INTO decisions VALUES (?,?,?,?,?,?,?,?)",(decision['id'],decision['run_id'],decision['created_at'],decision['decision'],int(decision['pricing_eligible']),json.dumps(decision['participants'],sort_keys=True),decision['start_utc'],json.dumps(decision['evidence'],sort_keys=True)))


def insert_review(db:sqlite3.Connection,review:dict[str,Any])->None:
 db.execute("INSERT INTO reviews VALUES (?,?,?,?,?,?,?,?,?)",(review['id'],review['decision_id'],review['reviewer'],review['reviewed_at'],review['expires_at'],review['scenario_proof'],json.dumps(review['differences'],sort_keys=True),json.dumps(review['snapshot_hashes'],sort_keys=True),review['outcome']))


def backup(db:sqlite3.Connection,target:Path)->None:
 target.parent.mkdir(parents=True,exist_ok=True);out=sqlite3.connect(target)
 try: db.backup(out)
 finally: out.close()


def verify_backup(path:Path)->dict[str,int]:
 db=sqlite3.connect(f"file:{path}?mode=ro",uri=True)
 try:
  result=db.execute("PRAGMA integrity_check").fetchone()[0]
  if result!='ok':raise RuntimeError(result)
  return {t:db.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ('runs',)+IMMUTABLE_TABLES}
 finally:db.close()
