"""Brings jobs you found yourself on LinkedIn / Indeed into the tracker.

LinkedIn and Indeed prohibit automated scraping, so nothing here fetches from them.
Instead: you paste a posting you're looking at, or upload the CSV from LinkedIn's own
"Get a copy of your data" export (Saved Jobs / Job Applications).
"""
from __future__ import annotations

import csv
import io
from urllib.parse import urlparse

MAX_CSV_BYTES = 2 * 1024 * 1024
MAX_ROWS = 1000

_TITLE_KEYS = ("job title", "title", "position")
_COMPANY_KEYS = ("company name", "company", "employer")
_URL_KEYS = ("job url", "job link", "url", "link")


class ImportError_(ValueError):
    pass


def safe_url(url: str) -> str:
    url = (url or "").strip()
    return url if urlparse(url).scheme in ("http", "https") and urlparse(url).netloc else ""


def source_for(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if host.endswith("linkedin.com"):
        return "LinkedIn"
    if host.endswith("indeed.com"):
        return "Indeed"
    return "Manual"


def _pick(row: dict, keys: tuple[str, ...]) -> str:
    for k, v in row.items():
        if k and k.strip().lower() in keys:
            return (v or "").strip()
    return ""


def parse_csv(data: bytes) -> list[dict]:
    if len(data) > MAX_CSV_BYTES:
        raise ImportError_("That file is larger than 2 MB.")
    lines = data.decode("utf-8-sig", errors="replace").splitlines()
    header_at = next(
        (i for i, l in enumerate(lines)
         if any(k in l.lower() for k in _TITLE_KEYS) and any(k in l.lower() for k in _COMPANY_KEYS)),
        None,
    )
    if header_at is None:
        found = lines[0][:120] if lines else "(empty file)"
        raise ImportError_(
            "Couldn't find job title and company columns. Expected a LinkedIn 'Saved Jobs.csv' or "
            f"'Job Applications.csv'. First line of your file: {found}"
        )
    jobs = []
    for row in csv.DictReader(lines[header_at:]):
        title, company = _pick(row, _TITLE_KEYS), _pick(row, _COMPANY_KEYS)
        if not title or not company:
            continue
        url = safe_url(_pick(row, _URL_KEYS))
        jobs.append({
            "title": title, "company": company, "url": url, "location": "",
            "source": "LinkedIn", "posted_at": None, "description": "",
        })
        if len(jobs) >= MAX_ROWS:
            break
    if not jobs:
        raise ImportError_("No jobs found in that file.")
    return jobs
