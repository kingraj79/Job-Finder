"""Web dashboard: browse matched jobs, draft applications, track status.

This app never submits anything to an employer or third-party site on its
own — every application is drafted here for you to review, edit, and send
yourself. Status changes (drafted/approved/applied/...) are things *you*
record after taking that action yourself.

Run with:
    uvicorn job_finder.webapp:app --reload
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import math
from datetime import datetime, timezone
from urllib.parse import urlencode

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from . import chat as chatlib
from . import importer
from . import config, db
from .classify import ROLE_LABELS, is_internship, role_category
from .difficulty import LABELS
from .drafting import generate_draft
from .main import collect_all_jobs, collect_district_jobs
from .matching import score_job
from .resume import ResumeError, extract_profile, extract_text

app = FastAPI(title="Job Finder")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
templates.env.globals.update(status_labels=db.STATUS_LABELS, category_of=db.category_of)

db.init_db()


def _linkedin_search_url(profile) -> str | None:
    titles = [t.strip() for t in (profile["target_titles"] or "").split(",") if t.strip()]
    if not titles:
        return None
    params = {"keywords": titles[0]}
    if profile["location"]:
        params["location"] = profile["location"]
    return "https://www.linkedin.com/jobs/search/?" + urlencode(params)


_EPOCH = datetime.min.replace(tzinfo=timezone.utc)


def _posted_dt(raw):
    if not raw:
        return _EPOCH
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return _EPOCH
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _prep(rows) -> list[dict]:
    out = []
    for r in rows:
        d = dict(r)
        dt = _posted_dt(d.get("posted_at"))
        d["posted_dt"] = dt
        d["posted_str"] = dt.strftime("%b %d, %Y") if dt != _EPOCH else "Unknown"
        d["difficulty_label"] = LABELS.get(d.get("difficulty") or 3, "Mid")
        d["role"] = role_category(d["title"])
        d["is_intern"] = is_internship(d["title"])
        out.append(d)
    return out


def _profile_titles(profile) -> list[str]:
    return [t.strip() for t in (profile["target_titles"] or "").split(",") if t.strip()]


def _run_search(conn) -> tuple[int, int]:
    """Search for jobs using the profile's target titles; returns (new, scanned)."""
    profile = db.get_profile(conn)
    titles = _profile_titles(profile)
    jobs = collect_all_jobs(
        log=lambda *_: None, keywords=titles or None, adzuna_terms=titles[:5] or None
    )
    new_count = 0
    for job in jobs:
        score, matched = score_job(profile, job)
        _, is_new = db.upsert_job(conn, job, score, matched)
        new_count += is_new
    return new_count, len(jobs)


def _indeed_search_url(profile) -> str | None:
    titles = _profile_titles(profile)
    if not titles:
        return None
    params = {"q": titles[0]}
    if profile["location"]:
        params["l"] = profile["location"]
    return "https://www.indeed.com/jobs?" + urlencode(params)


PAGE_SIZE = 30


