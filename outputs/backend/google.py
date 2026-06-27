import hashlib

from .search_provider import SearchProvider


QUERY_DEFINITIONS = [
    ("general", '"{full_name}"', "Locatie", 8, "Date personale"),
    ("linkedin", '"{full_name}" site:linkedin.com', "Profil social", 12, "Social Engineering"),
    ("facebook", '"{full_name}" site:facebook.com', "Profil social", 12, "Social Engineering"),
    ("instagram", '"{full_name}" site:instagram.com', "Profil social", 12, "Social Engineering"),
    ("pdf", '"{full_name}" filetype:pdf', "Document", 20, "Identity Theft"),
    ("cv", '"{full_name}" CV', "Document", 20, "Identity Theft"),
    ("email", '"{full_name}" email', "Email", 10, "Date personale"),
    ("phone", '"{full_name}" telefon', "Telefon", 15, "Date personale"),
]

RISKS = {
    "Locatie": "Rezultatul leaga numele de un context public, util pentru phishing personalizat.",
    "Profil social": "Profilul social poate furniza imagine, rol, contacte, interese sau relatii.",
    "Document": "Documentele publice pot contine CV, semnatura, date de contact sau istoric profesional.",
    "Email": "Emailul gasit public permite corelarea conturilor si incercari de resetare.",
    "Telefon": "Telefonul public creste riscul de smishing, impersonare si recuperare frauduloasa.",
}


def evidence_from_result(result, evidence_type, points, category):
    url = result.get("url", "")
    if not url:
        return None

    snippet = result.get("snippet", "")
    title = result.get("title", "") or url
    return {
        "id": hashlib.sha1(f"{evidence_type}:{url}:{snippet}".encode("utf-8")).hexdigest()[:12],
        "type": evidence_type,
        "value": title,
        "source": result.get("source", "Brave Search"),
        "url": url,
        "snippet": snippet,
        "confidence": result.get("confidence", "high"),
        "points": points,
        "category": category,
        "risk": RISKS[evidence_type],
        "severity": "ridicat" if points >= 15 else "mediu",
    }


def scan(profile):
    full_name = profile.get("fullName", "").strip()
    if not full_name:
        return []

    provider = SearchProvider()
    evidence = []
    for _, template, evidence_type, points, category in QUERY_DEFINITIONS:
        query = template.format(full_name=full_name)
        for result in provider.search(query):
            evidence_item = evidence_from_result(result, evidence_type, points, category)
            if evidence_item:
                evidence.append(evidence_item)
    return evidence
