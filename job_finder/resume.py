"""Turns an uploaded resume into text and a draft profile (skills, titles, contact).

Parsing happens in memory — the uploaded file itself is never written to disk;
only the extracted text is saved to your local profile.
"""
from __future__ import annotations

import io
import re
import zipfile
from xml.etree import ElementTree

MAX_BYTES = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}

SKILL_VOCAB = [
    # languages / engineering
    "python", "java", "javascript", "typescript", "golang", "rust", "c++", "c#", "ruby", "php", "scala",
    "kotlin", "swift", "sql", "nosql", "react", "angular", "vue", "node.js", "django", "flask", "fastapi",
    "spring", "graphql", "rest", "apis", "microservices", "distributed systems", "kafka", "spark",
    "aws", "azure", "gcp", "kubernetes", "docker", "terraform", "linux", "ci/cd", "postgresql", "mysql",
    "mongodb", "redis", "machine learning", "deep learning", "pytorch", "tensorflow", "data science",
    "data engineering", "etl", "airflow", "snowflake", "tableau", "power bi", "excel", "pandas", "numpy",
    # finance
    "financial modeling", "valuation", "risk management", "trading", "derivatives", "fixed income",
    "equities", "portfolio management", "quantitative", "bloomberg", "accounting", "audit", "compliance",
    "fp&a", "forecasting", "m&a", "private equity", "venture capital", "kyc", "aml",
    # product / design / business
    "product management", "roadmap", "a/b testing", "user research", "figma", "ux", "ui design",
    "prototyping", "agile", "scrum", "project management", "stakeholder management", "analytics",
    "marketing", "seo", "content strategy", "sales", "customer success", "salesforce", "hubspot",
    "operations", "supply chain", "recruiting", "leadership", "mentoring", "security", "cybersecurity",
]

TITLE_VOCAB = [
    "software engineer", "backend engineer", "frontend engineer", "full stack engineer",
    "full-stack engineer", "site reliability engineer", "devops engineer", "platform engineer",
    "data engineer", "data scientist", "machine learning engineer", "data analyst",
    "business analyst", "financial analyst", "quantitative analyst", "quantitative researcher",
    "quantitative developer", "trader", "product manager", "program manager", "project manager",
    "product designer", "ux designer", "ux researcher", "security engineer", "qa engineer",
    "solutions engineer", "sales engineer", "account manager", "account executive",
    "marketing manager", "operations manager", "accountant", "recruiter", "engineering manager",
    "mobile engineer", "ios engineer", "android engineer", "research scientist", "consultant",
]

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"(?:\+?\d{1,2}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")


class ResumeError(ValueError):
    pass


def extract_text(filename: str, data: bytes) -> str:
    if len(data) > MAX_BYTES:
        raise ResumeError("File is larger than 5 MB.")
    name = filename.lower()
    ext = name[name.rfind("."):] if "." in name else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ResumeError("Unsupported file type — upload a PDF, DOCX, TXT, or MD file.")

    try:
        if ext == ".pdf":
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
        elif ext == ".docx":
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                root = ElementTree.fromstring(z.read("word/document.xml"))
            ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
            paras = ["".join(t.text or "" for t in p.iter(f"{ns}t")) for p in root.iter(f"{ns}p")]
            text = "\n".join(paras)
        else:
            text = data.decode("utf-8", errors="replace")
    except ResumeError:
        raise
    except Exception as e:
        raise ResumeError(f"Couldn't read that file ({type(e).__name__}). Is it a valid {ext[1:].upper()}?")

    text = text.strip()
    if not text:
        raise ResumeError("No text found in the file (scanned image PDFs aren't supported).")
    return text


def _find_terms(text: str, vocab: list[str]) -> list[str]:
    low = text.lower()
    found = []
    for term in vocab:
        if re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", low):
            found.append(term)
    return found


def extract_profile(text: str) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    name = ""
    if lines and len(lines[0]) <= 40 and not re.search(r"[\d@]", lines[0]):
        name = lines[0].title() if lines[0].isupper() else lines[0]

    email = _EMAIL_RE.search(text)
    phone = _PHONE_RE.search(text)
    return {
        "name": name,
        "email": email.group(0) if email else "",
        "phone": phone.group(0) if phone else "",
        "skills": _find_terms(text, SKILL_VOCAB),
        "titles": _find_terms(text, TITLE_VOCAB),
    }
