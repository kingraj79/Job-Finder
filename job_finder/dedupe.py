"""De-duplication for jobs pulled from multiple sources."""
from __future__ import annotations


def dedupe_jobs(jobs: list[dict]) -> list[dict]:
    """Drop repeat postings (same title + company) seen across sources."""
    seen = set()
    unique = []
    for j in jobs:
        key = (
            (j.get("title") or "").strip().lower(),
            (j.get("company") or "").strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(j)
    return unique
