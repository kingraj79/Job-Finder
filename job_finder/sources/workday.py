"""
Workday career-site client (used by most large banks and enterprises).

Workday-hosted careers pages load their listings from a public JSON endpoint
that needs no login. This is NOT a documented, supported API — it is the same
request the employer's own careers page makes — so it is used sparingly:
a few search terms, a couple of pages each, with a polite User-Agent.
Workday's list endpoint has no descriptions, so jobs from here are rated on
title alone.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import requests

LIST_URL = "https://{tenant}.{host}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
JOB_URL = "https://{tenant}.{host}.myworkdayjobs.com/en-US/{site}{path}"
HEADERS = {"User-Agent": "job-finder/1.0 (personal job search tool)"}
PAGE_SIZE = 20


def _posted_at(text: str | None) -> str | None:
    """Workday only gives relative dates ("Posted 3 Days Ago"); convert approximately."""
    if not text:
        return None
    t = text.lower()
    now = datetime.now(timezone.utc)
    if "today" in t:
        days = 0
    elif "yesterday" in t:
        days = 1
    else:
        m = re.search(r"(\d+)\+?\s*day", t)
        if not m:
            return None
        days = int(m.group(1))
    return (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


def fetch_jobs(
    slug: str, host: str, site: str, terms: list[str] | None = None,
    max_pages: int = 2, timeout: int = 15,
) -> list[dict]:
    url = LIST_URL.format(tenant=slug, host=host, site=site)
    seen: set[str] = set()
    jobs = []
    for term in terms or [""]:
        for page in range(max_pages):
            resp = requests.post(
                url,
                json={"appliedFacets": {}, "limit": PAGE_SIZE, "offset": page * PAGE_SIZE, "searchText": term},
                headers=HEADERS,
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            postings = data.get("jobPostings") or []
            for p in postings:
                path = p.get("externalPath") or ""
                if not path or path in seen:
                    continue
                seen.add(path)
                jobs.append({
                    "title": (p.get("title") or "").strip(),
                    "company": slug,
                    "location": p.get("locationsText", "") or "",
                    "url": JOB_URL.format(tenant=slug, host=host, site=site, path=path),
                    "posted_at": _posted_at(p.get("postedOn")),
                    "source": "Workday",
                    "description": "",
                })
            if len(postings) < PAGE_SIZE or (page + 1) * PAGE_SIZE >= data.get("total", 0):
                break
    return jobs
