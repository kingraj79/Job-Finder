"""Generates a draft cover letter for a job.

This only ever produces a *draft* for you to review, edit, and send
yourself — nothing in this app submits an application on your behalf.

If ANTHROPIC_API_KEY is set (and the `anthropic` package is installed),
uses Claude to write a tailored draft. Otherwise falls back to a plain
template built from your profile and the matched keywords, so the app
works fully offline with zero extra setup.
"""
from __future__ import annotations

import os

MODEL = "claude-sonnet-5"


def _template_draft(profile, job: dict, matched_keywords: list[str]) -> str:
    name = profile["name"] or "[Your Name]"
    title = job.get("title", "this role")
    company = job.get("company", "your company")
    highlight = ", ".join(matched_keywords[:6]) or "the skills listed in the posting"

    resume_snippet = (profile["resume_text"] or "").strip()
    experience_line = (
        f"In my recent work, {resume_snippet.splitlines()[0]}"
        if resume_snippet
        else "My background lines up closely with what you're looking for."
    )

    return f"""Dear {company} Hiring Team,

I'm writing to apply for the {title} position at {company}. {experience_line}

My experience with {highlight} maps directly onto what this role needs, and I'd welcome \
the chance to bring that to your team.

I've attached my resume with more detail on my background. I'd love to talk about how I \
can contribute to {company}.

Sincerely,
{name}

---
DRAFT — edit before sending. Generated from your profile keywords; review for accuracy \
before you submit this anywhere.""".strip()


def _claude_draft(profile, job: dict, matched_keywords: list[str]) -> str | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic
    except ImportError:
        return None

    client = anthropic.Anthropic(api_key=api_key)
    prompt = f"""Write a concise, specific cover letter (under 250 words) for this candidate \
applying to this job. No generic filler, no exaggerated claims beyond what's given. Plain \
text, no markdown.

CANDIDATE PROFILE
Name: {profile['name']}
Target roles: {profile['target_titles']}
Skills: {profile['skills']}
Resume / background:
{profile['resume_text']}

JOB
Title: {job.get('title')}
Company: {job.get('company')}
Location: {job.get('location')}
Description:
{(job.get('description') or '')[:4000]}

Matched keywords between candidate and job: {', '.join(matched_keywords) or 'none found'}
"""
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in resp.content if block.type == "text").strip()
        return text or None
    except Exception:
        return None


def generate_draft(profile, job: dict, matched_keywords: list[str]) -> str:
    return _claude_draft(profile, job, matched_keywords) or _template_draft(
        profile, job, matched_keywords
    )
