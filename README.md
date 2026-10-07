# job-finder

Pulls fresh job postings relevant to your field from real employer sources,
scores them against your profile, and gives you a dashboard to draft
tailored applications and track where you stand with each one.

**This tool never submits anything on your behalf.** It finds jobs, scores
them, and helps you draft a cover letter — you review, edit, and actually
apply yourself on the employer's site. Status tracking (drafted / approved /
applied / ...) is something you record after taking that action.

## Quick start

You need Python 3 installed. Then, from this folder:

```bash
./start.sh
```

The first run creates a virtual environment, installs everything, and copies `.env.example` to `.env`.
After that it launches the app. Open **http://localhost:8000**, then:

1. Click **Upload resume** in the chat box (PDF, DOCX or TXT). The app reads your skills and job titles.
2. Wait 20-30 seconds while it searches company career sites. Matching jobs appear newest first.
3. Click **Applied**, **Saved** or **Did not apply** on each job to sort it into a tab.

Press `Ctrl+C` in the terminal to stop it. To use another port: `PORT=9000 ./start.sh`.

Optional extras (the app works without them): add free Adzuna keys to `.env` for another job source, and an
`ANTHROPIC_API_KEY` for better-written cover-letter drafts.

## Sources

- **Top companies' own career pages** — Greenhouse and Lever expose
  public JSON APIs meant for exactly this ([Stripe](https://boards.greenhouse.io/stripe),
  Airbnb, Robinhood, Coinbase, Figma, Discord, Reddit, Databricks,
  Instacart, Asana, Affirm, Pinterest, Palantir, Spotify — full list, and
  where to add more, in [`job_finder/config.py`](job_finder/config.py)).
- **Adzuna** — a job-search aggregator API that surfaces listings from
  many boards (including ones that also appear on Indeed/LinkedIn)
  through an official, free API.

It does **not** scrape LinkedIn or Indeed directly — both explicitly
prohibit that in their Terms of Service and actively block it. Adzuna
gives comparable coverage without that risk, and the dashboard has a
one-click link to a live LinkedIn search for your target titles instead.

## Big tech and banks

Fetched automatically (public job boards): Stripe, Airbnb, Anthropic, OpenAI, Cloudflare, Okta, Block,
Snowflake, Lyft, DoorDash, and more on Greenhouse/Lever/Ashby; plus Nvidia, Salesforce, Adobe, Intel, Cisco,
Visa, Mastercard, PayPal and the banks Citi, Wells Fargo, Capital One, Morgan Stanley, Barclays, Deutsche Bank,
State Street, BlackRock, Fidelity, PNC, U.S. Bank and Truist via **Workday**. The Workday feeds are the same
public JSON endpoint each company's own careers page uses — not a documented API — so they're queried lightly
(a few search terms, two pages each) and have no descriptions (those jobs are difficulty-rated on title alone).

Not fetched (no public feed): Google, Meta, Apple, Amazon, Microsoft, Netflix, Uber, JPMorgan, Goldman Sachs,
Bank of America, American Express, HSBC. The dashboard links straight to each one's career site instead.
Add or remove companies in `config.py` (`COMPANIES`, `CAREER_SITES`).

## Resume upload, tabs, and the Financial District view

- **Profile → Upload resume** (PDF/DOCX/TXT/MD): reads skills and job titles, fills your profile, searches, and
  lists matches newest first. The file isn't stored, only its text.
- **Dashboard tabs**: To review / Saved / Applied / Did not apply / All. Each job has Applied, Saved and
  Did not apply buttons; clicking one moves it to that tab. These record what *you* did — nothing is submitted.
- **Financial District** page: finance and fintech employers with Lower Manhattan offices (best-effort list,
  confirm offices yourself), New York postings only, each with a 1–5 difficulty estimate (title seniority +
  years of experience asked for), easiest or hardest first.

## Chat box, Employers, and Import

- **Chat box** (top of the dashboard): upload a resume, or ask in plain English ("entry level data jobs at
  banks in New York this week"). It shows the filters it understood. It's a rule-based parser, so it needs no
  API key. Ask it "how does matching work?" for the explanation.
- **Match %** is keyword overlap: the share of your resume skills and target titles found in a posting, plus a
  bonus when a target title is in the job title. It isn't semantic, and bank (Workday) jobs are scored on title only.
- **Employers** page: a bar chart and a card per company with how many jobs your searches found, and link-out
  cards for employers with no public feed.
- **Import** page: LinkedIn and Indeed forbid scraping, so nothing is pulled from them. Paste a posting you found,
  or upload LinkedIn's own data export (`Saved Jobs.csv` / `Job Applications.csv`).

## Setup

```bash
cd job-finder
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and add your free Adzuna credentials from
https://developer.adzuna.com/ :

```
ADZUNA_APP_ID=...
ADZUNA_APP_KEY=...
```

(If you skip this, the app still runs fine — it just skips the Adzuna
results and reports only the direct company career-page hits.)

Optionally add `ANTHROPIC_API_KEY` to get better, tailored cover-letter
drafts (via Claude) instead of the built-in plain-template draft.

## Run the dashboard (recommended)

```bash
uvicorn job_finder.webapp:app --reload
```

Open http://localhost:8000. From there:

1. **Profile** — enter your target titles, skills/keywords, and a resume
   summary. This drives both the match score and the draft text.
2. **Refresh jobs** — pulls fresh postings from all sources, scores them
   against your profile, and adds new ones to your tracked list (state
   persists in `jobs.db`, a local SQLite file — nothing is ever lost by
   refreshing again).
3. Click into a job to see the full description, matched keywords, and
   generate a draft application. Edit it, then click **Open posting on
   employer's site** to actually apply, and mark the status once you have.

## Run the one-off CLI report (legacy)

```bash
python -m job_finder.main
```

Prints progress to the terminal and writes a static `report.html` — no
profile matching, no drafts, no persistence between runs. Kept for a quick
"what's out there right now" check or scripted/cron use; the dashboard is
the fuller tool.

## Customizing

Everything you'd want to tune lives in [`job_finder/config.py`](job_finder/config.py):

- `COMPANIES` — add more by finding their Greenhouse (`boards.greenhouse.io/<slug>`)
  or Lever (`jobs.lever.co/<slug>`) careers URL and adding the slug. This is
  how you add specific companies' own career pages, ATS-backed rather than
  scraped.
- `KEYWORDS` — the title-matching filter applied to each company's full
  job list before it ever reaches your dashboard (separate from, and
  upstream of, the profile-based match score).
- `ADZUNA_SEARCH_TERMS` / `ADZUNA_LOCATION` / `ADZUNA_COUNTRY` — tune the
  aggregator search.
- `MAX_JOB_AGE_DAYS` — drop postings older than this.

Your profile, tracked jobs, drafts, and application statuses live in
`jobs.db` (SQLite) rather than config — edit those through the **Profile**
page and the dashboard instead.

## Running refreshes on a schedule

To keep the dashboard's job list current automatically, add a cron entry
that hits the refresh endpoint while `uvicorn` is running (macOS/Linux):

```bash
crontab -e
# refresh every morning at 8am
0 8 * * * curl -X POST http://localhost:8000/refresh
```

Or, for the legacy static-report CLI instead:

```bash
0 8 * * * cd /path/to/job-finder && /path/to/.venv/bin/python -m job_finder.main
```
