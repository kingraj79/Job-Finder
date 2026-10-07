"""SQLite persistence for jobs, the user's profile, and application tracking.

Kept to stdlib sqlite3 deliberately — this is a single-user local tool, no
need for an ORM or a server database.
"""
from __future__ import annotations

import hashlib
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .difficulty import rate_job

DB_PATH = Path(__file__).resolve().parent.parent / "jobs.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    name TEXT DEFAULT '',
    email TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    location TEXT DEFAULT '',
    target_titles TEXT DEFAULT '',
    skills TEXT DEFAULT '',
    resume_text TEXT DEFAULT '',
    portfolio_url TEXT DEFAULT '',
    linkedin_url TEXT DEFAULT '',
    updated_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT DEFAULT '',
    url TEXT NOT NULL,
    source TEXT NOT NULL,
    posted_at TEXT,
    description TEXT DEFAULT '',
    match_score INTEGER DEFAULT 0,
    matched_keywords TEXT DEFAULT '',
    first_seen_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS applications (
    job_id TEXT PRIMARY KEY REFERENCES jobs(id),
    status TEXT NOT NULL DEFAULT 'new',
    draft TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

STATUSES = [
    "new", "drafted", "approved", "saved", "applied", "interviewing", "offer", "rejected", "not_applied",
]
STATUS_LABELS = {
    "new": "new", "drafted": "drafted", "approved": "approved", "saved": "saved", "applied": "applied",
    "interviewing": "interviewing", "offer": "offer", "rejected": "rejected", "not_applied": "did not apply",
}

# Dashboard categories: which statuses each tab holds. Order = tab order.
CATEGORIES = [
    ("review", "To review", ["new", "drafted", "approved"]),
    ("saved", "Saved", ["saved"]),
    ("applied", "Applied", ["applied", "interviewing", "offer", "rejected"]),
    ("not_applied", "Did not apply", ["not_applied"]),
]
MARK_CHOICES = ("applied", "saved", "not_applied")


def category_of(status: str) -> str:
    for key, _label, statuses in CATEGORIES:
        if status in statuses:
            return key
    return "review"


def job_id(company: str, title: str, url: str) -> str:
    key = f"{company.strip().lower()}|{title.strip().lower()}|{url.strip().lower()}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:20]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


_JOB_MIGRATIONS = {
    "difficulty": "INTEGER DEFAULT 3",
    "difficulty_reason": "TEXT DEFAULT ''",
    "district": "TEXT DEFAULT ''",
}


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        existing = {r["name"] for r in conn.execute("PRAGMA table_info(jobs)")}
        for col, decl in _JOB_MIGRATIONS.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE jobs ADD COLUMN {col} {decl}")
        conn.execute("INSERT OR IGNORE INTO profile (id) VALUES (1)")


def get_profile(conn) -> sqlite3.Row:
    return conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()


def save_profile(conn, fields: dict) -> None:
    fields = dict(fields)
    fields["updated_at"] = now_iso()
    cols = ", ".join(f"{k} = :{k}" for k in fields)
    conn.execute(f"UPDATE profile SET {cols} WHERE id = 1", fields)


def upsert_job(
    conn, job: dict, score: int, matched_keywords: list[str], district: str = ""
) -> tuple[str, bool]:
    """Insert a job if new; refresh score/description if already known.

    Returns (job_id, is_new).
    """
    jid = job_id(job["company"], job["title"], job["url"])
    difficulty, reason = rate_job(job["title"], job.get("description", ""))
    existing = conn.execute("SELECT id, district FROM jobs WHERE id = ?", (jid,)).fetchone()
    if existing:
        conn.execute(
            """UPDATE jobs SET description = ?, match_score = ?, matched_keywords = ?,
               posted_at = COALESCE(?, posted_at), difficulty = ?, difficulty_reason = ?,
               district = ? WHERE id = ?""",
            (
                job.get("description", ""), score, ",".join(matched_keywords), job.get("posted_at"),
                difficulty, reason, district or existing["district"] or "", jid,
            ),
        )
        return jid, False

    conn.execute(
        """INSERT INTO jobs (id, title, company, location, url, source, posted_at,
           description, match_score, matched_keywords, first_seen_at,
           difficulty, difficulty_reason, district)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            jid, job["title"], job["company"], job.get("location", ""), job["url"],
            job["source"], job.get("posted_at"), job.get("description", ""), score,
            ",".join(matched_keywords), now_iso(), difficulty, reason, district,
        ),
    )
    conn.execute(
        """INSERT OR IGNORE INTO applications (job_id, status, created_at, updated_at)
           VALUES (?, 'new', ?, ?)""",
        (jid, now_iso(), now_iso()),
    )
    return jid, True


def list_jobs_with_status(conn, status: str | None = None) -> list[sqlite3.Row]:
    query = """
        SELECT jobs.*, applications.status AS app_status, applications.draft AS draft,
               applications.notes AS notes
        FROM jobs JOIN applications ON applications.job_id = jobs.id
    """
    params: tuple = ()
    if status:
        query += " WHERE applications.status = ?"
        params = (status,)
    query += " ORDER BY match_score DESC, first_seen_at DESC"
    return conn.execute(query, params).fetchall()


def get_job(conn, jid: str) -> sqlite3.Row | None:
    return conn.execute(
        """SELECT jobs.*, applications.status AS app_status, applications.draft AS draft,
                  applications.notes AS notes
           FROM jobs JOIN applications ON applications.job_id = jobs.id
           WHERE jobs.id = ?""",
        (jid,),
    ).fetchone()


def set_draft(conn, jid: str, draft: str) -> None:
    conn.execute(
        """UPDATE applications SET draft = ?, updated_at = ?,
           status = CASE WHEN status = 'new' THEN 'drafted' ELSE status END
           WHERE job_id = ?""",
        (draft, now_iso(), jid),
    )


def set_status(conn, jid: str, status: str, notes: str | None = None) -> None:
    if status not in STATUSES:
        raise ValueError(f"unknown status: {status}")
    if notes is None:
        conn.execute(
            "UPDATE applications SET status = ?, updated_at = ? WHERE job_id = ?",
            (status, now_iso(), jid),
        )
    else:
        conn.execute(
            "UPDATE applications SET status = ?, notes = ?, updated_at = ? WHERE job_id = ?",
            (status, notes, now_iso(), jid),
        )


def counts_by_category(conn) -> dict:
    by_status = counts_by_status(conn)
    counts = {key: 0 for key, _l, _s in CATEGORIES}
    for status, n in by_status.items():
        counts[category_of(status)] += n
    counts["all"] = sum(counts.values())
    return counts


def counts_by_status(conn) -> dict:
    rows = conn.execute(
        "SELECT status, COUNT(*) AS n FROM applications GROUP BY status"
    ).fetchall()
    return {r["status"]: r["n"] for r in rows}
