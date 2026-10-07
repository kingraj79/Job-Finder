"""Sorts a job into a broad role type from its title, for the dashboard's "Role type" filter.

First matching rule wins, so order matters (e.g. "Product Designer" is Design, not Product).
"""
from __future__ import annotations

import re

ROLE_RULES = [
    ("Security", r"security|cyber|infosec|appsec|threat|fraud"),
    ("Design", r"design|\bux\b|\bui\b|creative|brand"),
    ("Product", r"product manager|product owner|product lead|head of product|program manager|technical program|\bpm\b"),
    ("Quant & Trading", r"quant|trader|trading|market mak|portfolio|researcher"),
    ("Data, ML & AI", r"data scien|data engineer|data analy|analytics|machine learning|\bml\b|\bai\b|\bllm\b|deep learning|research scien"),
    ("Finance & Analysis", r"financ|accountant|accounting|accounts (?:payable|receivable)|audit|\btax\b|treasury|\brisk\b|credit|underwrit|controller|compliance|analyst|\bfp&a\b|actuar|investment|banking"),
    ("Engineering", r"engineer|developer|software|\bswe\b|\bsre\b|devops|architect|infrastructure|platform|backend|back-end|frontend|front-end|full[- ]stack|mobile|\bios\b|android|\bqa\b|firmware|hardware|systems|technician"),
    ("Sales & Marketing", r"sales|account executive|account manager|marketing|growth|partnership|business development|customer success|solutions consult|advertis|communications|\bpr\b"),
    ("Operations & People", r"operations|recruit|people|talent|\bhr\b|legal|counsel|workplace|facilities|supply|procurement|support|administrative|coordinator|executive assistant"),
]
ROLE_LABELS = [label for label, _ in ROLE_RULES] + ["Other"]
_COMPILED = [(label, re.compile(pattern, re.I)) for label, pattern in ROLE_RULES]
_INTERN_RE = re.compile(r"\b(intern|interns|internship|apprentice|co-?op)\b", re.I)


def role_category(title: str) -> str:
    for label, rx in _COMPILED:
        if rx.search(title or ""):
            return label
    return "Other"


def is_internship(title: str) -> bool:
    return bool(_INTERN_RE.search(title or ""))
