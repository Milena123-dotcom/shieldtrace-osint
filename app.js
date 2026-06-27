const form = document.querySelector("#scanForm");
const views = document.querySelectorAll(".view");
const navItems = document.querySelectorAll(".nav-item");
const loadSample = document.querySelector("#loadSample");
const exportReport = document.querySelector("#exportReport");

const state = {
  profile: null,
  report: null,
  history: [
    { label: "Ian", score: 78 },
    { label: "Feb", score: 74 },
    { label: "Mar", score: 69 },
    { label: "Apr", score: 64 },
    { label: "Mai", score: 58 },
  ],
};

const riskRules = [
  { key: "phone", label: "Telefon public", points: 15, category: "Date personale" },
  { key: "email", label: "Email public", points: 10, category: "Date personale" },
  { key: "city", label: "Locatie aproximativa", points: 8, category: "Date personale" },
  { key: "domain", label: "Domeniu personal", points: 10, category: "Professional Exposure" },
  { key: "usernames", label: "Username reutilizat", points: 14, category: "Corelare conturi" },
  { key: "documents", label: "Documente indexate", points: 20, category: "Identity Theft" },
  { key: "social", label: "Profile sociale multiple", points: 12, category: "Social Engineering" },
  { key: "media", label: "Poze suficiente pentru impersonare", points: 11, category: "Deepfake" },
];

function escapeHtml(value) {
  return String(value)
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

function slugify(value) {
  return value.toLowerCase().replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "");
}

function sourceUrl(host, path = "") {
  return `https://${host}/${path}`.replace(/\/$/, "");
}

function generateEvidence(profile) {
  const hasModule = (name) => profile.modules.includes(name);
  const evidence = [];
  const nameSlug = slugify(profile.fullName);
  const city = profile.city || profile.country;
  const firstUsername = profile.usernames[0] || nameSlug || "profil-public";

  if (hasModule("google")) {
    evidence.push({
      id: "google-name-location",
      type: "Locatie",
      value: city,
      source: "Google Search",
      url: sourceUrl("www.google.com/search", `?q=%22${encodeURIComponent(profile.fullName)}%22`),
      snippet: `${profile.fullName} - profil public asociat cu ${city}.`,
      confidence: "medie",
      points: 8,
      category: "Date personale",
      risk: "Ajuta un atacator sa personalizeze mesajul si sa para ca iti cunoaste contextul.",
      severity: "mediu",
    });
  }

  if (hasModule("social")) {
    evidence.push({
      id: "social-profile",
      type: "Profil social",
      value: `@${firstUsername}`,
      source: "Social Media",
      url: sourceUrl("social.example", firstUsername),
      snippet: `Profil public cu numele ${profile.fullName}, fotografie, bio si locatie: ${city}.`,
      confidence: profile.usernames.length ? "ridicata" : "medie",
      points: 12,
      category: "Social Engineering",
      risk: "Poate furniza ton, interese si detalii personale pentru phishing credibil.",
      severity: "mediu",
    });
  }

  if (hasModule("documents")) {
    evidence.push({
      id: "public-document",
      type: "Document",
      value: profile.domain ? `${profile.domain}/cv-${nameSlug || "profil"}.pdf` : `CV ${profile.fullName}`,
      source: "PDF/DOC",
      url: profile.domain
        ? sourceUrl(profile.domain, `cv-${nameSlug || "profil"}.pdf`)
        : sourceUrl("documents.example", `cv-${nameSlug || "profil"}.pdf`),
      snippet: profile.email
        ? `Document indexat care contine numele ${profile.fullName}, emailul ${profile.email} si istoricul profesional.`
        : `Document indexat care contine numele ${profile.fullName} si istoricul profesional.`,
      confidence: "medie",
      points: 20,
      category: "Identity Theft",
      risk: "Documentele pot contine semnatura, istoric profesional, adresa sau date folosite la verificari de identitate.",
      severity: "ridicat",
    });
  }

  if (profile.email && hasModule("email")) {
    evidence.push({
      id: "public-email",
      type: "Email",
      value: profile.email,
      source: "Email",
      url: sourceUrl("gravatar.com", profile.email.toLowerCase()),
      snippet: `Emailul ${profile.email} apare ca identificator public si poate lega avatarul de conturi externe.`,
      confidence: "ridicata",
      points: 10,
      category: "Date personale",
      risk: "Permite cautari inverse si incercari de resetare sau corelare a conturilor.",
      severity: "mediu",
    });
  }

  if (profile.phone) {
    evidence.push({
      id: "public-phone",
      type: "Telefon",
      value: profile.phone,
      source: "Fragment public",
      url: profile.domain ? sourceUrl(profile.domain, "contact") : sourceUrl("search.example", nameSlug),
      snippet: `Numarul ${profile.phone} este asociat cu ${profile.fullName} intr-un fragment public.`,
      confidence: "medie",
      points: 15,
      category: "Date personale",
      risk: "Creste riscul de smishing, impersonare telefonica si recuperare frauduloasa de conturi.",
      severity: "ridicat",
    });
  }

  if (profile.usernames.length && hasModule("username")) {
    evidence.push({
      id: "username-reuse",
      type: "Username",
      value: profile.usernames.join(", "),
      source: "Username Search",
      url: sourceUrl("username.example", firstUsername),
      snippet: `${profile.usernames.join(", ")} apar pe mai multe platforme si pot lega hobby-uri, profil profesional si conturi personale.`,
      confidence: "ridicata",
      points: 14,
      category: "Corelare conturi",
      risk: "Reutilizarea username-ului reduce separarea dintre identitatea personala si cea profesionala.",
      severity: "ridicat",
    });
  }

  if (hasModule("social") && profile.usernames.length >= 2) {
    evidence.push({
      id: "public-media",
      type: "Media",
      value: `${Math.max(12, profile.usernames.length * 8)} fotografii estimate`,
      source: "Social Media",
      url: sourceUrl("images.example", nameSlug || firstUsername),
      snippet: `Au fost gasite mai multe fotografii publice asociate cu ${profile.fullName} si username-urile introduse.`,
      confidence: "medie",
      points: 11,
      category: "Deepfake",
      risk: "Volumul de imagini publice poate facilita impersonarea vizuala sau profilarea.",
      severity: "mediu",
    });
  }

  return evidence;
}

