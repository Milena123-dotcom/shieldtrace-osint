const form = document.querySelector("#scanForm");
const views = document.querySelectorAll(".view");
const navItems = document.querySelectorAll(".nav-item");
const clearForm = document.querySelector("#clearForm");
const exportReport = document.querySelector("#exportReport");

const state = {
  profile: null,
  report: null,
  history: [],
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function switchView(viewName) {
  views.forEach((view) => view.classList.toggle("active", view.id === `view-${viewName}`));
  navItems.forEach((item) => item.classList.toggle("active", item.dataset.view === viewName));
}

function formToProfile() {
  const data = new FormData(form);
  return {
    fullName: data.get("fullName").trim(),
    country: data.get("country").trim(),
    city: data.get("city").trim(),
    email: data.get("email").trim(),
    phone: data.get("phone").trim(),
    usernames: data
      .get("usernames")
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean),
    domain: data.get("domain").trim(),
    modules: data.getAll("modules"),
    consent: data.get("consent") === "on",
  };
}

function evidenceDisplayValue(item) {
  return item.value || item.title || item.url || "";
}

function riskColor(level) {
  const normalized = String(level || "").toLowerCase();
  if (normalized === "critical" || normalized === "high") return "var(--danger)";
  if (normalized === "medium") return "var(--warn)";
  return "var(--ok)";
}

function buildReport(profile, scanResult = {}) {
  const risk = scanResult.risk || { score: 0, level: "Low", reasons: [] };
  const aiReport = scanResult.aiReport || {
    summary: "Nu au fost găsite informații publice.",
    attack_scenarios: [],
    recommendations: [],
  };
  const evidence = Array.isArray(scanResult.evidence) ? scanResult.evidence : [];
  const reasons = Array.isArray(risk.reasons) ? risk.reasons : [];

  return {
    createdAt: new Date().toISOString(),
    profile,
    evidence,
    risk: {
      score: Number(risk.score) || 0,
      level: risk.level || "Low",
      reasons,
    },
    aiReport,
    pdfUrl: scanResult.pdfUrl || null,
    pdfError: scanResult.pdfError || null,
    scanMeta: scanResult.meta || null,
    metrics: {
      profiles: evidence.filter((item) => ["Profil social", "github", "gravatar"].includes(item.type)).length,
      documents: evidence.filter((item) => item.type === "Document" || String(item.url || "").toLowerCase().includes(".pdf")).length,
      riskFactors: reasons.length,
    },
  };
}

async function scanOnline(profile) {
  const response = await fetch("/api/scan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile),
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || `Scanarea live a esuat cu status ${response.status}`);
  }

  return payload;
}

