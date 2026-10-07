"""Turns a plain-English request ("entry level data jobs at banks in New York this week")
into filters over the tracked jobs.

Rule-based on purpose: no API key needed, and the filters it understood are echoed
back to the user so a misread request is obvious rather than silent.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from . import config
from .resume import SKILL_VOCAB, TITLE_VOCAB

STOP = set("""a an the and or of to for in at on with me my i find show get give list search looking look want need
jobs job roles role positions position openings opening please can you any some all that are is be from new latest
newest recent recently posted relevant matching match matches work working near around about hiring companies company
what where which who how do does it its this these those only just top best good""".split())

LOCATIONS = {
    "new york": ["new york", "nyc", "manhattan"], "nyc": ["new york", "nyc", "manhattan"],
    "san francisco": ["san francisco"], "sf": ["san francisco"], "seattle": ["seattle"], "austin": ["austin"],
    "boston": ["boston"], "chicago": ["chicago"], "london": ["london"], "toronto": ["toronto"],
    "los angeles": ["los angeles"], "remote": ["remote"], "singapore": ["singapore"],
}
SENIORITY = [
    (r"\b(intern|internship|interns)\b", (1, 1), "internships"),
    (r"\b(entry[- ]level|junior|jr|new grad|graduate|early career|beginner|easy|easiest)\b", (1, 2), "entry level"),
    (r"\b(mid[- ]level|intermediate)\b", (3, 3), "mid level"),
    (r"\b(senior|sr|experienced|hard|hardest)\b", (4, 5), "senior"),
    (r"\b(staff|principal|director|executive|leadership)\b", (5, 5), "staff and above"),
]
RESERVED = {
    "bank", "banks", "banking", "tech", "big", "fintech", "finance", "financial", "district", "fidi", "wall",
    "street", "intern", "internship", "junior", "senior", "entry", "level", "graduate", "easy", "hard",
    "today", "week", "month", "days", "day", "last", "past", "resume", "profile", "faang", "trading",
    "remote", "mid", "staff", "principal", "director", "grad", "early", "career",
}
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+#.&/-]*")


def _has_term(text: str, term: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(term) + r"s?(?![a-z0-9])", text) is not None


def parse_query(message: str) -> dict:
    text = message.lower().strip()
    q: dict = {
        "titles": [t for t in TITLE_VOCAB if _has_term(text, t)],
        "skills": [s for s in SKILL_VOCAB if _has_term(text, s)],
        "freeform": [], "locations": [], "location_label": "", "difficulty": None, "difficulty_label": "",
        "group": None, "max_age_days": None, "use_profile": False, "explain": False,
    }

    q["skills"] = [sk for sk in q["skills"] if not any(sk in t for t in q["titles"])]
    q["explain"] = bool(re.search(r"\bhow\b.*\b(match|score|know|work)", text))
    q["use_profile"] = bool(re.search(r"\b(my resume|my profile|my skills|for me|match me|suit me|relevant to me|about me)\b", text))

    for pattern, rng, label in SENIORITY:
        if re.search(pattern, text):
            q["difficulty"], q["difficulty_label"] = rng, label
            break

    if re.search(r"\b(banks?|banking)\b", text):
        q["group"] = "banks"
    elif re.search(r"\b(big tech|faang|tech giants?)\b", text):
        q["group"] = "big_tech"
    elif re.search(r"\b(fintech|trading|financial district|fidi|wall street)\b", text):
        q["group"] = "district"

    consumed: set[str] = set()
    for name, terms in LOCATIONS.items():
        if _has_term(text, name):
            q["locations"], q["location_label"] = terms, name.title() if name != "nyc" else "New York"
            consumed.update(name.split())
            break
    else:
        m = re.search(r"\b(?:in|near|around)\s+([a-z][a-z .]{2,24}?)(?=\s+(?:at|for|with|that|and|jobs?|roles?|posted|this|last)\b|[.,?!]|$)", text)
        if m and not (set(m.group(1).split()) & (RESERVED | STOP)):
            q["locations"], q["location_label"] = [m.group(1).strip()], m.group(1).strip().title()
            consumed.update(m.group(1).split())

    if re.search(r"\btoday\b", text):
        q["max_age_days"] = 1
    elif re.search(r"\b(this|past|last) week\b", text):
        q["max_age_days"] = 7
    elif re.search(r"\b(this|past|last) month\b", text):
        q["max_age_days"] = 30
    elif m := re.search(r"\b(?:last|past)\s+(\d{1,3})\s+days?\b", text):
        q["max_age_days"] = int(m.group(1))

    known = {w for t in q["titles"] + q["skills"] for w in t.split()}
    for tok in _TOKEN_RE.findall(text):
        base = tok.rstrip("s") if len(tok) > 3 else tok
        if len(tok) < 2 or tok in STOP or tok in RESERVED or tok in consumed or tok.isdigit() or tok in known or base in known:
            continue
        if tok not in q["freeform"]:
            q["freeform"].append(tok)
    return q


def has_criteria(q: dict) -> bool:
    return bool(q["titles"] or q["skills"] or q["freeform"] or q["locations"] or q["group"]
                or q["difficulty"] or q["max_age_days"])


def describe(q: dict) -> str:
    parts = []
    what = q["titles"] + q["freeform"] + q["skills"]
    if what:
        parts.append("matching " + ", ".join(what))
    if q["difficulty_label"]:
        parts.append(q["difficulty_label"])
    if q["location_label"]:
        parts.append("remote" if q["location_label"] == "Remote" else "in " + q["location_label"])
    if q["group"]:
        parts.append({"banks": "at banks", "big_tech": "at big tech companies",
                      "district": "at Financial District firms"}[q["group"]])
    if q["max_age_days"]:
        parts.append(f"posted in the last {q['max_age_days']} day(s)")
    return ", ".join(parts) or "all tracked jobs"


def _in_group(job: dict, group: str | None) -> bool:
    if group is None:
        return True
    if group == "district":
        return bool(job.get("district"))
    names = config.BANK_COMPANIES if group == "banks" else config.BIG_TECH_COMPANIES
    return job["company"] in names


def filter_jobs(jobs: list[dict], q: dict, profile_titles: list[str], profile_skills: list[str]) -> list[dict]:
    titles = [t.lower() for t in q["titles"]]
    freeform = q["freeform"]
    skills = [s.lower() for s in q["skills"]]
    if q["use_profile"] and not (titles or freeform or skills):
        titles = [t.lower() for t in profile_titles]
        skills = [s.lower() for s in profile_skills] if not titles else []

    cutoff = None
    if q["max_age_days"]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=q["max_age_days"])

    out = []
    for j in jobs:
        title = j["title"].lower()
        blob = title + " " + (j.get("description") or "").lower()
        if (titles or freeform) and not (
            any(_has_term(title, t) for t in titles) or any(f in title for f in freeform)
        ):
            continue
        if skills and not any(_has_term(blob, s) for s in skills):
            continue
        if q["locations"] and not any(l in (j.get("location") or "").lower() for l in q["locations"]):
            continue
        if q["difficulty"] and not (q["difficulty"][0] <= (j.get("difficulty") or 3) <= q["difficulty"][1]):
            continue
        if not _in_group(j, q["group"]):
            continue
        if cutoff and not (j["posted_dt"] >= cutoff):
            continue
        out.append(j)
    out.sort(key=lambda j: j["posted_dt"], reverse=True)
    return out


EXPLAIN = (
    "Here's how matching works. Your resume or profile gives me a list of skills and target job titles. "
    "For each job, the Match % is the share of those keywords found in the job's title and description, "
    "plus a 15-point bonus for each target title that appears in the job title. It's keyword overlap, not "
    "understanding, so it can't tell a core requirement from a passing mention. Bank jobs (Workday) have no "
    "description text, so their score comes from the title alone. Difficulty (1-5) comes from title seniority "
    "and the years of experience a posting asks for."
)

GREETING = (
    "Upload your resume with the button below and I'll read your skills and titles, then find relevant jobs, "
    "newest first. Or just ask, for example: \"entry level data jobs at banks in New York this week\", "
    "\"senior backend engineer remote\", or \"jobs for me\"."
)