@app.get("/")
def dashboard(
    request: Request, sort: str = "newest", relevant: str = "", tab: str = "review",
    q: str = "", company: str = "", page: int = 1, level: str = "", role: str = "",
):
    with db.get_conn() as conn:
        profile = db.get_profile(conn)
        all_jobs = _prep(db.list_jobs_with_status(conn))
        counts = db.counts_by_category(conn)

    valid_tabs = {k for k, _l, _s in db.CATEGORIES}
    tab = tab if tab == "all" or tab in valid_tabs else "review"
    sort = sort if sort in ("match", "easiest", "hardest") else "newest"

    jobs = all_jobs if tab == "all" else [j for j in all_jobs if db.category_of(j["app_status"]) == tab]
    if relevant:
        titles = [t.lower() for t in _profile_titles(profile)]
        jobs = [j for j in jobs if any(t in j["title"].lower() for t in titles)]
    words = q.lower().split()
    if words:
        jobs = [j for j in jobs if all(w in (j["title"] + " " + j["company"]).lower() for w in words)]
    companies = sorted({j["company"] for j in jobs})
    if company:
        jobs = [j for j in jobs if j["company"] == company]

    level = level if level in ("1", "2", "3", "4", "5", "intern") else ""
    role = role if role in ROLE_LABELS else ""
    level_counts = {"intern": sum(1 for j in jobs if j["is_intern"])}
    for n in range(1, 6):
        level_counts[str(n)] = sum(1 for j in jobs if j["difficulty"] == n)
    role_counts = {r: sum(1 for j in jobs if j["role"] == r) for r in ROLE_LABELS}
    if level == "intern":
        jobs = [j for j in jobs if j["is_intern"]]
    elif level:
        jobs = [j for j in jobs if j["difficulty"] == int(level)]
    if role:
        jobs = [j for j in jobs if j["role"] == role]

    if sort == "match":
        jobs.sort(key=lambda j: (j["match_score"], j["posted_dt"]), reverse=True)
    elif sort in ("easiest", "hardest"):
        jobs.sort(key=lambda j: j["posted_dt"], reverse=True)
        jobs.sort(key=lambda j: j["difficulty"], reverse=(sort == "hardest"))
    else:
        jobs.sort(key=lambda j: j["posted_dt"], reverse=True)

    total = len(jobs)
    pages = max(1, math.ceil(total / PAGE_SIZE))
    page = min(max(page, 1), pages)
    state = {"tab": tab, "sort": sort, "relevant": "1" if relevant else "", "q": q, "company": company,
             "level": level, "role": role, "page": page}

    def link(**over):
        merged = {**state, **over}
        if "page" not in over:
            merged["page"] = 1
        return "/?" + urlencode({k: v for k, v in merged.items() if v not in ("", None) and not (k == "page" and v == 1)})

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "profile": profile,
            "jobs": jobs[(page - 1) * PAGE_SIZE: page * PAGE_SIZE],
            "total": total, "page": page, "pages": pages,
            "counts": counts, "tab": tab, "categories": db.CATEGORIES,
            "sort": sort, "relevant": bool(relevant), "q": q, "company": company,
            "level": level, "role": role, "level_counts": level_counts, "role_counts": role_counts,
            "level_labels": LABELS, "role_labels": ROLE_LABELS,
            "companies": companies, "link": link,
            "needs_resume": not _profile_titles(profile),
            "linkedin_url": _linkedin_search_url(profile),
            "indeed_url": _indeed_search_url(profile),
            "career_sites": config.CAREER_SITES,
            "chat_greeting": chatlib.GREETING,
        },
    )


_GROUPS = [
    ("big_tech", "Big tech", "Product and platform companies"),
    ("banks", "Banks and asset managers", "Pulled from each bank's Workday careers feed"),
    ("finance", "Finance, trading and fintech", "Includes the Financial District list"),
    ("other", "Other tracked employers", ""),
]
_PALETTE = ["#4f46e5", "#0891b2", "#16a34a", "#d97706", "#dc2626", "#7c3aed", "#0d9488", "#be185d"]


def _color(name: str) -> str:
    return _PALETTE[int(hashlib.md5(name.encode()).hexdigest(), 16) % len(_PALETTE)]


@app.get("/employers")
def employers(request: Request):
    with db.get_conn() as conn:
        jobs = _prep(db.list_jobs_with_status(conn))
    by_company: dict[str, list[dict]] = {}
    for j in jobs:
        by_company.setdefault(j["company"], []).append(j)

    district_names = {c["name"] for c in config.DISTRICT_COMPANIES}
    names = [c["name"] for c in config.COMPANIES] + [c["name"] for c in config.DISTRICT_COMPANIES]
    names = list(dict.fromkeys(names))

    def group_of(n):
        if n in config.BANK_COMPANIES:
            return "banks"
        if n in config.BIG_TECH_COMPANIES:
            return "big_tech"
        if n in district_names or n in {"Robinhood", "Coinbase", "Affirm"}:
            return "finance"
        return "other"

    cards = {key: [] for key, _t, _d in _GROUPS}
    for n in names:
        js = sorted(by_company.get(n, []), key=lambda j: j["posted_dt"], reverse=True)
        cards[group_of(n)].append({
            "name": n, "count": len(js), "color": _color(n),
            "newest": js[0]["posted_str"] if js else "",
            "entry": sum(1 for j in js if j["difficulty"] <= 2),
            "top": [j["title"] for j in js[:3]],
            "href": "/?" + urlencode({"tab": "all", "company": n}),
        })
    for lst in cards.values():
        lst.sort(key=lambda c: c["count"], reverse=True)

    ranked = sorted((c for lst in cards.values() for c in lst if c["count"]), key=lambda c: c["count"], reverse=True)[:12]
    return templates.TemplateResponse(
        request,
        "employers.html",
        {
            "groups": [(k, t, d, cards[k]) for k, t, d in _GROUPS if cards[k]],
            "chart": ranked,
            "chart_max": ranked[0]["count"] if ranked else 1,
            "no_feed": [{"name": n, "url": u, "color": _color(n)} for n, u in config.CAREER_SITES],
        },
    )


