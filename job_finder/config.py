"""
Configuration for job_finder.

Edit COMPANIES, KEYWORDS, and the Adzuna search settings below to tune
what shows up in your report. No code changes needed elsewhere.
"""

# Companies with public ATS job board APIs (verified working as of setup).
# ats: "greenhouse" or "lever"
# slug:  the board token used in that ATS's API URL. To find a new
#        company's slug: check their careers page URL — Greenhouse URLs
#        look like boards.greenhouse.io/<slug>, Lever URLs look like
#        jobs.lever.co/<slug>.
COMPANIES = [
    {"name": "Stripe", "ats": "greenhouse", "slug": "stripe"},
    {"name": "Airbnb", "ats": "greenhouse", "slug": "airbnb"},
    {"name": "Robinhood", "ats": "greenhouse", "slug": "robinhood"},
    {"name": "Coinbase", "ats": "greenhouse", "slug": "coinbase"},
    {"name": "Figma", "ats": "greenhouse", "slug": "figma"},
    {"name": "Discord", "ats": "greenhouse", "slug": "discord"},
    {"name": "Reddit", "ats": "greenhouse", "slug": "reddit"},
    {"name": "Databricks", "ats": "greenhouse", "slug": "databricks"},
    {"name": "Instacart", "ats": "greenhouse", "slug": "instacart"},
    {"name": "Asana", "ats": "greenhouse", "slug": "asana"},
    {"name": "Affirm", "ats": "greenhouse", "slug": "affirm"},
    {"name": "Pinterest", "ats": "greenhouse", "slug": "pinterest"},
    {"name": "Palantir", "ats": "lever", "slug": "palantir"},
    {"name": "Spotify", "ats": "lever", "slug": "spotify"},

    # --- More big tech (public Greenhouse / Ashby job boards) ---
    {"name": "Anthropic", "ats": "greenhouse", "slug": "anthropic"},
    {"name": "OpenAI", "ats": "ashby", "slug": "openai"},
    {"name": "Cloudflare", "ats": "greenhouse", "slug": "cloudflare"},
    {"name": "Okta", "ats": "greenhouse", "slug": "okta"},
    {"name": "Block", "ats": "greenhouse", "slug": "block"},
    {"name": "Twilio", "ats": "greenhouse", "slug": "twilio"},
    {"name": "Snowflake", "ats": "ashby", "slug": "snowflake"},
    {"name": "Lyft", "ats": "greenhouse", "slug": "lyft"},
    {"name": "DoorDash", "ats": "greenhouse", "slug": "doordashusa"},
    {"name": "Dropbox", "ats": "greenhouse", "slug": "dropbox"},
    {"name": "Roblox", "ats": "greenhouse", "slug": "roblox"},
    {"name": "Scale AI", "ats": "greenhouse", "slug": "scaleai"},
    {"name": "Notion", "ats": "ashby", "slug": "notion"},
    {"name": "GitLab", "ats": "greenhouse", "slug": "gitlab"},
    {"name": "Elastic", "ats": "greenhouse", "slug": "elastic"},

    # --- Big tech on Workday ---
    {"name": "Nvidia", "ats": "workday", "slug": "nvidia", "host": "wd5", "site": "NVIDIAExternalCareerSite"},
    {"name": "Salesforce", "ats": "workday", "slug": "salesforce", "host": "wd12", "site": "External_Career_Site"},
    {"name": "Adobe", "ats": "workday", "slug": "adobe", "host": "wd5", "site": "external_experienced"},
    {"name": "Intel", "ats": "workday", "slug": "intel", "host": "wd1", "site": "External"},
    {"name": "Cisco", "ats": "workday", "slug": "cisco", "host": "wd5", "site": "Cisco_Careers"},
    {"name": "HP", "ats": "workday", "slug": "hp", "host": "wd5", "site": "ExternalCareerSite"},
    {"name": "Autodesk", "ats": "workday", "slug": "autodesk", "host": "wd1", "site": "Ext"},
    {"name": "PayPal", "ats": "workday", "slug": "paypal", "host": "wd1", "site": "jobs"},
    {"name": "Visa", "ats": "workday", "slug": "visa", "host": "wd5", "site": "Visa"},
    {"name": "Mastercard", "ats": "workday", "slug": "mastercard", "host": "wd1", "site": "CorporateCareers"},

    # --- Banks & asset managers on Workday ---
    {"name": "Citi", "ats": "workday", "slug": "citi", "host": "wd5", "site": "2"},
    {"name": "Wells Fargo", "ats": "workday", "slug": "wf", "host": "wd1", "site": "WellsFargoJobs"},
    {"name": "Capital One", "ats": "workday", "slug": "capitalone", "host": "wd12", "site": "Capital_One"},
    {"name": "Morgan Stanley", "ats": "workday", "slug": "ms", "host": "wd5", "site": "External"},
    {"name": "Barclays", "ats": "workday", "slug": "barclays", "host": "wd3", "site": "External_Career_Site_Barclays"},
    {"name": "Deutsche Bank", "ats": "workday", "slug": "db", "host": "wd3", "site": "DBWebsite"},
    {"name": "State Street", "ats": "workday", "slug": "statestreet", "host": "wd1", "site": "Global"},
    {"name": "BlackRock", "ats": "workday", "slug": "blackrock", "host": "wd1", "site": "BlackRock_Professional"},
    {"name": "Fidelity", "ats": "workday", "slug": "fmr", "host": "wd1", "site": "FidelityCareers"},
    {"name": "PNC", "ats": "workday", "slug": "pnc", "host": "wd5", "site": "external"},
    {"name": "U.S. Bank", "ats": "workday", "slug": "usbank", "host": "wd1", "site": "US_Bank_Careers"},
    {"name": "Truist", "ats": "workday", "slug": "truist", "host": "wd1", "site": "Careers"},
]

