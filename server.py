#!/usr/bin/env python3
import hashlib
import json
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


ROOT = pathlib.Path(__file__).resolve().parent
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_CX = os.getenv("GOOGLE_CX", "")
USER_AGENT = "ShieldTrace-MVP/1.0"


def request_json(url, timeout=12):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return 0, None


def google_search(query, limit=3):
    if not GOOGLE_API_KEY or not GOOGLE_CX:
        return []

    params = urllib.parse.urlencode(
        {
            "key": GOOGLE_API_KEY,
            "cx": GOOGLE_CX,
            "q": query,
            "num": min(limit, 10),
            "safe": "active",
        }
    )
    status, payload = request_json(f"https://www.googleapis.com/customsearch/v1?{params}")
    if status != 200 or not payload:
        return []
    return payload.get("items", [])[:limit]


def evidence_from_google(item, evidence_type, points, category, risk, confidence="medie"):
    title = item.get("title", "Rezultat online")
    link = item.get("link", "")
    snippet = item.get("snippet", "")
    return {
        "id": hashlib.sha1(f"{evidence_type}:{link}:{snippet}".encode("utf-8")).hexdigest()[:12],
        "type": evidence_type,
        "value": title,
        "source": "Google Programmable Search",
        "url": link,
        "snippet": snippet,
        "confidence": confidence,
        "points": points,
        "category": category,
        "risk": risk,
        "severity": "ridicat" if points >= 15 else "mediu",
    }


def scan_google(profile):
    evidence = []
    full_name = profile.get("fullName", "").strip()
    city = profile.get("city") or profile.get("country") or ""
    email = profile.get("email", "").strip()
    phone = profile.get("phone", "").strip()
    domain = profile.get("domain", "").strip()
    modules = set(profile.get("modules", []))

    if "google" in modules and full_name:
        query = f'"{full_name}" {city}'.strip()
        for item in google_search(query, 3):
            evidence.append(
                evidence_from_google(
                    item,
                    "Locatie",
                    8,
                    "Date personale",
                    "Rezultatul leaga numele de o locatie/context public, util pentru phishing personalizat.",
                )
            )

    if "social" in modules and full_name:
        social_query = f'"{full_name}" (site:linkedin.com OR site:facebook.com OR site:instagram.com)'
        for item in google_search(social_query, 4):
            evidence.append(
                evidence_from_google(
                    item,
                    "Profil social",
                    12,
                    "Social Engineering",
                    "Profilul social poate furniza imagine, rol, contacte, interese sau relatii.",
                    "medie",
                )
            )

    if "documents" in modules and full_name:
        doc_query = f'"{full_name}" (filetype:pdf OR filetype:doc OR filetype:docx OR "CV")'
        if domain:
            doc_query = f'{doc_query} site:{domain}'
        for item in google_search(doc_query, 5):
            evidence.append(
                evidence_from_google(
                    item,
                    "Document",
                    20,
                    "Identity Theft",
                    "Documentele publice pot contine CV, semnatura, date de contact sau istoric profesional.",
                    "medie",
                )
            )

    if "email" in modules and email:
        for item in google_search(f'"{email}"', 3):
            evidence.append(
                evidence_from_google(
                    item,
                    "Email",
                    10,
                    "Date personale",
                    "Emailul gasit public permite corelarea conturilor si incercari de resetare.",
                    "ridicata",
                )
            )

    if phone:
        for item in google_search(f'"{phone}" "{full_name}"', 2):
            evidence.append(
                evidence_from_google(
                    item,
                    "Telefon",
                    15,
                    "Date personale",
                    "Telefonul public creste riscul de smishing, impersonare si recuperare frauduloasa.",
                    "ridicata",
                )
            )

    if "username" in modules:
        for username in profile.get("usernames", [])[:5]:
            for item in google_search(f'"{username}"', 2):
                evidence.append(
                    evidence_from_google(
                        item,
                        "Username",
                        14,
                        "Corelare conturi",
                        "Username-ul gasit public poate lega activitati de pe platforme diferite.",
                        "medie",
                    )
                )

    return evidence


def scan_github(profile):
    evidence = []
    if "username" not in set(profile.get("modules", [])):
        return evidence

    for username in profile.get("usernames", [])[:5]:
        safe_username = urllib.parse.quote(username.strip())
        if not safe_username:
            continue
        status, payload = request_json(f"https://api.github.com/users/{safe_username}")
        if status != 200 or not payload:
            continue
        evidence.append(
            {
                "id": f"github-{payload.get('id')}",
                "type": "Username",
                "value": username,
                "source": "GitHub API",
                "url": payload.get("html_url", ""),
                "snippet": f"Cont GitHub public: {payload.get('name') or username}; bio: {payload.get('bio') or 'fara bio public'}; locatie: {payload.get('location') or 'nespecificata'}.",
                "confidence": "ridicata",
                "points": 14,
                "category": "Corelare conturi",
                "risk": "Contul poate lega identitatea tehnica/profesionala de username-uri folosite in alte locuri.",
                "severity": "ridicat",
            }
        )
    return evidence


def scan_gravatar(profile):
    email = profile.get("email", "").strip().lower()
    if not email or "email" not in set(profile.get("modules", [])):
        return []

    email_hash = hashlib.md5(email.encode("utf-8")).hexdigest()
    status, payload = request_json(f"https://en.gravatar.com/{email_hash}.json")
    if status != 200 or not payload:
        return []

    entry = (payload.get("entry") or [{}])[0]
    return [
        {
            "id": f"gravatar-{email_hash[:10]}",
            "type": "Email",
            "value": email,
            "source": "Gravatar",
            "url": entry.get("profileUrl", f"https://gravatar.com/{email_hash}"),
            "snippet": f"Profil Gravatar public asociat emailului; nume afisat: {entry.get('displayName') or 'nespecificat'}.",
            "confidence": "ridicata",
            "points": 10,
            "category": "Date personale",
            "risk": "Avatarul si profilul pot lega emailul de identitatea vizuala si conturi externe.",
            "severity": "mediu",
        }
    ]


def dedupe_evidence(evidence):
    seen = set()
    unique = []
    for item in evidence:
        key = (item.get("type"), item.get("url"), item.get("snippet"))
        if key in seen or not item.get("url"):
            continue
        seen.add(key)
        unique.append(item)
    return unique


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_POST(self):
        if self.path != "/api/scan":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        try:
            profile = json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "JSON invalid")
            return

        if not profile.get("consent"):
            self.send_error(403, "Consimtamantul este obligatoriu")
            return

        started = time.time()
        evidence = []
        evidence.extend(scan_google(profile))
        evidence.extend(scan_github(profile))
        evidence.extend(scan_gravatar(profile))
        evidence = dedupe_evidence(evidence)

        payload = {
            "evidence": evidence,
            "meta": {
                "mode": "live API" if evidence else "live fara rezultate",
                "googleConfigured": bool(GOOGLE_API_KEY and GOOGLE_CX),
                "sources": ["Google Programmable Search", "GitHub API", "Gravatar"],
                "durationMs": round((time.time() - started) * 1000),
                "notice": "Rezultatele sunt obtinute din API-uri publice si trebuie folosite doar cu consimtamant.",
            },
        }

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    port = int(os.getenv("PORT", "8787"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"ShieldTrace live backend: http://127.0.0.1:{port}")
    print("Seteaza GOOGLE_API_KEY si GOOGLE_CX pentru rezultate Google reale.")
    server.serve_forever()


if __name__ == "__main__":
    main()
