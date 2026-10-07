#!/usr/bin/env python3
"""
job_finder — pulls fresh postings from top-company career pages
(Greenhouse / Lever) plus the Adzuna aggregator API, filters them to
your field, de-dupes, and renders an HTML dashboard.

Usage:
    python -m job_finder.main
"""
from __future__ import annotations

import sys
import traceback
from datetime import datetime, timedelta, timezone

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from . import config
from concurrent.futures import ThreadPoolExecutor

from .sources import greenhouse, lever, adzuna, ashby, workday
from .dedupe import dedupe_jobs
from .report import render_report


def matches_keywords(title: str, keywords: list[str]) -> bool:
    t = title.lower()
    return any(k.lower() in t for k in keywords)


def parse_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def is_recent_enough(posted_at_raw, max_age_days: int) -> bool:
    dt = parse_date(posted_at_raw)
    if dt is None:
        return True  # unknown date — keep it rather than silently drop it
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    return dt >= cutoff


_FETCHERS = {"greenhouse": greenhouse.fetch_jobs, "lever": lever.fetch_jobs, "ashby": ashby.fetch_jobs}
_MAX_WORKERS = 8
_WORKDAY_TERMS_CAP = 5


def _fetch_company(c: dict, terms: list[str] | None = None, max_pages: int = 2) -> list[dict]:
    try:
        if c["ats"] == "workday":
            jobs = workday.fetch_jobs(
                c["slug"], host=c["host"], site=c["site"],
                terms=(terms or config.ADZUNA_SEARCH_TERMS)[:_WORKDAY_TERMS_CAP], max_pages=max_pages,
            )
        elif c["ats"] in _FETCHERS:
            jobs = _FETCHERS[c["ats"]](c["slug"])
        else:
            print(f"  skip {c['name']}: unknown ATS '{c['ats']}'", file=sys.stderr)
            return []
    except Exception as e:
        print(f"  warn: failed to fetch {c['name']} ({c['ats']}): {e}", file=sys.stderr)
        return []
    for j in jobs:
        j["company"] = c["name"]
    return jobs


def _fetch_many(companies: list[dict], **kwargs) -> list[list[dict]]:
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        return list(pool.map(lambda c: _fetch_company(c, **kwargs), companies))


def collect_company_jobs(keywords: list[str] | None = None) -> list[dict]:
    keywords = keywords or config.KEYWORDS
    all_jobs = []
    results = _fetch_many(config.COMPANIES, terms=keywords if keywords is not config.KEYWORDS else None)
    for c, jobs in zip(config.COMPANIES, results):
        matched = [j for j in jobs if matches_keywords(j["title"], keywords)]
        print(f"  {c['name']}: {len(jobs)} total postings, {len(matched)} matched your field")
        all_jobs.extend(matched)
    return all_jobs


def collect_district_jobs() -> list[dict]:
    """Every posting from the district companies located in the district's city."""
    all_jobs = []
    results = _fetch_many(config.DISTRICT_COMPANIES, terms=["New York"], max_pages=5)
    for c, jobs in zip(config.DISTRICT_COMPANIES, results):
        local = [
            j for j in jobs
            if any(t in (j.get("location") or "").lower() for t in config.DISTRICT_LOCATION_TERMS)
        ]
        print(f"  {c['name']}: {len(jobs)} total postings, {len(local)} in {config.DISTRICT_NAME}")
        all_jobs.extend(local)
    return all_jobs


def collect_adzuna_jobs(terms: list[str] | None = None) -> list[dict]:
    all_jobs = []
    try:
        for term in (terms or config.ADZUNA_SEARCH_TERMS):
            jobs = adzuna.fetch_jobs(
                search_term=term,
                country=config.ADZUNA_COUNTRY,
                results_per_page=config.ADZUNA_RESULTS_PER_PAGE,
                max_pages=config.ADZUNA_MAX_PAGES,
                location=config.ADZUNA_LOCATION,
            )
            print(f"  Adzuna '{term}': {len(jobs)} postings")
            all_jobs.extend(jobs)
    except RuntimeError as e:
        print(f"  skipping Adzuna: {e}", file=sys.stderr)
    except Exception as e:
        print(f"  warn: Adzuna fetch failed: {e}", file=sys.stderr)
    return all_jobs


def collect_all_jobs(log=print, keywords=None, adzuna_terms=None) -> list[dict]:
    """Runs the full collection pipeline and returns deduped, filtered jobs.

    Shared by the CLI report (below) and the web dashboard.
    """
    log("Fetching from company career pages (Greenhouse / Lever)...")
    company_jobs = collect_company_jobs(keywords)

    log("Fetching from Adzuna (aggregator)...")
    adzuna_jobs = collect_adzuna_jobs(adzuna_terms)

    all_jobs = company_jobs + adzuna_jobs
    all_jobs = [j for j in all_jobs if is_recent_enough(j.get("posted_at"), config.MAX_JOB_AGE_DAYS)]
    all_jobs = dedupe_jobs(all_jobs)

    def sort_key(j):
        return parse_date(j.get("posted_at")) or datetime.min.replace(tzinfo=timezone.utc)

    all_jobs.sort(key=sort_key, reverse=True)
    return all_jobs


def main():
    all_jobs = collect_all_jobs()
    print(f"{len(all_jobs)} jobs after de-duping and age filter (<= {config.MAX_JOB_AGE_DAYS} days)")

    render_report(all_jobs, config.OUTPUT_HTML)
    print(f"\nReport written to {config.OUTPUT_HTML}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
