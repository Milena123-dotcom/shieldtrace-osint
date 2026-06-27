import json
import os
import urllib.error
import urllib.request


INSUFFICIENT_INFO = "Nu există suficiente informații publice pentru a susține acest risc."
FORBIDDEN_UNSUPPORTED_PHRASES = ["probabil", "cel mai probabil", "este posibil"]


def generate_report(results: list, score: int, reasons: list, use_ai: bool = True) -> dict:
    evidence_urls = _evidence_urls(results, reasons)
    if not evidence_urls or not reasons:
        return _empty_report()

    local_report = _local_report(results, score, reasons, evidence_urls)
    if not _should_use_openai(use_ai):
        return local_report

    ai_report = _openai_report(results, score, reasons)
    if _is_supported_report(ai_report, evidence_urls):
        return ai_report
    return local_report


def _should_use_openai(use_ai):
    if not use_ai:
        return False
    if os.getenv("AI_REPORT_MODE", "").strip().lower() in {"rules", "local", "off", "disabled"}:
        return False
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def _empty_report():
    return {
        "summary": INSUFFICIENT_INFO,
        "attack_scenarios": [],
        "recommendations": [],
    }


def _local_report(results, score, reasons, evidence_urls):
    scenarios = _local_attack_scenarios(reasons)
    recommendations = _local_recommendations(reasons)
    if not scenarios and not recommendations:
        return _empty_report()

    return {
        "summary": _summary(score, reasons, evidence_urls),
        "attack_scenarios": scenarios,
        "recommendations": recommendations,
    }


def _summary(score, reasons, evidence_urls):
    rule_names = ", ".join(reason["rule"] for reason in reasons[:4])
    return (
        f"Scorul calculat este {score}. Raportul se bazează pe {len(evidence_urls)} dovezi reale "
        f"și pe regulile declanșate: {rule_names}."
    )


def _local_attack_scenarios(reasons):
    scenario_rules = [
        (
            "phishing personalizat",
            {"Email public", "Profil LinkedIn", "Profil Facebook public", "Profil Instagram public", "CV public"},
            "Datele publice citate pot fi folosite pentru a construi un mesaj adaptat identității persoanei.",
        ),
        (
            "resetare cont",
            {"Email public", "Telefon public"},
            "Datele de contact citate pot fi folosite în încercări de recuperare sau validare a conturilor.",
        ),
        (
            "impersonare",
            {"Profil LinkedIn", "Profil Facebook public", "Profil Instagram public", "Profil GitHub", "Profil Gravatar"},
            "Profilele publice citate pot oferi elemente de identitate reutilizabile în impersonare.",
        ),
        (
            "social engineering",
            {"Telefon public", "Profil LinkedIn", "Profil Facebook public", "Profil Instagram public", "Profil GitHub", "Profil Gravatar", "CV public"},
            "Dovezile citate pot oferi context pentru abordări directe și mesaje credibile.",
        ),
        (
            "doxing",
            {"Document PDF public", "CV public", "Mai mult de 10 rezultate publice", "Mai mult de 20 rezultate publice"},
            "Documentele sau volumul mare de rezultate citate cresc expunerea publică a identității.",
        ),
    ]

    scenarios = []
    for title, rule_names, description in scenario_rules:
        matched = [reason for reason in reasons if reason.get("rule") in rule_names and reason.get("evidence_url")]
        if matched:
            scenarios.append(
                {
                    "title": title,
                    "description": description,
                    "based_on": _unique_urls(reason["evidence_url"] for reason in matched),
                }
            )
    return scenarios


def _local_recommendations(reasons):
    priority_by_points = lambda points: "High" if points >= 20 else "Medium" if points >= 8 else "Low"
    recommendations = []
    for reason in reasons:
        evidence_url = reason.get("evidence_url", "")
        if not evidence_url:
            continue
        recommendations.append(
            {
                "priority": priority_by_points(reason.get("points", 0)),
                "title": reason.get("rule", ""),
                "description": f"{reason.get('recommendation', '')} Dovada: {evidence_url}.",
                "evidence": [evidence_url],
            }
        )
    return recommendations


def _openai_report(results, score, reasons):
    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        "input": [
            {
                "role": "system",
                "content": (
                    "Generează exclusiv JSON valid pentru un raport OSINT defensiv. "
                    "Nu inventa informații. Orice afirmație trebuie să citeze URL-uri din datele primite. "
                    f"Dacă dovezile nu susțin riscul, folosește exact: {INSUFFICIENT_INFO} "
                    "Nu folosi expresiile: Probabil, Cel mai probabil, Este posibil, decât dacă există dovezi citate. "
                    "Nu căuta pe internet."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "results": _compact_results(results),
                        "risk": {"score": score, "reasons": reasons},
                        "required_schema": {
                            "summary": "",
                            "attack_scenarios": [{"title": "", "description": "", "based_on": []}],
                            "recommendations": [{"priority": "High|Medium|Low", "title": "", "description": "", "evidence": []}],
                        },
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "text": {"format": {"type": "json_object"}},
    }

    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY', '').strip()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None

    text = _extract_response_text(body)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _extract_response_text(response_body):
    if response_body.get("output_text"):
        return response_body["output_text"]

    chunks = []
    for item in response_body.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                chunks.append(content["text"])
    return "".join(chunks)


def _is_supported_report(report, evidence_urls):
    if not isinstance(report, dict):
        return False
    if not isinstance(report.get("summary"), str):
        return False
    if _contains_forbidden_unsupported_phrase(report):
        return False

    scenarios = report.get("attack_scenarios")
    recommendations = report.get("recommendations")
    if not isinstance(scenarios, list) or not isinstance(recommendations, list):
        return False

    for scenario in scenarios:
        if not _valid_evidence_list(scenario.get("based_on"), evidence_urls):
            return False
        if scenario.get("based_on") and not scenario.get("description"):
            return False

    for recommendation in recommendations:
        if recommendation.get("priority") not in {"High", "Medium", "Low"}:
            return False
        if not _valid_evidence_list(recommendation.get("evidence"), evidence_urls):
            return False
        if recommendation.get("evidence") and not recommendation.get("description"):
            return False
    return True


def _valid_evidence_list(urls, evidence_urls):
    if not isinstance(urls, list) or not urls:
        return False
    return all(url in evidence_urls for url in urls)


def _contains_forbidden_unsupported_phrase(report):
    text = json.dumps(report, ensure_ascii=False).lower()
    return any(phrase in text for phrase in FORBIDDEN_UNSUPPORTED_PHRASES)


def _evidence_urls(results, reasons):
    urls = [item.get("url", "") for item in results]
    urls.extend(reason.get("evidence_url", "") for reason in reasons)
    return set(url for url in urls if url)


def _compact_results(results):
    compact = []
    for item in results:
        if not item.get("url"):
            continue
        compact.append(
            {
                "type": item.get("type", ""),
                "title": item.get("title") or item.get("value", ""),
                "url": item.get("url", ""),
                "source": item.get("source", ""),
                "snippet": item.get("snippet", ""),
                "metadata": item.get("metadata", {}),
            }
        )
    return compact


def _unique_urls(urls):
    seen = set()
    unique = []
    for url in urls:
        if url and url not in seen:
            seen.add(url)
            unique.append(url)
    return unique
