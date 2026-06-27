#!/usr/bin/env python3
import json
import os
import pathlib
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from backend import github, google, gravatar


ROOT = pathlib.Path(__file__).resolve().parent
USER_AGENT = "ShieldTrace-MVP/1.0"


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


def run_scanner(fn, *args):
    try:
        return fn(*args)
    except Exception:
        return []


def scan_profile(profile):
    tasks = [(google.scan, profile)]

    for username in profile.get("usernames", []):
        tasks.append((github.scan, username))

    if profile.get("email"):
        tasks.append((gravatar.scan, profile.get("email", "")))

    evidence = []
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(tasks)))) as executor:
        futures = [executor.submit(run_scanner, fn, arg) for fn, arg in tasks]
        for future in as_completed(futures):
            evidence.extend(future.result())

    return dedupe_evidence(evidence)


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
        evidence = scan_profile(profile)

        payload = {
            "evidence": evidence,
            "meta": {
                "mode": "live API" if evidence else "live fara rezultate",
                "braveConfigured": bool(os.getenv("BRAVE_API_KEY", "").strip()),
                "sources": ["Brave Search", "GitHub", "Gravatar"],
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
    print("Seteaza BRAVE_API_KEY pentru rezultate Brave Search reale.")
    server.serve_forever()


if __name__ == "__main__":
    main()