# Groups used by the chat box ("jobs at banks", "big tech roles").
BANK_COMPANIES = {
    "Citi", "Wells Fargo", "Capital One", "Morgan Stanley", "Barclays", "Deutsche Bank", "State Street",
    "BlackRock", "Fidelity", "PNC", "U.S. Bank", "Truist",
}
BIG_TECH_COMPANIES = {
    "Stripe", "Airbnb", "Pinterest", "Reddit", "Databricks", "Palantir", "Spotify", "Figma", "Discord",
    "Anthropic", "OpenAI", "Cloudflare", "Okta", "Block", "Twilio", "Snowflake", "Lyft", "DoorDash",
    "Dropbox", "Roblox", "Scale AI", "Notion", "GitLab", "Elastic", "Nvidia", "Salesforce", "Adobe",
    "Intel", "Cisco", "HP", "Autodesk", "PayPal", "Visa", "Mastercard",
}

# Big employers with NO usable public job feed (their own custom career sites).
# They are not fetched automatically; the dashboard links straight to each one.
CAREER_SITES = [
    ("Google", "https://www.google.com/about/careers/applications/jobs/results"),
    ("Meta", "https://www.metacareers.com/jobs"),
    ("Apple", "https://jobs.apple.com/en-us/search"),
    ("Amazon", "https://www.amazon.jobs/en/search"),
    ("Microsoft", "https://jobs.careers.microsoft.com/global/en/search"),
    ("Netflix", "https://jobs.netflix.com/search"),
    ("Uber", "https://www.uber.com/us/en/careers/list/"),
    ("JPMorgan Chase", "https://www.jpmorganchase.com/careers"),
    ("Goldman Sachs", "https://www.goldmansachs.com/careers/"),
    ("Bank of America", "https://careers.bankofamerica.com/en-us/job-search"),
    ("American Express", "https://www.americanexpress.com/en-us/careers/"),
    ("HSBC", "https://www.hsbc.com/careers"),
]

