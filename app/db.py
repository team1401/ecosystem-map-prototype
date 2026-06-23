from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "ecosystem.db"

PUBLIC_STATUS = "Approved / Published"
PUBLIC_VISIBILITY = "Public"

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS ecosystems (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  location TEXT,
  theme TEXT,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'Active',
  admin_owner TEXT
);

CREATE TABLE IF NOT EXISTS entities (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ecosystem_id INTEGER NOT NULL REFERENCES ecosystems(id),
  name TEXT NOT NULL,
  type TEXT NOT NULL,
  description TEXT,
  location TEXT,
  website TEXT,
  social_links TEXT,
  tags TEXT,
  publication_status TEXT NOT NULL DEFAULT 'Draft',
  visibility TEXT NOT NULL DEFAULT 'Public',
  source TEXT,
  confidence TEXT DEFAULT 'Verified',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ecosystem_id INTEGER NOT NULL REFERENCES ecosystems(id),
  name TEXT NOT NULL,
  starts_at TEXT,
  location TEXT,
  host_entity_id INTEGER REFERENCES entities(id),
  category TEXT,
  link TEXT,
  publication_status TEXT NOT NULL DEFAULT 'Draft',
  visibility TEXT NOT NULL DEFAULT 'Public',
  description TEXT
);

CREATE TABLE IF NOT EXISTS resources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ecosystem_id INTEGER NOT NULL REFERENCES ecosystems(id),
  name TEXT NOT NULL,
  type TEXT,
  description TEXT,
  provider_entity_id INTEGER REFERENCES entities(id),
  eligibility TEXT,
  location TEXT,
  url TEXT,
  tags TEXT,
  publication_status TEXT NOT NULL DEFAULT 'Draft',
  visibility TEXT NOT NULL DEFAULT 'Public'
);

CREATE TABLE IF NOT EXISTS opportunities (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ecosystem_id INTEGER NOT NULL REFERENCES ecosystems(id),
  name TEXT NOT NULL,
  type TEXT,
  deadline TEXT,
  sponsor_entity_id INTEGER REFERENCES entities(id),
  eligibility TEXT,
  link TEXT,
  description TEXT,
  publication_status TEXT NOT NULL DEFAULT 'Draft',
  visibility TEXT NOT NULL DEFAULT 'Public'
);

CREATE TABLE IF NOT EXISTS needs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ecosystem_id INTEGER NOT NULL REFERENCES ecosystems(id),
  need_type TEXT,
  description TEXT NOT NULL,
  requester_entity_id INTEGER REFERENCES entities(id),
  urgency TEXT,
  location TEXT,
  status TEXT NOT NULL DEFAULT 'Open',
  publication_status TEXT NOT NULL DEFAULT 'Draft',
  visibility TEXT NOT NULL DEFAULT 'Public'
);

CREATE TABLE IF NOT EXISTS offers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ecosystem_id INTEGER NOT NULL REFERENCES ecosystems(id),
  offer_type TEXT,
  description TEXT NOT NULL,
  provider_entity_id INTEGER REFERENCES entities(id),
  availability TEXT,
  location TEXT,
  status TEXT NOT NULL DEFAULT 'Open',
  publication_status TEXT NOT NULL DEFAULT 'Draft',
  visibility TEXT NOT NULL DEFAULT 'Public'
);

CREATE TABLE IF NOT EXISTS relationships (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ecosystem_id INTEGER NOT NULL REFERENCES ecosystems(id),
  source_entity_id INTEGER NOT NULL REFERENCES entities(id),
  relationship_type TEXT NOT NULL,
  target_kind TEXT NOT NULL DEFAULT 'entity',
  target_entity_id INTEGER REFERENCES entities(id),
  target_label TEXT,
  description TEXT,
  evidence TEXT,
  confidence TEXT NOT NULL DEFAULT 'Suggested',
  publication_status TEXT NOT NULL DEFAULT 'Draft',
  visibility TEXT NOT NULL DEFAULT 'Public',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS submissions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ecosystem_id INTEGER REFERENCES ecosystems(id),
  submitter_name TEXT,
  submitter_email TEXT,
  submission_type TEXT NOT NULL,
  raw_data TEXT NOT NULL,
  linked_record_kind TEXT,
  linked_record_id INTEGER,
  status TEXT NOT NULL DEFAULT 'Pending Review',
  admin_notes TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  reviewed_at TEXT
);

CREATE TABLE IF NOT EXISTS contributors (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  email TEXT,
  role TEXT NOT NULL DEFAULT 'Contributor',
  linked_entity_id INTEGER REFERENCES entities(id),
  contribution_history TEXT
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def public_clause(alias: str = "") -> str:
    prefix = f"{alias}." if alias else ""
    return f"{prefix}publication_status = '{PUBLIC_STATUS}' AND {prefix}visibility = '{PUBLIC_VISIBILITY}'"
