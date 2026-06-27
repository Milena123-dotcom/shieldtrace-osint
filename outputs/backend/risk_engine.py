import re
from urllib.parse import urlparse


MAX_SCORE = 100
EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
    r"[A-Za-z]{2,63}\b"
)


def calculate_risk(results: list) -> dict:
    evidence = [item for item in results if item.get("url")]
    if not evidence:
        return {"score": 0, "level": "Low", "reasons": []}

    reasons = []
    reasons.extend(_single_match_rules(evidence))
    reasons.extend(_volume_rules(evidence))

    score = min(MAX_SCORE, sum(reason["points"] for reason in reasons))
    return {
        "score": score,
        "level": _level_for_score(score),
        "reasons": reasons,
    }


def _single_match_rules(evidence):
    rules = [
        {
            "rule": "Email public",
            "points": 10,
            "predicate": _has_real_email,
            "recommendation": "Elimina emailul din paginile publice sau foloseste un email dedicat pentru expunere publica.",
        },
        {
            "rule": "Telefon public",
            "points": 20,
            "predicate": lambda item: _contains_any(item, ["telefon", "phone", "tel:"]) or item.get("type") == "Telefon",
            "recommendation": "Elimina numarul de telefon din paginile publice unde este asociat cu identitatea ta.",
        },
        {
            "rule": "Document PDF public",
            "points": 25,
            "predicate": lambda item: _url_contains(item, ".pdf") or item.get("type") == "Document",
            "recommendation": "Sterge, muta sau redacteaza documentele PDF publice care contin date personale.",
        },
        {
            "rule": "CV public",
            "points": 20,
            "predicate": lambda item: _contains_any(item, [" cv", "curriculum vitae", "resume"]),
            "recommendation": "Inlocuieste CV-ul public cu o versiune redactata sau limiteaza accesul la document.",
        },
        {
            "rule": "Profil LinkedIn",
            "points": 8,
            "predicate": lambda item: _domain_contains(item, "linkedin.com"),
            "recommendation": "Revizuieste informatiile publice din profilul LinkedIn si limiteaza detaliile sensibile.",
        },
        {
            "rule": "Profil Facebook public",
            "points": 10,
            "predicate": lambda item: _domain_contains(item, "facebook.com"),
            "recommendation": "Verifica setarile de confidentialitate pentru profilul Facebook public.",
        },
        {
            "rule": "Profil Instagram public",
            "points": 8,
            "predicate": lambda item: _domain_contains(item, "instagram.com"),
            "recommendation": "Limiteaza detaliile personale si media publice vizibile in Instagram.",
        },
        {
            "rule": "Profil GitHub",
            "points": 5,
            "predicate": lambda item: item.get("type") == "github" or item.get("source") == "GitHub",
            "recommendation": "Revizuieste profilul GitHub public si separa identitatea profesionala de cea personala.",
        },
        {
            "rule": "Profil Gravatar",
            "points": 5,
            "predicate": lambda item: item.get("type") == "gravatar" or item.get("source") == "Gravatar",
            "recommendation": "Verifica profilul Gravatar si elimina datele personale care nu trebuie sa fie publice.",
        },
    ]

    reasons = []
    for rule in rules:
        match = next((item for item in evidence if rule["predicate"](item)), None)
        if match:
            reasons.append(_reason(rule["rule"], rule["points"], match["url"], rule["recommendation"]))
    return reasons


def _volume_rules(evidence):
    count = len(evidence)
    if count > 20:
        return [
            _reason(
                "Mai mult de 20 rezultate publice",
                20,
                evidence[0]["url"],
                "Prioritizeaza eliminarea sau reducerea expunerii din sursele cu cele mai multe date personale.",
            )
        ]
    if count > 10:
        return [
            _reason(
                "Mai mult de 10 rezultate publice",
                10,
                evidence[0]["url"],
                "Redu numarul de pagini publice care asociaza numele cu date personale.",
            )
        ]
    return []


def _reason(rule, points, evidence_url, recommendation):
    return {
        "rule": rule,
        "points": points,
        "evidence_url": evidence_url,
        "recommendation": recommendation,
    }


def _level_for_score(score):
    if score >= 80:
        return "Critical"
    if score >= 60:
        return "High"
    if score >= 30:
        return "Medium"
    return "Low"


def _contains_any(item, terms):
    haystack = " ".join(
        [
            item.get("title", ""),
            item.get("value", ""),
            item.get("url", ""),
            item.get("snippet", ""),
        ]
    ).lower()
    return any(term.lower() in haystack for term in terms)


def _has_real_email(item):
    haystack = " ".join(
        [
            item.get("title", ""),
            item.get("value", ""),
            item.get("url", ""),
            item.get("snippet", ""),
        ]
    )
    return bool(EMAIL_RE.search(haystack))


def _url_contains(item, term):
    return term.lower() in item.get("url", "").lower()


def _domain_contains(item, domain):
    hostname = urlparse(item.get("url", "")).hostname or ""
    return domain in hostname.lower()
