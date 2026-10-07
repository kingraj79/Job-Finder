"""Renders the collected jobs into a self-contained HTML dashboard."""
from __future__ import annotations

import html
from datetime import datetime, timezone


def _parse(raw):
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _fmt_date(raw) -> str:
    dt = _parse(raw)
    return dt.strftime("%b %d, %Y") if dt else "Unknown"


def _is_new(raw, days: int = 3) -> bool:
    dt = _parse(raw)
    if not dt:
        return False
    return (datetime.now(timezone.utc) - dt).days <= days


def render_report(jobs: list[dict], output_path: str) -> None:
    generated_at = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    companies = sorted({j["company"] for j in jobs})
    sources = sorted({j["source"] for j in jobs})

    rows = []
    for j in jobs:
        title = html.escape(j.get("title", ""))
        company = html.escape(j.get("company", ""))
        location = html.escape(j.get("location", "") or "—")
        url = html.escape(j.get("url", "#"), quote=True)
        source = html.escape(j.get("source", ""))
        date_str = _fmt_date(j.get("posted_at"))
        new_badge = '<span class="badge">NEW</span>' if _is_new(j.get("posted_at")) else ""
        search_blob = html.escape((j.get("title", "") + " " + j.get("company", "")).lower())
        rows.append(f"""
        <tr data-company="{company.lower()}" data-source="{source.lower()}" data-text="{search_blob}">
          <td><a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a>{new_badge}</td>
          <td>{company}</td>
          <td>{location}</td>
          <td><span class="tag">{source}</span></td>
          <td>{date_str}</td>
        </tr>""")

    company_options = "".join(
        f'<option value="{html.escape(c.lower())}">{html.escape(c)}</option>' for c in companies
    )
    source_options = "".join(
        f'<option value="{html.escape(s.lower())}">{html.escape(s)}</option>' for s in sources
    )

    empty_msg = (
        '<div class="empty">No jobs matched. Try widening KEYWORDS in config.py, '
        "or check that your Adzuna credentials are set.</div>"
        if not rows
        else ""
    )

    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Job Search Report</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root {{
    --bg: #f7f7f8; --card: #ffffff; --text: #1a1a1a; --muted: #666;
    --border: #e3e3e6; --accent: #4f46e5; --new: #16a34a;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg: #15161a; --card: #1e1f24; --text: #eaeaea; --muted: #9a9a9a;
             --border: #2c2d33; --accent: #818cf8; --new: #4ade80; }}
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
          background: var(--bg); color: var(--text); }}
  .wrap {{ max-width: 1100px; margin: 0 auto; padding: 32px 20px 60px; }}
  h1 {{ font-size: 1.6rem; margin-bottom: 4px; }}
  .meta {{ color: var(--muted); font-size: 0.9rem; margin-bottom: 24px; }}
  .stats {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom: 24px; }}
  .stat {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px;
           padding: 12px 18px; min-width: 120px; }}
  .stat .n {{ font-size: 1.4rem; font-weight: 700; }}
  .stat .l {{ font-size: 0.8rem; color: var(--muted); }}
  .controls {{ display:flex; gap:10px; flex-wrap:wrap; margin-bottom: 16px; }}
  input, select {{ background: var(--card); color: var(--text); border: 1px solid var(--border);
                   border-radius: 8px; padding: 8px 12px; font-size: 0.9rem; }}
  input[type=text] {{ flex: 1; min-width: 220px; }}
  table {{ width: 100%; border-collapse: collapse; background: var(--card); border-radius: 10px;
           overflow: hidden; border: 1px solid var(--border); }}
  th, td {{ text-align: left; padding: 10px 14px; border-bottom: 1px solid var(--border); font-size: 0.92rem; }}
  th {{ background: rgba(127,127,127,0.08); font-size: 0.8rem; text-transform: uppercase;
        letter-spacing: 0.03em; color: var(--muted); }}
  tr:last-child td {{ border-bottom: none; }}
  a {{ color: var(--accent); text-decoration: none; font-weight: 500; }}
  a:hover {{ text-decoration: underline; }}
  .badge {{ background: var(--new); color: #fff; font-size: 0.65rem; padding: 2px 6px;
            border-radius: 999px; margin-left: 6px; vertical-align: middle; }}
  .tag {{ background: rgba(127,127,127,0.15); padding: 2px 8px; border-radius: 999px; font-size: 0.78rem; }}
  .empty {{ text-align:center; padding: 40px; color: var(--muted); }}
</style>
</head>
<body>
<div class="wrap">
  <h1>Job Search Report</h1>
  <div class="meta">Generated {generated_at} &middot; {len(jobs)} matching postings</div>

  <div class="stats">
    <div class="stat"><div class="n">{len(jobs)}</div><div class="l">Total jobs</div></div>
    <div class="stat"><div class="n">{len(companies)}</div><div class="l">Companies</div></div>
    <div class="stat"><div class="n">{len(sources)}</div><div class="l">Sources</div></div>
  </div>

  <div class="controls">
    <input type="text" id="search" placeholder="Search title or company...">
    <select id="companyFilter"><option value="">All companies</option>{company_options}</select>
    <select id="sourceFilter"><option value="">All sources</option>{source_options}</select>
  </div>

  <table id="jobsTable">
    <thead><tr><th>Role</th><th>Company</th><th>Location</th><th>Source</th><th>Posted</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table>
  {empty_msg}
</div>

<script>
  const search = document.getElementById('search');
  const companyFilter = document.getElementById('companyFilter');
  const sourceFilter = document.getElementById('sourceFilter');
  const rows = Array.from(document.querySelectorAll('#jobsTable tbody tr'));

  function applyFilters() {{
    const q = search.value.toLowerCase();
    const c = companyFilter.value;
    const s = sourceFilter.value;
    rows.forEach(row => {{
      const matchesText = !q || row.dataset.text.includes(q);
      const matchesCompany = !c || row.dataset.company === c;
      const matchesSource = !s || row.dataset.source === s;
      row.style.display = (matchesText && matchesCompany && matchesSource) ? '' : 'none';
    }});
  }}

  search.addEventListener('input', applyFilters);
  companyFilter.addEventListener('change', applyFilters);
  sourceFilter.addEventListener('change', applyFilters);
</script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(doc)
