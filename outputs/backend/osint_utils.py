import hashlib
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request


EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
    r"[A-Za-z]{2,63}\b"
)
PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")


def evidence_id(*parts):
    raw = ":".join(str(part or "") for part in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def is_valid_http_url(url):
    parsed = urllib.parse.urlparse((url or "").strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def hostname(url):
    return (urllib.parse.urlparse(url).hostname or "").lower()


def host_matches(url, expected_domains):
    if not expected_domains:
        return True
    host = hostname(url)
    return any(host == domain or host.endswith(f".{domain}") for domain in expected_domains)


def verify_url_accessible(url, timeout=8):
    if not is_valid_http_url(url):
        return False

    headers = {
        "User-Agent": "ShieldTrace-OSINT/1.0",
        "Accept": "text/html,application/pdf,*/*",
    }
    for method in ("HEAD", "GET"):
        request = urllib.request.Request(url, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return 200 <= response.status < 400
        except urllib.error.HTTPError as exc:
            if exc.code == 405 and method == "HEAD":
                continue
            return False
        except (urllib.error.URLError, TimeoutError, ValueError):
            return False
    return False


def normalized_text(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text).casefold().strip()


def name_tokens(full_name):
    normalized = normalized_text(full_name)
    return [token for token in re.split(r"[^a-z0-9]+", normalized) if len(token) > 1]


def text_contains_name(title, snippet, full_name):
    haystack = normalized_text(f"{title} {snippet}")
    tokens = name_tokens(full_name)
    if len(tokens) < 2:
        return False
    return all(token in haystack for token in tokens)


def contains_email(*values):
    return bool(EMAIL_RE.search(" ".join(str(value or "") for value in values)))


def contains_phone(*values):
    return bool(PHONE_RE.search(" ".join(str(value or "") for value in values)))
