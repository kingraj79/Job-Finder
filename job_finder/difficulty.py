"""Rates how hard a job is to land, from 1 (entry) to 5 (expert / leadership).

Transparent heuristic, not a model: it combines the seniority words in the
title with the years of experience the posting asks for, and returns the
reasons so the UI can show *why* a job got its rating.
"""
from __future__ import annotations

import re

LABELS = {1: "Entry", 2: "Early", 3: "Mid", 4: "Senior", 5: "Expert / Leadership"}

_TITLE_LEVELS = [
    (1, r"\b(intern|internship|apprentice|new grad|graduate|entry[- ]level|junior|jr\.?)\b"),
    (5, r"\b(director|vp|vice president|head of|chief|cto|principal|distinguished|fellow)\b"),
    (4, r"\b(senior|sr\.?|staff|lead|manager|architect)\b"),
    (2, r"\b(associate|analyst|engineer i|developer i|level 1)\b"),
]

_YEARS_RE = re.compile(r"(\d{1,2})\s*\+?\s*(?:-|to|–)?\s*(?:\d{1,2}\s*)?\+?\s*years?", re.I)


def _title_level(title: str) -> int | None:
    t = title.lower()
    for level, pattern in _TITLE_LEVELS:
        if re.search(pattern, t):
            return level
    return None


def _years_required(description: str) -> int | None:
    """Years of experience asked for — only mentions near the word 'experience',
    so company-history lines like "founded 20 years ago" don't count."""
    text = description or ""
    years = []
    for m in _YEARS_RE.finditer(text):
        window = text[max(0, m.start() - 60): m.end() + 60].lower()
        if "experience" in window or "exposure" in window:
            years.append(int(m.group(1)))
    years = [y for y in years if 0 < y <= 15]
    return max(years) if years else None


def _years_level(years: int) -> int:
    if years <= 1:
        return 1
    if years <= 3:
        return 2
    if years <= 5:
        return 3
    if years <= 8:
        return 4
    return 5


def rate_job(title: str, description: str) -> tuple[int, str]:
    """Returns (difficulty 1-5, short human-readable reason)."""
    title_level = _title_level(title or "")
    years = _years_required(description or "")
    years_level = _years_level(years) if years is not None else None

    signals = [lvl for lvl in (title_level, years_level) if lvl is not None]
    reasons = []
    if title_level is not None:
        reasons.append(f"title level {title_level}")
    if years is not None:
        reasons.append(f"asks for up to {years} yrs experience")

    if not signals:
        return 3, "no seniority signals found, assumed mid-level"

    # Title is the stronger signal: a "Principal" role is hard regardless of the
    # years quoted; blend the two otherwise.
    if title_level in (1, 5):
        score = title_level
    else:
        score = round(sum(signals) / len(signals))
    return max(1, min(5, score)), "; ".join(reasons)