function scoreProfile(profile, evidence) {
  const evidenceByRule = {
    phone: evidence.filter((item) => item.type === "Telefon"),
    email: evidence.filter((item) => item.type === "Email"),
    city: evidence.filter((item) => item.type === "Locatie"),
    domain: evidence.filter((item) => profile.domain && item.url.includes(profile.domain)),
    usernames: evidence.filter((item) => item.type === "Username"),
    documents: evidence.filter((item) => item.type === "Document"),
    social: evidence.filter((item) => item.type === "Profil social"),
    media: evidence.filter((item) => item.type === "Media"),
  };

  let score = 0;
  const matches = [];
  riskRules.forEach((rule) => {
    const linkedEvidence = evidenceByRule[rule.key] || [];
    if (linkedEvidence.length) {
      score += rule.points;
      matches.push({ ...rule, evidence: linkedEvidence });
    }
  });

  score = Math.min(100, score + Math.min(12, evidence.length * 2));
  return { score, matches };
}

function levelForScore(score) {
  if (score >= 70) return { label: "HIGH", color: "var(--danger)" };
  if (score >= 45) return { label: "MEDIUM", color: "var(--warn)" };
  return { label: "LOW", color: "var(--ok)" };
}

function recommendationsFor(matches, profile) {
  const map = {
    phone: ["Ascunde sau inlocuieste numarul de telefon public", 18],
    email: ["Foloseste un email public separat de emailul personal", 11],
    city: ["Elimina orasul din fragmentele publice care il leaga de numele complet", 8],
    domain: [`Revizuieste paginile indexate de pe ${profile.domain || "domeniul personal"}`, 10],
    usernames: ["Separa username-urile personale de cele profesionale", 16],
    documents: ["Sterge sau redacteaza documentele publice care contin date personale", 20],
    social: ["Curata bio-urile si detaliile personale din profilele sociale", 15],
    media: ["Redu fotografiile publice reutilizabile pentru impersonare", 9],
  };

  return matches
    .map((rule) => ({
      title: map[rule.key][0],
      impact: map[rule.key][1],
      basedOn: rule.evidence.map((item) => `${item.type}: ${item.value}`).join(" | "),
      reason: rule.evidence[0]?.risk || "Reduce expunerea publica.",
    }))
    .sort((a, b) => b.impact - a.impact)
    .slice(0, 5);
}

function buildReport(profile, liveEvidence = null, scanMeta = null) {
  const evidence = liveEvidence?.length ? liveEvidence : generateEvidence(profile);
  const risk = scoreProfile(profile, evidence);
  const level = levelForScore(risk.score);
  const recs = recommendationsFor(risk.matches, profile);
  const socialCount = evidence.some((item) => item.type === "Profil social")
    ? Math.max(2, profile.usernames.length + 2)
    : 0;
  const documentCount = evidence.filter((item) => item.type === "Document").length;

  return {
    createdAt: new Date().toISOString(),
    profile,
    score: risk.score,
    identityTheftProbability: Math.min(95, Math.round(risk.score * 0.82 + documentCount * 9)),
    level: level.label,
    color: level.color,
    evidence,
    scanMeta,
    matchedRules: risk.matches,
    recommendations: recs,
    metrics: {
      profiles: socialCount,
      documents: documentCount,
      sensitive: risk.matches.filter((rule) => rule.category !== "Corelare conturi").length,
      photos: socialCount * 6,
    },
  };
}

async function scanOnline(profile) {
  const response = await fetch("/api/scan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile),
  });

  if (!response.ok) {
    throw new Error(`Scanarea live a esuat cu status ${response.status}`);
  }

  return response.json();
}

