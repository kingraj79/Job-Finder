"""
Adzuna aggregator API client.

Adzuna aggregates postings from many job boards (including listings that
also appear on Indeed/LinkedIn) under its own free API — this reaches
that coverage without scraping those sites directly, which is against
their Terms of Service.

Requires free credentials from https://developer.adzuna.com/, set as:
    ADZUNA_APP_ID
    ADZUNA_APP_KEY
"""
from __future__ import annotations

import os

import requests

BASE_URL = "https://api.adzuna.com/v1/api/jobs"


def fetch_jobs(
    search_term: str,
    country: str,
    results_per_page: int,
    max_pages: int,
    location: str | None = None,
    timeout: int = 15,
) -> list[dict]:
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        raise RuntimeError(
            "ADZUNA_APP_ID / ADZUNA_APP_KEY are not set. Get free credentials "
            "at https://developer.adzuna.com/ and add them to your .env "
            "(see .env.example)."
        )

    jobs = []
    for page in range(1, max_pages + 1):
        url = f"{BASE_URL}/{country}/search/{page}"
        params = {
            "app_id": app_id,
            "app_key": app_key,
            "results_per_page": results_per_page,
            "what": search_term,
            "content-type": "application/json",
        }
        if location:
            params["where"] = location

        resp = requests.get(url, params=params, timeout=timeout)
        if resp.status_code == 400:
            # Adzuna returns 400 past the last available page — stop quietly.
            break
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if not results:
            break

        for r in results:
            jobs.append({
                "title": (r.get("title") or "").strip(),
                "company": (r.get("company") or {}).get("display_name", "Unknown"),
                "location": (r.get("location") or {}).get("display_name", ""),
                "url": r.get("redirect_url", ""),
                "posted_at": r.get("created"),
                "source": "Adzuna",
                "description": (r.get("description") or "").strip(),
            })

    return jobs
