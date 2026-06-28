import json
import urllib.error
import urllib.parse
import urllib.request

from .osint_utils import is_valid_http_url, verify_url_accessible


def scan(username: str) -> list:
    username = username.strip()
    if not username:
        return []

    safe_username = urllib.parse.quote(username)
    request = urllib.request.Request(
        f"https://api.github.com/users/{safe_username}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "ShieldTrace-OSINT/1.0",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            if response.status != 200:
                return []
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return []

    url = payload.get("html_url", "")
    if not is_valid_http_url(url) or not verify_url_accessible(url):
        return []

    metadata = {
        "name": payload.get("name") or "",
        "bio": payload.get("bio") or "",
        "company": payload.get("company") or "",
        "location": payload.get("location") or "",
        "public_repos": payload.get("public_repos") or 0,
        "followers": payload.get("followers") or 0,
    }
    snippet_parts = [part for part in [metadata["name"], metadata["bio"], metadata["company"], metadata["location"]] if part]

    return [
        {
            "id": str(payload.get("id", "")),
            "type": "github",
            "title": payload.get("login") or username,
            "url": url,
            "source": "GitHub",
            "snippet": " | ".join(snippet_parts),
            "confidence": "high",
            "verified": True,
            "metadata": metadata,
        }
    ]