@app.get("/import")
def import_page(request: Request):
    with db.get_conn() as conn:
        profile = db.get_profile(conn)
    return templates.TemplateResponse(
        request,
        "import.html",
        {"linkedin_url": _linkedin_search_url(profile), "indeed_url": _indeed_search_url(profile)},
    )


_IMPORT_STATUS = {"new": "new", "saved": "saved", "applied": "applied", "not_applied": "not_applied"}


@app.post("/import/job")
def import_job(
    title: str = Form(""), company: str = Form(""), url: str = Form(""), location: str = Form(""),
    description: str = Form(""), status: str = Form("saved"),
):
    title, company = title.strip()[:200], company.strip()[:120]
    if not title or not company:
        return RedirectResponse("/import?msg=Job title and company are required.", status_code=303)
    status = _IMPORT_STATUS.get(status, "saved")
    clean_url = importer.safe_url(url)
    job = {
        "title": title, "company": company, "url": clean_url, "location": location.strip()[:120],
        "source": importer.source_for(clean_url), "description": description.strip()[:20000],
        "posted_at": datetime.now(timezone.utc).isoformat(),
    }
    with db.get_conn() as conn:
        profile = db.get_profile(conn)
        score, kws = score_job(profile, job)
        jid, _ = db.upsert_job(conn, job, score, kws)
        db.set_status(conn, jid, status)
    return RedirectResponse(f"/?tab={db.category_of(status)}&msg=Added {title} at {company}.", status_code=303)


@app.post("/import/csv")
def import_csv(file: UploadFile = File(...), kind: str = Form("saved")):
    data = file.file.read(importer.MAX_CSV_BYTES + 1)
    try:
        rows = importer.parse_csv(data)
    except importer.ImportError_ as e:
        return RedirectResponse(f"/import?msg={e}", status_code=303)
    status = "applied" if kind == "applied" else "saved"
    with db.get_conn() as conn:
        profile = db.get_profile(conn)
        for job in rows:
            score, kws = score_job(profile, job)
            jid, _ = db.upsert_job(conn, job, score, kws)
            db.set_status(conn, jid, status)
    return RedirectResponse(f"/?tab={status}&msg=Imported {len(rows)} jobs from LinkedIn as {status}.", status_code=303)


@app.get("/district")
def district(request: Request, order: str = "easiest"):
    with db.get_conn() as conn:
        jobs = _prep([r for r in db.list_jobs_with_status(conn) if r["district"]])
    hardest_first = order == "hardest"
    jobs.sort(key=lambda j: j["posted_dt"], reverse=True)  # newest first within a level
    jobs.sort(key=lambda j: j["difficulty"], reverse=hardest_first)
    companies = sorted({j["company"] for j in jobs})
    return templates.TemplateResponse(
        request,
        "district.html",
        {
            "jobs": jobs,
            "companies": companies,
            "district_name": config.DISTRICT_NAME,
            "order": "hardest" if hardest_first else "easiest",
            "labels": LABELS,
        },
    )


@app.post("/district/refresh")
def district_refresh():
    jobs = collect_district_jobs()
    with db.get_conn() as conn:
        profile = db.get_profile(conn)
        new_count = 0
        for job in jobs:
            score, matched = score_job(profile, job)
            _, is_new = db.upsert_job(conn, job, score, matched, district=config.DISTRICT_NAME)
            new_count += is_new
    return RedirectResponse(
        f"/district?msg={len(jobs)} {config.DISTRICT_NAME} postings scanned ({new_count} new)", status_code=303
    )


