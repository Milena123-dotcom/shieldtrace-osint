import re

from .osint_utils import (
    contains_email,
    contains_phone,
    evidence_id,
    host_matches,
    is_valid_http_url,
    text_contains_name,
    verify_url_accessible,
)
from .search_provider import SearchProvider


CV_RE = re.compile(r"\b(cv|curriculum vitae|resume)\b", re.IGNORECASE)


QUERY_DEFINITIONS = [
    {
        "key": "linkedin",
        "query": '"{full_name}" site:linkedin.com',
        "type": "Profil social",
        "expected_domains": ["linkedin.com"],
    },
    {
        "key": "facebook",
        "query": '"{full_name}" site:facebook.com',
        "type": "Profil social",
        "expected_domains": ["facebook.com"],
    },
    {
        "key": "instagram",
        "query": '"{full_name}" site:instagram.com',
        "type": "Profil social",
        "expected_domains": ["instagram.com"],
    },
    {
        "key": "pdf",
        "query": '"{full_name}" filetype:pdf',
        "type": "Document",
        "expected_domains": [],
        "requires_pdf": True,
    },
    {
        "key": "cv",
        "query": '"{full_name}" CV',
        "type": "Document",
        "expected_domains": [],
        "requires_cv": True,
    },
    {
        "key": "email",
        "query": '"{full_name}" email',
        "type": "Email",
        "expected_domains": [],
        "requires_email": True,
    },
    {
        "key": "phone",
        "query": '"{full_name}" telefon',
        "type": "Telefon",
        "expected_domains": [],
        "requires_phone": True,
    },
]


def scan(profile):
    full_name = profile.get("fullName", "").strip()
    if not full_name:
        return []

    provider = SearchProvider()
    evidence = []
    seen_urls = set()

    for definition in QUERY_DEFINITIONS:
        query = definition["query"].format(full_name=full_name)
        for result in provider.search(query):
            evidence_item = evidence_from_result(result, definition, full_name)
            if not evidence_item:
                continue

            dedupe_key = evidence_item["url"].rstrip("/").lower()
            if dedupe_key in seen_urls:
                continue
            seen_urls.add(dedupe_key)
            evidence.append(evidence_item)

    return evidence


def evidence_from_result(result, definition, full_name):
    title = result.get("title", "").strip()
    url = result.get("url", "").strip()
    snippet = result.get("snippet", "").strip()

    if not is_valid_http_url(url):
        return None
    if not host_matches(url, definition.get("expected_domains", [])):
        return None
    if not text_contains_name(title, snippet, full_name):
        return None
    if not _matches_required_signal(definition, title, snippet, url):
        return None
    if not verify_url_accessible(url):
        return None

    return {
        "id": evidence_id(definition["type"], url, snippet),
        "type": definition["type"],
        "title": title or url,
        "value": title or url,
        "url": url,
        "snippet": snippet,
        "source": result.get("source", "Brave Search"),
        "confidence": result.get("confidence", "high"),
        "verified": True,
    }


def _matches_required_signal(definition, title, snippet, url):
    haystack = f"{title} {snippet} {url}".lower()
    if definition.get("requires_pdf"):
        return ".pdf" in url.lower()
    if definition.get("requires_cv"):
        return bool(CV_RE.search(haystack))
    if definition.get("requires_email"):
        return contains_email(title, snippet, url)
    if definition.get("requires_phone"):
        return contains_phone(title, snippet)
    return True
