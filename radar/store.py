import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.environ.get('RADAR_DB', Path(__file__).resolve().parent.parent / '.radar/radar.db'))

@contextmanager
def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()

def init():
    with db() as c:
        c.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS evidence(
          id TEXT PRIMARY KEY, source TEXT NOT NULL, title TEXT NOT NULL,
          url TEXT NOT NULL, published TEXT NOT NULL, summary TEXT NOT NULL,
          theme TEXT NOT NULL, stance TEXT NOT NULL DEFAULT 'unknown',
          cluster TEXT NOT NULL, retrieved TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS evidence_theme_date ON evidence(theme,published);
        CREATE TABLE IF NOT EXISTS observations(
          source TEXT, symbol TEXT, date TEXT, metric TEXT, value REAL,
          unit TEXT, url TEXT, retrieved TEXT,
          PRIMARY KEY(source,symbol,date,metric));
        CREATE TABLE IF NOT EXISTS source_runs(
          source TEXT PRIMARY KEY, status TEXT, count INTEGER, message TEXT,
          checked TEXT, first_date TEXT, last_date TEXT);
        CREATE TABLE IF NOT EXISTS watchlist(theme TEXT PRIMARY KEY, created TEXT);
        CREATE TABLE IF NOT EXISTS notes(theme TEXT PRIMARY KEY, body TEXT, updated TEXT);
        CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, status TEXT, started TEXT, ended TEXT, result TEXT);
        CREATE TABLE IF NOT EXISTS holdings(
          id TEXT PRIMARY KEY, manager TEXT, period TEXT, filed TEXT, issuer TEXT, cusip TEXT,
          shares REAL, share_type TEXT, put_call TEXT, reported_value REAL, url TEXT,
          retrieved TEXT);
        CREATE TABLE IF NOT EXISTS decisions(
          id TEXT PRIMARY KEY, theme TEXT, disposition TEXT, rationale TEXT,
          evidence_ids TEXT, created TEXT);
        CREATE TABLE IF NOT EXISTS scenarios(theme TEXT PRIMARY KEY, model TEXT, updated TEXT);
        ''')
        c.execute("UPDATE jobs SET status='interrupted', ended=datetime('now') WHERE status='running'")
