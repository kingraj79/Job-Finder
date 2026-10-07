"""Scores a job posting against the user's profile.

Deliberately simple keyword overlap rather than an ML model — transparent,
fast, no external calls, and easy for you to see *why* something scored
the way it did (the matched keyword list is shown in the UI).
"""
from __future__ import annotations

import re

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9+#.\-]*")


def _tokenize(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def _split_csv(value: str) -> list[str]:
    return [v.strip() for v in (value or "").split(",") if v.strip()]


def profile_keywords(profile) -> list[str]:
    skills = _split_csv(profile["skills"])
    titles = _split_csv(profile["target_titles"])
    return skills + titles


def score_job(profile, job: dict) -> tuple[int, list[str]]:
    """Returns (score 0-100, matched keyword phrases)."""
    keywords = profile_keywords(profile)
    if not keywords:
        return 0, []

    blob = f"{job.get('title', '')} {job.get('description', '')}".lower()
    title = job.get("title", "").lower()

    matched = []
    hits = 0
    for kw in keywords:
        kw_l = kw.lower()
        if re.search(r"(?<![a-z0-9])" + re.escape(kw_l) + r"(?![a-z0-9])", blob):
            hits += 1
            matched.append(kw)

    title_bonus = 0
    for t in _split_csv(profile["target_titles"]):
        if t.lower() in title:
            title_bonus += 15

    raw = (hits / len(keywords)) * 100 + title_bonus
    return min(100, round(raw)), matched
