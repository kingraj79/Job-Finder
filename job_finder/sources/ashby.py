"""
Ashby job board API client.

Public, unauthenticated posting API Ashby-hosted companies expose for their
own careers pages — safe and intended for this use.
Docs: https://developers.ashbyhq.com/docs/public-job-posting-api
"""
from __future__ import annotations

import requests

from ..util import strip_html

BASE_URL = "https://api.ashbyhq.com/posting-api/job-board/{slug}"


def fetch_jobs(slug: str, timeout: int = 15) -> list[dict]:
    url = BASE_URL.format(slug=slug)
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()

    jobs = []
    for j in resp.json().get("jobs", []):
        if j.get("isListed") is False:
            continue
        jobs.append({
            "title": (j.get("title") or "").strip(),
            "company": slug,
            "location": j.get("location", "") or "",
            "url": j.get("jobUrl", ""),
            "posted_at": j.get("publishedAt"),
            "source": "Ashby",
            "description": j.get("descriptionPlain") or strip_html(j.get("descriptionHtml")),
        })
    return jobs
