#!/usr/bin/env python3
import json
import mimetypes
import os
import pathlib
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

from backend import ai_report, github, google, gravatar, report_generator, risk_engine


ROOT = pathlib.Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "reports"
USER_AGENT = "ShieldTrace-MVP/1.0"
MAX_BODY_BYTES = 32 * 1024
RATE_LIMIT_MAX = 20
RATE_LIMIT_WINDOW_SECONDS = 60 * 60
PDF_RETENTION_SECONDS = 24 * 60 * 60
PDF_CLEANUP_INTERVAL_SECONDS = 60 * 60
PUBLIC_FILES = {
    "/": ROOT / "index.html",
    "/index.html": ROOT / "index.html",
    "/styles.css": ROOT / "styles.css",
    "/app.js": ROOT / "app.js",
    "/favicon.ico": ROOT / "favicon.ico",
    "/logo.png": ROOT / "logo.png",
    "/logo.svg": ROOT / "logo.svg",
}
EMAIL_RE = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
    r"[A-Za-z]{2,63}$"
)
DOMAIN_RE = re.compile(
    r"^(?=.{1,255}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$"
)
UUID_PDF_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\.pdf$"
)

rate_limit_lock = threading.Lock()
rate_limit_buckets = {}


def is_production():
    return os.getenv("APP_ENV", os.getenv("ENV", "development")).lower() == "production"


def allowed_origins():
    if is_production():
        origin = os.getenv("APP_ORIGIN", "").strip().rstrip("/")
        return {origin} if origin else set()
    return {
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8787",
        "http://127.0.0.1:8787",
    }


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


def validate_profile(profile):
    if not isinstance(profile, dict):
        return "Payload-ul trebuie sa fie un obiect JSON."

    full_name = str(profile.get("fullName", "")).strip()
    if not full_name:
        return "Numele este obligatoriu."
    if len(full_name) > 100:
        return "Numele poate avea maxim 100 de caractere."

    email = str(profile.get("email", "")).strip()
    if email and not EMAIL_RE.fullmatch(email):
        return "Email invalid."

    phone = str(profile.get("phone", "")).strip()
    if len(phone) > 25:
        return "Telefonul poate avea maxim 25 de caractere."

    usernames = profile.get("usernames", [])
    if usernames is None:
        usernames = []
    if not isinstance(usernames, list):
        return "Username-urile trebuie trimise ca lista."
    for username in usernames:
        if len(str(username).strip()) > 50:
            return "Fiecare username poate avea maxim 50 de caractere."

    domain = str(profile.get("domain", "")).strip()
    if len(domain) > 255:
        return "Domeniul poate avea maxim 255 de caractere."
    if domain and not DOMAIN_RE.fullmatch(domain):
        return "Domeniu invalid."

    return None


def check_rate_limit(ip_address):
    now = time.time()
    with rate_limit_lock:
        bucket = [
            timestamp
            for timestamp in rate_limit_buckets.get(ip_address, [])
            if now - timestamp < RATE_LIMIT_WINDOW_SECONDS
        ]
        if len(bucket) >= RATE_LIMIT_MAX:
            rate_limit_buckets[ip_address] = bucket
            return False
        bucket.append(now)
        rate_limit_buckets[ip_address] = bucket
        return True


def cleanup_old_reports():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - PDF_RETENTION_SECONDS
    for pdf_path in REPORTS_DIR.glob("*.pdf"):
        try:
            if pdf_path.stat().st_mtime < cutoff:
                pdf_path.unlink()
        except OSError:
            continue


def start_report_cleanup_thread():
    def loop():
        while True:
            time.sleep(PDF_CLEANUP_INTERVAL_SECONDS)
            cleanup_old_reports()

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()


class Handler(BaseHTTPRequestHandler):
    server_version = "ShieldTraceHTTP/1.0"

    def end_headers(self):
        origin = self.headers.get("Origin", "").strip().rstrip("/")
        if origin in allowed_origins():
            self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path.startswith("/reports/"):
            self.serve_report(path)
            return

        file_path = PUBLIC_FILES.get(path)
        if not file_path or not file_path.exists() or not file_path.is_file():
            self.send_error(404)
            return
        self.serve_file(file_path)

    def do_POST(self):
        if urlparse(self.path).path != "/api/scan":
            self.send_json(404, {"error": "Endpoint inexistent."})
            return

        if not check_rate_limit(self.client_address[0]):
            self.send_json(429, {"error": "Limita de 20 scanari pe ora pentru acest IP a fost depasita."})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_json(400, {"error": "Content-Length invalid."})
            return

        if length > MAX_BODY_BYTES:
            self.send_json(413, {"error": "Request body prea mare. Limita este 32KB."})
            return

        try:
            profile = json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            self.send_json(400, {"error": "JSON invalid."})
            return

        validation_error = validate_profile(profile)
        if validation_error:
            self.send_json(400, {"error": validation_error})
            return

        if not profile.get("consent"):
            self.send_json(403, {"error": "Consimtamantul este obligatoriu."})
            return

        started = time.time()
        evidence = scan_profile(profile)
        risk = risk_engine.calculate_risk(evidence)
        ai_summary = ai_report.generate_report(evidence, risk["score"], risk["reasons"])
        pdf_result = report_generator.generate_pdf_report(
            profile=profile,
            results=evidence,
            risk=risk,
            ai_report=ai_summary,
            reports_dir=REPORTS_DIR,
        )

        self.send_json(
            200,
            {
                "evidence": evidence,
                "risk": risk,
                "aiReport": ai_summary,
                "pdfUrl": pdf_result.get("pdf_url"),
                "pdfError": pdf_result.get("error"),
                "meta": {
                    "mode": "live API" if evidence else "live fara rezultate",
                    "braveConfigured": bool(os.getenv("BRAVE_API_KEY", "").strip()),
                    "sources": ["Brave Search", "GitHub", "Gravatar"],
                    "durationMs": round((time.time() - started) * 1000),
                    "notice": "Rezultatele sunt obtinute din API-uri publice si trebuie folosite doar cu consimtamant.",
                },
            },
        )

    def serve_report(self, path):
        filename = path.removeprefix("/reports/")
        if "/" in filename or not UUID_PDF_RE.fullmatch(filename):
            self.send_error(404)
            return

        file_path = REPORTS_DIR / filename
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404)
            return
        self.serve_file(file_path, content_type="application/pdf")

    def serve_file(self, file_path, content_type=None):
        content = file_path.read_bytes()
        detected_type = content_type or mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", detected_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    cleanup_old_reports()
    start_report_cleanup_thread()
    port = int(os.getenv("PORT", "8787"))
    host = "0.0.0.0" if is_production() else "127.0.0.1"
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"ShieldTrace live backend: http://{host}:{port}")
    print("Seteaza BRAVE_API_KEY pentru rezultate Brave Search reale.")
    server.serve_forever()


if __name__ == "__main__":
    main()
