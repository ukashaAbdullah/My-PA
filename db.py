import sqlite3
from pathlib import Path
import json

DB = Path("careerbuddy.db")

def conn():
    return sqlite3.connect(DB)

def init_db():
    c = conn()
    c.execute("""
    CREATE TABLE IF NOT EXISTS profile (
        id INTEGER PRIMARY KEY CHECK (id=1),
        data TEXT NOT NULL
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS opportunities (
        id TEXT PRIMARY KEY,
        data TEXT NOT NULL,
        saved INTEGER DEFAULT 0
    )
    """)
    c.commit()
    c.close()

def save_profile(data):
    c = conn()
    c.execute("INSERT OR REPLACE INTO profile(id,data) VALUES(1,?)", (json.dumps(data),))
    c.commit()
    c.close()

def load_profile():
    c = conn()
    row = c.execute("SELECT data FROM profile WHERE id=1").fetchone()
    c.close()
    return json.loads(row[0]) if row else {}

def save_opportunities(items):
    c = conn()
    for item in items:
        if not item.get("id"):
            continue
        existing = c.execute("SELECT saved FROM opportunities WHERE id=?", (item["id"],)).fetchone()
        saved = existing[0] if existing else 0
        c.execute(
            "INSERT OR REPLACE INTO opportunities(id,data,saved) VALUES(?,?,?)",
            (item["id"], json.dumps(item), saved)
        )
    c.commit()
    c.close()

def toggle_saved(item_id, value=True):
    c = conn()
    c.execute("UPDATE opportunities SET saved=? WHERE id=?", (1 if value else 0, item_id))
    c.commit()
    c.close()

def load_saved():
    c = conn()
    rows = c.execute("SELECT data FROM opportunities WHERE saved=1 ORDER BY rowid DESC").fetchall()
    c.close()
    return [json.loads(r[0]) for r in rows]