function renderReport(report) {
  document.querySelector("#scanState").textContent = "finalizat";
  document.querySelector("#scoreValue").textContent = report.score;
  document.querySelector("#scoreRing").style.setProperty("--score", report.score);
  document.querySelector("#scoreRing").style.setProperty("--ring-color", report.color);
  document.querySelector("#riskLevel").textContent = report.level;
  document.querySelector("#riskSummary").textContent =
    report.score >= 70
      ? "Exista dovezi suficiente pentru un atac de phishing sau impersonare credibila."
      : report.score >= 45
        ? "Exista date corelabile care merita reduse in sursele publice."
        : "Expunerea estimata este controlata, dar monitorizarea ramane utila.";

  document.querySelector("#metricsRow").innerHTML = `
    <div><strong>${report.metrics.profiles}</strong><span>profile</span></div>
    <div><strong>${report.metrics.documents}</strong><span>documente</span></div>
    <div><strong>${report.identityTheftProbability}%</strong><span>furt identitate</span></div>
  `;

  document.querySelector("#reportDate").textContent = new Intl.DateTimeFormat("ro-RO", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(report.createdAt));

  const profile = report.profile;
  document.querySelector("#aiAnalysis").textContent =
    `Pentru ${profile.fullName}, raportul este justificat de ${report.evidence.length} dovezi OSINT: ` +
    `${report.metrics.profiles} profile publice, ${report.metrics.documents} documente si ` +
    `${report.metrics.sensitive} categorii de date sensibile. Coeficientul estimat de posibilitate de furt ` +
    `de identitate este ${report.identityTheftProbability}%, deoarece datele gasite pot lega nume, contact, ` +
    `locatie, documente si identitati de cont. Prioritatea este: ` +
    `${report.recommendations[0]?.title.toLowerCase() || "monitorizarea periodica a expunerii"}.`;

  document.querySelector("#evidenceList").innerHTML = report.evidence
    .map(
      (item) => `
        <article class="evidence-card">
          <div class="evidence-topline">
            <div>
              <strong>${escapeHtml(item.type)}</strong>
              <span class="evidence-value">${escapeHtml(item.value)}</span>
            </div>
            <span class="pill">+${item.points} risc</span>
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
    .join("");

  document.querySelector("#findingTable").innerHTML = report.matchedRules
    .map(
      (rule) => `
        <div class="finding-row">
          <div>
            <strong>${escapeHtml(rule.label)}</strong>
            <span>${escapeHtml(rule.category)} · bazat pe ${rule.evidence.length} rezultat(e) gasite</span>
          </div>
          <span class="pill">+${rule.points}</span>
        </div>
      `,
    )
    .join("");

  document.querySelector("#recommendations").innerHTML = report.recommendations
    .map(
      (rec) => `
        <div class="recommendation">
          <div>
            <strong>${escapeHtml(rec.title)}</strong>
            <span>${escapeHtml(rec.reason)}</span>
            <span>Gasit: ${escapeHtml(rec.basedOn)}</span>
          </div>
          <div class="impact">${rec.impact}%</div>
        </div>
      `,
    )
    .join("");

  renderHistory(report.score);
  renderAlerts(report);
}

function renderHistory(latestScore = null) {
  const rows = latestScore
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
    .join("");
}

function renderAlerts(report = null) {
  const alerts = report
    ? [
        `A fost detectata o corelare noua pentru ${report.profile.fullName}: ${report.evidence.length} dovezi OSINT active.`,
        report.metrics.documents
          ? "Exista documente publice care ar trebui verificate si redactate manual."
          : "Nu au fost simulate documente publice noi.",
        report.identityTheftProbability > 60
          ? `Coeficientul de furt de identitate este ${report.identityTheftProbability}%, deci prioritatea este eliminarea datelor de contact si a documentelor.`
          : "Coeficientul de furt de identitate ramane moderat.",
      ]
    : ["Monitorizarea va porni dupa prima analiza."];

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
      state.report = buildReport(state.profile, liveScan.evidence, liveScan.meta);
      document.querySelector("#scanState").textContent = liveScan.meta?.mode || "live";
    } catch (error) {
      state.report = buildReport(state.profile, null, {
        mode: "demo fallback",
        warning: error.message,
      });
      document.querySelector("#scanState").textContent = "demo fallback";
    }
    renderReport(state.report);
    switchView("report");
  }, 450);
});

loadSample.addEventListener("click", () => {
  form.querySelector('[name="fullName"]').value = "Ana Popescu";
  form.querySelector('[name="country"]').value = "Romania";
  form.querySelector('[name="city"]').value = "Bucuresti";
  form.querySelector('[name="email"]').value = "ana.popescu@example.com";
  form.querySelector('[name="phone"]').value = "+40 712 345 678";
  form.querySelector('[name="usernames"]').value = "ana.pop, anap_dev, ana.photo";
  form.querySelector('[name="domain"]').value = "anapopescu.ro";
  form.querySelector('[name="consent"]').checked = true;
  switchView("scan");
});

exportReport.addEventListener("click", () => {
  if (!state.report) {
    switchView("scan");
    return;
  }

  const blob = new Blob([JSON.stringify(state.report, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `shieldtrace-report-${Date.now()}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
});

renderHistory();
renderAlerts();