def _ingest_resume(conn, filename: str, data: bytes) -> dict:
    """Saves resume text + detected profile fields. Raises ResumeError on a bad file."""
    text = extract_text(filename, data)
    found = extract_profile(text)
    profile = db.get_profile(conn)
    db.save_profile(
        conn,
        {
            "resume_text": text,
            "name": profile["name"] or found["name"],
            "email": profile["email"] or found["email"],
            "phone": profile["phone"] or found["phone"],
            "skills": ", ".join(found["skills"]) or profile["skills"],
            "target_titles": ", ".join(found["titles"]) or profile["target_titles"],
        },
    )
    return found


@app.post("/resume")
def resume_upload(resume: UploadFile = File(...)):
    data = resume.file.read(5 * 1024 * 1024 + 1)
    with db.get_conn() as conn:
        try:
            found = _ingest_resume(conn, resume.filename or "", data)
        except ResumeError as e:
            return RedirectResponse(f"/profile?msg={e}", status_code=303)
        profile = db.get_profile(conn)
        if not _profile_titles(profile):
            return RedirectResponse(
                "/profile?msg=Resume saved, but no job titles were detected — add your target "
                "titles below, then click Refresh jobs.",
                status_code=303,
            )
        new_count, scanned = _run_search(conn)
    return RedirectResponse(
        f"/?sort=newest&relevant=1&msg=Resume processed: {len(found['skills'])} skills and "
        f"{len(found['titles'])} titles detected. {new_count} new jobs ({scanned} scanned), newest first.",
        status_code=303,
    )


CHAT_LIMIT = 25


def _job_cards(jobs: list[dict]) -> list[dict]:
    return [
        {
            "id": j["id"], "title": j["title"], "company": j["company"], "location": j["location"] or "",
            "posted": j["posted_str"], "difficulty": j["difficulty"], "difficulty_label": j["difficulty_label"],
            "match": j["match_score"], "status": j["app_status"],
        }
        for j in jobs[:CHAT_LIMIT]
    ]


def _chat_result(reply: str, jobs: list[dict], total: int | None = None) -> dict:
    return {"reply": reply, "jobs": _job_cards(jobs), "total": len(jobs) if total is None else total}


@app.post("/chat")
def chat(message: str = Form(...)):
    message = message.strip()[:500]
    q = chatlib.parse_query(message)
    if q["explain"]:
        return _chat_result(chatlib.EXPLAIN, [])

    with db.get_conn() as conn:
        profile = db.get_profile(conn)
        profile_titles = _profile_titles(profile)
        profile_skills = [s.strip() for s in (profile["skills"] or "").split(",") if s.strip()]
        if not chatlib.has_criteria(q) and not q["use_profile"]:
            return _chat_result("I didn't catch what to look for. " + chatlib.GREETING, [])
        if q["use_profile"] and not (profile_titles or profile_skills or q["titles"] or q["freeform"]):
            return _chat_result("I don't have your resume yet — upload it with the button below and I'll use it.", [])

        jobs = _prep(db.list_jobs_with_status(conn))
        matches = chatlib.filter_jobs(jobs, q, profile_titles, profile_skills)

        fetched = False
        wanted = q["titles"] + q["freeform"]
        if len(matches) < 5 and wanted:
            fresh = collect_all_jobs(log=lambda *_: None, keywords=wanted, adzuna_terms=wanted[:5])
            for job in fresh:
                score, kws = score_job(profile, job)
                db.upsert_job(conn, job, score, kws)
            fetched = True
            jobs = _prep(db.list_jobs_with_status(conn))
            matches = chatlib.filter_jobs(jobs, q, profile_titles, profile_skills)

    what = chatlib.describe(q) if not (q["use_profile"] and not (q["titles"] or q["freeform"] or q["skills"])) \
        else "matching your profile"
    if not matches:
        return _chat_result(
            f"No tracked jobs found {what}. Try fewer filters, or a broader title.", [])
    shown = min(len(matches), CHAT_LIMIT)
    extra = " I searched live for fresh postings too." if fetched else ""
    return _chat_result(f"Found {len(matches)} jobs {what}, newest first. Showing {shown}.{extra}", matches)