function renderReport(report) {
  const score = report.risk.score;
  const level = report.risk.level;
  const reasons = report.risk.reasons;
  const aiReport = report.aiReport;

  document.querySelector("#scanState").textContent = "finalizat";
  document.querySelector("#scoreValue").textContent = score;
  document.querySelector("#scoreRing").style.setProperty("--score", score);
  document.querySelector("#scoreRing").style.setProperty("--ring-color", riskColor(level));
  document.querySelector("#riskLevel").textContent = level;
  document.querySelector("#riskSummary").textContent =
    report.evidence.length === 0
      ? "Nu au fost găsite informații publice."
      : aiReport.summary || "Nu există suficiente informații publice pentru a susține acest risc.";

  document.querySelector("#metricsRow").innerHTML = `
    <div><strong>${report.metrics.profiles}</strong><span>profile</span></div>
    <div><strong>${report.metrics.documents}</strong><span>documente</span></div>
    <div><strong>${score}%</strong><span>furt identitate</span></div>
  `;

  document.querySelector("#reportDate").textContent = new Intl.DateTimeFormat("ro-RO", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(report.createdAt));

  document.querySelector("#aiAnalysis").textContent =
    report.pdfError || aiReport.summary || "Nu au fost găsite informații publice.";

  document.querySelector("#evidenceList").innerHTML = report.evidence.length
    ? report.evidence
      .map(
        (item) => `
        <article class="evidence-card">
          <div class="evidence-topline">
            <div>
              <strong>${escapeHtml(item.type)}</strong>
              <span class="evidence-value">${escapeHtml(evidenceDisplayValue(item))}</span>
            </div>
            <span class="pill">${escapeHtml(item.source)}</span>
          </div>
          <a class="evidence-url" href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">
            ${escapeHtml(item.url)}
          </a>
          <p class="evidence-snippet">${escapeHtml(item.snippet)}</p>
          <div class="evidence-meta">
            <span>Sursa: ${escapeHtml(item.source)}</span>
            <span>Incredere: ${escapeHtml(item.confidence)}</span>
          </div>
        </article>
      `,
      )
      .join("")
    : `<article class="evidence-card">Nu au fost găsite informații publice.</article>`;

  document.querySelector("#findingTable").innerHTML = reasons.length
    ? reasons
      .map(
        (reason) => `
        <div class="finding-row">
          <div>
            <strong>${escapeHtml(reason.rule)}</strong>
            <span>${escapeHtml(reason.recommendation)} · ${escapeHtml(reason.evidence_url)}</span>
          </div>
          <span class="pill">+${escapeHtml(reason.points)}</span>
        </div>
      `,
      )
      .join("")
    : `<div class="finding-row"><div><strong>Nu au fost găsite informații publice.</strong></div><span class="pill">+0</span></div>`;

  document.querySelector("#recommendations").innerHTML = aiReport.recommendations?.length
    ? aiReport.recommendations
      .map(
        (rec) => `
        <div class="recommendation">
          <div>
            <strong>${escapeHtml(rec.title)}</strong>
            <span>${escapeHtml(rec.description)}</span>
            <span>Gasit: ${escapeHtml((rec.evidence || []).join(" | "))}</span>
          </div>
          <div class="impact">${escapeHtml(rec.priority)}</div>
        </div>
      `,
      )
      .join("")
    : `<div class="recommendation"><div><strong>Nu au fost găsite informații publice.</strong></div><div class="impact">0</div></div>`;

  renderHistory(score);
  renderAlerts(report);
}

function renderHistory(latestScore = null) {
  const rows = latestScore !== null
    ? [...state.history, { label: "Acum", score: latestScore }]
    : state.history;

  document.querySelector("#historyChart").innerHTML = rows
    .map(
      (row) => `
        <div class="bar-wrap">
          <div class="bar" style="height:${Math.max(28, row.score * 2.3)}px"></div>
          <strong>${row.score}</strong>
          <span>${row.label}</span>
        </div>
      `,
    )
    .join("") || "";
}

function renderAlerts(report = null) {
  const alerts = report && report.evidence.length
    ? [
        `A fost detectata o corelare noua pentru ${report.profile.fullName}: ${report.evidence.length} dovezi OSINT active.`,
        `Scor backend: ${report.risk.score}/100, nivel ${report.risk.level}.`,
        report.risk.reasons.length
          ? `Factori de risc justificati prin dovezi: ${report.risk.reasons.length}.`
          : "Nu exista factori de risc fara dovezi.",
      ]
    : ["Nu au fost găsite informații publice."];

  document.querySelector("#alertsList").innerHTML = alerts
    .map(
      (alert, index) => `
        <div class="alert-item">
          <strong>${index === 0 ? "Status" : "Semnal"}</strong>
          <span>${escapeHtml(alert)}</span>
        </div>
      `,
    )
    .join("");
}

navItems.forEach((item) => {
  item.addEventListener("click", () => switchView(item.dataset.view));
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  document.querySelector("#scanState").textContent = "cauta live";

  window.setTimeout(async () => {
    state.profile = formToProfile();
    try {
      const liveScan = await scanOnline(state.profile);
      state.report = buildReport(state.profile, liveScan);
      document.querySelector("#scanState").textContent = liveScan.meta?.mode || "live";
    } catch (error) {
      state.report = buildReport(state.profile, {
        evidence: [],
        risk: { score: 0, level: "Low", reasons: [] },
        aiReport: {
          summary: error.message,
          attack_scenarios: [],
          recommendations: [],
        },
        meta: {
          mode: "eroare",
          warning: error.message,
        },
      });
      document.querySelector("#scanState").textContent = "eroare";
    }
    renderReport(state.report);
    switchView("report");
  }, 450);
});

clearForm.addEventListener("click", () => {
  form.reset();
  switchView("scan");
});

exportReport.addEventListener("click", () => {
  if (!state.report || !state.report.pdfUrl) {
    switchView("scan");
    return;
  }
  window.open(state.report.pdfUrl, "_blank", "noreferrer");
});

renderHistory();
renderAlerts();
