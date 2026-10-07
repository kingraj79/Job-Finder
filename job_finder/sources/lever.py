"""
Lever job board API client.

Public, unauthenticated endpoint Lever-hosted companies expose for their
own careers pages — safe and intended for this use.
Docs: https://github.com/lever/postings-api
"""
from __future__ import annotations

from datetime import datetime, timezone

import requests

from ..util import strip_html

BASE_URL = "https://api.lever.co/v0/postings/{slug}"


def fetch_jobs(slug: str, timeout: int = 15) -> list[dict]:
    """Fetch all open postings for a Lever board token."""
    url = BASE_URL.format(slug=slug)
    resp = requests.get(url, params={"mode": "json"}, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for j in data:
        created_ms = j.get("createdAt")
        posted_at = None
        if created_ms:
            posted_at = datetime.fromtimestamp(
                created_ms / 1000, tz=timezone.utc
            ).isoformat()

        description = j.get("descriptionPlain") or strip_html(j.get("description"))
        lists = j.get("lists") or []
        extra = " ".join(
            strip_html(item.get("content", "")) for item in lists if isinstance(item, dict)
        )

        jobs.append({
            "title": (j.get("text") or "").strip(),
            "company": slug,
            "location": (j.get("categories") or {}).get("location", ""),
            "url": j.get("hostedUrl", ""),
            "posted_at": posted_at,
            "source": "Lever",
            "description": (description + " " + extra).strip(),
        })
    return jobs