@app.post("/chat/resume")
def chat_resume(resume: UploadFile = File(...)):
    data = resume.file.read(5 * 1024 * 1024 + 1)
    with db.get_conn() as conn:
        try:
            found = _ingest_resume(conn, resume.filename or "", data)
        except ResumeError as e:
            return _chat_result(str(e), [])
        profile = db.get_profile(conn)
        titles = _profile_titles(profile)
        if not titles:
            return _chat_result(
                f"I read your resume ({len(found['skills'])} skills found) but couldn't spot a job title. "
                "Tell me what roles you want, e.g. \"data analyst jobs\".", [])
        new_count, scanned = _run_search(conn)
        jobs = _prep(db.list_jobs_with_status(conn))
        low = [t.lower() for t in titles]
        matches = [j for j in jobs if any(t in j["title"].lower() for t in low)]
        matches.sort(key=lambda j: j["posted_dt"], reverse=True)
    reply = (
        f"Read your resume: {len(found['skills'])} skills ({', '.join(found['skills'][:8])}"
        f"{'...' if len(found['skills']) > 8 else ''}) and titles: {', '.join(titles)}. "
        f"Found {len(matches)} relevant jobs ({new_count} new), newest first. Showing {min(len(matches), CHAT_LIMIT)}."
    )
    return _chat_result(reply, matches)


@app.get("/profile")
def profile_form(request: Request):
    with db.get_conn() as conn:
        profile = db.get_profile(conn)
    return templates.TemplateResponse(request, "profile.html", {"profile": profile})


@app.post("/profile")
def profile_save(
    name: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    location: str = Form(""),
    portfolio_url: str = Form(""),
    linkedin_url: str = Form(""),
    target_titles: str = Form(""),
    skills: str = Form(""),
    resume_text: str = Form(""),
):
    with db.get_conn() as conn:
        db.save_profile(
            conn,
            {
                "name": name, "email": email, "phone": phone, "location": location,
                "portfolio_url": portfolio_url, "linkedin_url": linkedin_url,
                "target_titles": target_titles, "skills": skills, "resume_text": resume_text,
            },
        )
    return RedirectResponse("/profile?msg=Profile saved", status_code=303)


@app.post("/refresh")
def refresh():
    with db.get_conn() as conn:
        new_count, scanned = _run_search(conn)
    return RedirectResponse(f"/?msg={new_count} new jobs found ({scanned} total scanned)", status_code=303)


@app.post("/job/{job_id}/mark")
def job_mark(job_id: str, choice: str = Form(...)):
    if choice not in db.MARK_CHOICES:
        return JSONResponse({"error": "bad choice"}, status_code=400)
    with db.get_conn() as conn:
        if db.get_job(conn, job_id) is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        db.set_status(conn, job_id, choice)
        counts = db.counts_by_category(conn)
    return {
        "status": choice,
        "label": db.STATUS_LABELS[choice],
        "category": db.category_of(choice),
        "counts": counts,
    }


@app.get("/job/{job_id}")
def job_detail(request: Request, job_id: str):
    with db.get_conn() as conn:
        job = db.get_job(conn, job_id)
    if job is None:
        return RedirectResponse("/?msg=Job not found", status_code=303)
    return templates.TemplateResponse(
        request, "job_detail.html", {"job": job, "statuses": db.STATUSES}
    )


@app.post("/job/{job_id}/draft")
def job_draft(job_id: str, draft_text: str = Form(""), save_only: str = Form("")):
    with db.get_conn() as conn:
        job = db.get_job(conn, job_id)
        if job is None:
            return RedirectResponse("/?msg=Job not found", status_code=303)

        if save_only:
            db.set_draft(conn, job_id, draft_text)
        else:
            profile = db.get_profile(conn)
            matched = job["matched_keywords"].split(",") if job["matched_keywords"] else []
            draft = generate_draft(profile, dict(job), matched)
            db.set_draft(conn, job_id, draft)
    return RedirectResponse(f"/job/{job_id}", status_code=303)


@app.post("/job/{job_id}/status")
def job_status(job_id: str, status: str = Form(...), notes: str = Form("")):
    with db.get_conn() as conn:
        db.set_status(conn, job_id, status, notes)
    return RedirectResponse(f"/job/{job_id}", status_code=303)