# Keywords used to filter each company's full job list down to roles
# relevant to your field. Case-insensitive substring match against the
# job title. Add/remove freely.
KEYWORDS = [
    # Software engineering
    "software engineer", "backend", "back-end", "front-end", "frontend",
    "full stack", "full-stack", "swe", "site reliability", "sre",
    "infrastructure engineer", "platform engineer", "mobile engineer",
    "ios engineer", "android engineer", "machine learning engineer",
    "ml engineer", "data engineer",
    # Product / design
    "product manager", "product designer", "ux designer", "ui designer",
    "product design", "user experience", "user researcher", "design lead",
]

# --- Adzuna (aggregator; surfaces listings that also appear on boards
#     like Indeed/LinkedIn, without scraping those sites directly) ---
# Free credentials: https://developer.adzuna.com/
ADZUNA_COUNTRY = "us"           # e.g. us, gb, ca, au...
ADZUNA_RESULTS_PER_PAGE = 20
ADZUNA_MAX_PAGES = 3            # per search term
ADZUNA_SEARCH_TERMS = [
    "software engineer",
    "product manager",
    "product designer",
]
ADZUNA_LOCATION = None          # e.g. "San Francisco" — None = no filter

# --- Financial-district view ---
# Finance / trading / fintech employers with a Lower Manhattan (NYC Financial
# District) presence, each confirmed to have a live public job board. This is a
# best-effort list from general knowledge, NOT verified office addresses —
# confirm a company's office before relying on it. Edit freely.
# To target a different district (e.g. San Francisco), change DISTRICT_NAME,
# DISTRICT_LOCATION_TERMS, and the companies below.
DISTRICT_NAME = "NYC Financial District"
DISTRICT_LOCATION_TERMS = ["new york", "nyc", "manhattan"]
DISTRICT_COMPANIES = [
    {"name": "Jane Street", "ats": "greenhouse", "slug": "janestreet"},
    {"name": "Virtu Financial", "ats": "greenhouse", "slug": "virtu"},
    {"name": "Clear Street", "ats": "greenhouse", "slug": "clearstreet"},
    {"name": "IEX", "ats": "greenhouse", "slug": "iex"},
    {"name": "Hudson River Trading", "ats": "greenhouse", "slug": "wehrtyou"},
    {"name": "IMC Trading", "ats": "greenhouse", "slug": "imc"},
    {"name": "Akuna Capital", "ats": "greenhouse", "slug": "akunacapital"},
    {"name": "DRW", "ats": "greenhouse", "slug": "drweng"},
    {"name": "DriveWealth", "ats": "greenhouse", "slug": "drivewealth"},
    {"name": "Betterment", "ats": "greenhouse", "slug": "betterment"},
    {"name": "Carta", "ats": "greenhouse", "slug": "carta"},
    {"name": "Mercury", "ats": "greenhouse", "slug": "mercury"},
    {"name": "Fireblocks", "ats": "greenhouse", "slug": "fireblocks"},
    {"name": "Gemini", "ats": "greenhouse", "slug": "gemini"},
    {"name": "Ramp", "ats": "ashby", "slug": "ramp"},
    {"name": "Paxos", "ats": "ashby", "slug": "paxos"},
    {"name": "NerdWallet (Fundera)", "ats": "ashby", "slug": "nerdwallet"},
    {"name": "Anchorage Digital", "ats": "lever", "slug": "anchorage"},
    # Large banks with Lower Manhattan offices (Workday search is limited to "New York" postings)
    {"name": "Citi", "ats": "workday", "slug": "citi", "host": "wd5", "site": "2"},
    {"name": "Morgan Stanley", "ats": "workday", "slug": "ms", "host": "wd5", "site": "External"},
    {"name": "Deutsche Bank", "ats": "workday", "slug": "db", "host": "wd3", "site": "DBWebsite"},
    {"name": "Barclays", "ats": "workday", "slug": "barclays", "host": "wd3", "site": "External_Career_Site_Barclays"},
    {"name": "BlackRock", "ats": "workday", "slug": "blackrock", "host": "wd1", "site": "BlackRock_Professional"},
]

# --- Output ---
MAX_JOB_AGE_DAYS = 21            # drop postings older than this
OUTPUT_HTML = "report.html"
