"""
Greenhouse job board API client.

Public, unauthenticated endpoint that Greenhouse-hosted companies expose
for their own careers pages to consume — safe and intended for this use.
Docs: https://developers.greenhouse.io/job-board.html
"""
from __future__ import annotations

import requests

from ..util import strip_html

BASE_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"


def fetch_jobs(slug: str, timeout: int = 15) -> list[dict]:
    """Fetch all open postings for a Greenhouse board token."""
    url = BASE_URL.format(slug=slug)
    resp = requests.get(url, params={"content": "true"}, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for j in data.get("jobs", []):
        jobs.append({
            "title": (j.get("title") or "").strip(),
            "company": slug,
            "location": (j.get("location") or {}).get("name", ""),
            "url": j.get("absolute_url", ""),
            "posted_at": j.get("updated_at"),
            "source": "Greenhouse",
            "description": strip_html(j.get("content")),
        })
    return jobs
