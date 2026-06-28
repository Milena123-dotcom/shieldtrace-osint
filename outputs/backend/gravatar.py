import hashlib
import json
import urllib.error
import urllib.request

from .osint_utils import is_valid_http_url, verify_url_accessible


def scan(email: str) -> list:
    email = email.strip().lower()
    if not email:
        return []

    email_hash = hashlib.md5(email.encode("utf-8")).hexdigest()
    request = urllib.request.Request(
        f"https://en.gravatar.com/{email_hash}.json",
        headers={"User-Agent": "ShieldTrace-OSINT/1.0"},
    )

    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            if response.status != 200:
                return []
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return []

    entries = payload.get("entry") or []
    if not entries:
        return []

    entry = entries[0]
    url = entry.get("profileUrl", "")
    if not is_valid_http_url(url) or not verify_url_accessible(url):
        return []

    metadata = {
        "name": entry.get("displayName") or "",
        "bio": entry.get("aboutMe") or "",
        "company": "",
        "location": entry.get("currentLocation") or "",
        "public_repos": 0,
        "followers": 0,
    }
    snippet_parts = [part for part in [metadata["name"], metadata["bio"], metadata["location"]] if part]

    return [
        {
            "id": email_hash,
            "type": "gravatar",
            "title": entry.get("displayName") or email,
            "url": url,
            "source": "Gravatar",
            "snippet": " | ".join(snippet_parts),
            "confidence": "high",
            "verified": True,
            "metadata": metadata,
        }
    ]
