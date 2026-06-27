import datetime as _dt
import pathlib
import uuid

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
except ImportError as exc:
    colors = None
    A4 = None
    ParagraphStyle = None
    getSampleStyleSheet = None
    cm = None
    PageBreak = None
    Paragraph = None
    SimpleDocTemplate = None
    Spacer = None
    Table = None
    TableStyle = None
    REPORTLAB_IMPORT_ERROR = exc
else:
    REPORTLAB_IMPORT_ERROR = None


DISCLAIMER = (
    "Acest raport este bazat exclusiv pe informații publice și pe date furnizate de utilizator. "
    "Nu reprezintă dovada existenței unui incident de securitate."
)


def generate_pdf_report(profile: dict, results: list, risk: dict, ai_report: dict, reports_dir) -> dict:
    if REPORTLAB_IMPORT_ERROR:
        return {
            "pdf_path": None,
            "pdf_url": None,
            "error": "ReportLab nu este instalat. Instalează librăria cu: pip install reportlab",
        }

    reports_path = pathlib.Path(reports_dir)
    reports_path.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4()}.pdf"
    pdf_path = reports_path / filename

    styles = getSampleStyleSheet()
    base = ParagraphStyle(
        "ShieldBase",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#16201c"),
        spaceAfter=8,
    )
    title = ParagraphStyle(
        "ShieldTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#16201c"),
        spaceAfter=18,
    )
    heading = ParagraphStyle(
        "ShieldHeading",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=22,
        textColor=colors.HexColor("#0e6f5c"),
        spaceAfter=14,
    )
    small = ParagraphStyle(
        "ShieldSmall",
        parent=base,
        fontSize=8,
        leading=10,
    )

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=1.55 * cm,
        leftMargin=1.55 * cm,
        topMargin=1.45 * cm,
        bottomMargin=1.35 * cm,
        title="ShieldTrace Identity Exposure Assessment",
        author="Negoiță Milena-Cristina",
    )

    story = []
    _page_1(story, title, heading, base, profile, risk)
    story.append(PageBreak())
    _page_2(story, heading, base, ai_report)
    story.append(PageBreak())
    _page_3(story, heading, base, small, results)
    story.append(PageBreak())
    _page_4(story, heading, small, risk)
    story.append(PageBreak())
    _page_5(story, heading, base, ai_report)
    story.append(PageBreak())
    _page_6(story, heading, base, ai_report)
    story.append(PageBreak())
    _final_page(story, heading, base)

    doc.build(story)
    return {
        "pdf_path": str(pdf_path),
        "pdf_url": f"/reports/{filename}",
        "error": None,
    }


def _page_1(story, title, heading, base, profile, risk):
    story.append(Paragraph("ShieldTrace", title))
    story.append(Paragraph("Identity Exposure Assessment", heading))
    story.append(Spacer(1, 16))
    story.append(Paragraph(f"Numele persoanei analizate: {_safe(profile.get('fullName'))}", base))
    story.append(Paragraph(f"Data scanării: {_dt.datetime.now().strftime('%Y-%m-%d %H:%M')}", base))
    story.append(Spacer(1, 20))
    story.append(Paragraph(f"Identity Exposure Score: {_safe(risk.get('score', 0))}/100", heading))
    story.append(Paragraph(f"Nivel: {_safe(risk.get('level', 'Low'))}", base))


def _page_2(story, heading, base, ai_report):
    story.append(Paragraph("Executive Summary", heading))
    summary = _limit_words(ai_report.get("summary") or "Nu există suficiente informații publice pentru a susține acest risc.", 250)
    story.append(Paragraph(_safe(summary), base))


def _page_3(story, heading, base, small, results):
    story.append(Paragraph("Dovezi găsite", heading))
    if not results:
        story.append(Paragraph("Nu au fost găsite informații publice.", base))
        return
    for result in results:
        if not result.get("url"):
            continue
        story.append(Paragraph(f"<b>Titlu:</b> {_safe(_result_title(result))}", base))
        story.append(Paragraph(f"<b>Sursă:</b> {_safe(result.get('source'))}", base))
        story.append(Paragraph(f"<b>URL complet:</b> {_safe(result.get('url'))}", small))
        story.append(Paragraph(f"<b>Nivel încredere:</b> {_safe(result.get('confidence'))}", base))
        story.append(Paragraph(f"<b>Snippet:</b> {_safe(result.get('snippet'))}", base))
        story.append(Spacer(1, 8))


def _page_4(story, heading, small, risk):
    story.append(Paragraph("Factori de risc", heading))
    reasons = risk.get("reasons", [])
    data = [["Regulă", "Puncte", "URL dovadă", "Recomandare"]]
    for reason in reasons:
        data.append(
            [
                Paragraph(_safe(reason.get("rule")), small),
                Paragraph(str(reason.get("points", 0)), small),
                Paragraph(_safe(reason.get("evidence_url")), small),
                Paragraph(_safe(reason.get("recommendation")), small),
            ]
        )
    if len(data) == 1:
        data.append([Paragraph("Nu există factori de risc fără dovezi.", small), "", "", ""])
    _table(story, data)


def _page_5(story, heading, base, ai_report):
    story.append(Paragraph("Scenarii de atac", heading))
    scenarios = ai_report.get("attack_scenarios", [])
    if not scenarios:
        story.append(Paragraph("Nu există suficiente informații publice pentru a susține acest risc.", base))
        return
    for scenario in scenarios:
        based_on = scenario.get("based_on", [])
        if not based_on:
            continue
        story.append(Paragraph(f"<b>{_safe(scenario.get('title'))}</b>", base))
        story.append(Paragraph(_safe(scenario.get("description")), base))
        story.append(Paragraph(f"Dovezi: {_safe('; '.join(based_on))}", base))
        story.append(Spacer(1, 8))


def _page_6(story, heading, base, ai_report):
    story.append(Paragraph("Plan de remediere", heading))
    recommendations = ai_report.get("recommendations", [])
    if not recommendations:
        story.append(Paragraph("Nu există recomandări fără dovezi reale.", base))
        return
    for priority in ["High", "Medium", "Low"]:
        story.append(Paragraph(f"Prioritate {priority}", base))
        priority_items = [item for item in recommendations if item.get("priority") == priority]
        if not priority_items:
            story.append(Paragraph("Nu există recomandări pentru această prioritate.", base))
            continue
        for item in priority_items:
            evidence = item.get("evidence", [])
            if not evidence:
                continue
            story.append(Paragraph(f"<b>{_safe(item.get('title'))}</b>", base))
            story.append(Paragraph(_safe(item.get("description")), base))
            story.append(Paragraph(f"URL dovadă: {_safe('; '.join(evidence))}", base))
            story.append(Spacer(1, 8))


def _final_page(story, heading, base):
    story.append(Paragraph("Disclaimer", heading))
    story.append(Paragraph(DISCLAIMER, base))


def _table(story, data):
    table = Table(data, colWidths=[3.3 * cm, 1.6 * cm, 4.9 * cm, 6.2 * cm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2ed")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#16201c")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dfe5df")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(table)


def _result_title(result):
    return result.get("title") or result.get("value") or result.get("url") or ""


def _safe(value):
    if value is None:
        return ""
    text = str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _limit_words(text, limit):
    words = str(text).split()
    if len(words) <= limit:
        return str(text)
    return " ".join(words[:limit])
