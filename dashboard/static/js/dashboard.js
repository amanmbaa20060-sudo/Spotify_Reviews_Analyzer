const API = "/api";
let researchData = [];
let activeRq = "rq1";

function qs(id) { return document.getElementById(id); }

function sinceParam() {
  const days = qs("filter-days")?.value;
  return days ? `since_days=${days}` : "";
}

async function fetchJson(path) {
  const res = await fetch(`${API}${path}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function stars(n) {
  if (!n) return "—";
  return "★".repeat(n) + "☆".repeat(5 - n);
}

function renderOverview(data) {
  const ps = data.play_store;
  const as = data.app_store;
  qs("kpi-play-store").textContent = ps.average?.toFixed(1) ?? "—";
  qs("kpi-app-store").textContent = as.average?.toFixed(1) ?? "—";
  qs("kpi-play-count").textContent = `${ps.count} reviews`;
  qs("kpi-app-count").textContent = `${as.count} reviews`;
  qs("kpi-total").textContent = data.total_records.toLocaleString();
  qs("kpi-processed").textContent = `${data.processed_records.toLocaleString()} analyzed`;

  const mix = data.sentiment_mix || {};
  const bar = qs("sentiment-bar");
  const legend = qs("sentiment-legend");
  bar.innerHTML = "";
  legend.innerHTML = "";
  const colors = { positive: "#1db954", negative: "#ef4444", neutral: "#9ca3af", unknown: "#d1d5db" };
  Object.entries(mix).forEach(([k, v]) => {
    const seg = document.createElement("div");
    seg.className = "sentiment-seg";
    seg.style.width = `${v}%`;
    seg.style.background = colors[k] || "#9ca3af";
    bar.appendChild(seg);
    legend.innerHTML += `${k.toUpperCase()} ${v}% · `;
  });
}

function sourceLabel(key) {
  if (key === "app_store") return "iOS";
  if (key === "play_store") return "Android";
  return key;
}

function renderRqTabs() {
  const el = qs("rq-selector");
  el.innerHTML = researchData.map((rq) =>
    `<button class="rq-tab ${rq.rq_id === activeRq ? "active" : ""}" data-rq="${rq.rq_id}">${rq.rq_id.toUpperCase()}</button>`
  ).join("");
  el.querySelectorAll(".rq-tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      activeRq = btn.dataset.rq;
      renderActiveRq();
      renderRqTabs();
    });
  });
}

function renderRqEvidenceList(evidence) {
  const evidenceEl = qs("rq-evidence-list");
  if (!evidenceEl) return;
  if (!evidence.length) {
    evidenceEl.innerHTML = "<p class='rq-evidence-empty'>No negative problem reviews found for this RQ yet.</p>";
    return;
  }
  evidenceEl.innerHTML = evidence.map((item, idx) => `
    <article class="rq-evidence-item" data-idx="${idx}" tabindex="0" role="button">
      <div class="rq-evidence-meta">
        <span class="rq-evidence-rank">#${idx + 1}</span>
        <strong>${sourceLabel(item.source_key)}</strong>
        <span class="pill negative">NEGATIVE</span>
        <span class="stars">${stars(item.rating)}</span>
      </div>
      <p class="rq-evidence-theme">${escapeHtml(item.theme_label || item.theme_id || "")}</p>
      <blockquote>${escapeHtml(item.snippet)}</blockquote>
    </article>
  `).join("");
  evidenceEl.querySelectorAll(".rq-evidence-item").forEach((card) => {
    const idx = Number(card.dataset.idx);
    const open = () => openCitation(evidence[idx]);
    card.addEventListener("click", open);
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        open();
      }
    });
  });
}

async function loadRqEvidence() {
  const evidenceEl = qs("rq-evidence-list");
  if (!evidenceEl) return;
  evidenceEl.innerHTML = "<p class='rq-evidence-empty'>Loading negative reviews…</p>";
  try {
    const data = await fetchJson(`/research-questions/${activeRq}/top-evidence`);
    renderRqEvidenceList(data.items || []);
  } catch (e) {
    evidenceEl.innerHTML = `<p class='rq-evidence-empty'>Could not load evidence. ${escapeHtml(String(e.message))}</p>`;
  }
}

function renderRqFactors(analysis) {
  const factorsEl = qs("active-rq-factors");
  const segmentsEl = qs("active-rq-segments");
  if (!factorsEl) return;

  const causes = analysis?.root_causes || [];
  if (!causes.length) {
    factorsEl.innerHTML = "<p class='rq-evidence-empty'>No weighted factors available.</p>";
    segmentsEl?.classList.add("hidden");
    return;
  }

  factorsEl.innerHTML = causes.map((factor) => `
    <article class="rq-factor-item">
      <div class="rq-factor-header">
        <span class="rq-factor-label">${escapeHtml(factor.label)}</span>
        <span class="rq-factor-weight">${factor.weight}%</span>
      </div>
      <div class="rq-factor-bar-track">
        <div class="rq-factor-bar-fill" style="width:${Math.min(factor.weight, 100)}%"></div>
      </div>
      <p class="rq-factor-desc">${escapeHtml(factor.description)}</p>
      <div class="rq-factor-meta">
        <span>${factor.mention_count} mentions</span>
        <span>${factor.negative_share}% negative</span>
        ${factor.top_sources ? Object.entries(factor.top_sources).slice(0, 2).map(([k, v]) =>
          `<span>${sourceLabel(k)} ${v}%</span>`).join("") : ""}
      </div>
    </article>
  `).join("");

  const segments = analysis?.segment_factors || [];
  if (segmentsEl) {
    if (!segments.length) {
      segmentsEl.classList.add("hidden");
      segmentsEl.innerHTML = "";
    } else {
      segmentsEl.classList.remove("hidden");
      segmentsEl.innerHTML = `
        <h3>SEGMENT SIGNALS</h3>
        <ul class="rq-segment-list">${segments.map((s) =>
          `<li><strong>${s.weight}%</strong> — ${escapeHtml(s.label)}</li>`).join("")}</ul>`;
    }
  }
}

async function loadRqProblemAnalysis() {
  const summaryEl = qs("active-rq-problem");
  const factorsEl = qs("active-rq-factors");
  if (!summaryEl || !factorsEl) return;
  summaryEl.textContent = "Loading problem analysis…";
  factorsEl.innerHTML = "";
  try {
    const data = await fetchJson(`/research-questions/${activeRq}/problem-analysis`);
    const analysis = data.problem_analysis || {};
    summaryEl.textContent = data.problem_summary || analysis.summary || "";
    renderRqFactors(analysis);
    const rq = researchData.find((r) => r.rq_id === activeRq);
    if (rq) {
      rq.problem_analysis = analysis;
      rq.problem_summary = summaryEl.textContent;
    }
  } catch (e) {
    summaryEl.textContent = "Could not load problem analysis.";
    factorsEl.innerHTML = `<p class='rq-evidence-empty'>${escapeHtml(String(e.message))}</p>`;
  }
}

async function renderActiveRq() {
  const rq = researchData.find((r) => r.rq_id === activeRq);
  if (!rq) return;
  qs("active-rq-id").textContent = rq.rq_id.toUpperCase();
  qs("active-rq-title").textContent = rq.label;
  qs("active-rq-tags").innerHTML = (rq.tags || []).map((t) => `<span class="tag">${t}</span>`).join("");
  qs("active-rq-solutions").innerHTML = (rq.proposed_solutions || []).map((s) => `<li>${s}</li>`).join("");
  qs("readiness-score").textContent = rq.readiness_score ?? "—";
  qs("readiness-meta").innerHTML = `
    <div>Reviews: <strong>${rq.review_count}</strong></div>
    <div>Readiness: <strong>${rq.readiness}</strong></div>
    <div>Evidence: <strong>…</strong> reviews</div>
  `;
  await Promise.all([loadRqProblemAnalysis(), loadRqEvidence()]);
  const rqAgain = researchData.find((r) => r.rq_id === activeRq);
  if (!rqAgain) return;
  const count = (qs("rq-evidence-list")?.querySelectorAll(".rq-evidence-item").length) || 0;
  qs("readiness-meta").innerHTML = `
    <div>Reviews: <strong>${rqAgain.review_count}</strong></div>
    <div>Readiness: <strong>${rqAgain.readiness}</strong></div>
    <div>Evidence: <strong>${count}</strong> negative reviews</div>
  `;
}

function openCitation(c) {
  if (!c) return;
  qs("drawer-body").innerHTML = `
    <p><strong>Review ID:</strong> <code>${c.review_id}</code></p>
    <p><strong>Source:</strong> ${sourceLabel(c.source_key)}</p>
    <p><strong>Rating:</strong> ${stars(c.rating)}</p>
    <p><strong>Sentiment:</strong> ${c.sentiment || "n/a"}</p>
    <p><strong>Theme:</strong> ${escapeHtml(c.theme_label || c.theme_id || "n/a")}</p>
    <p><strong>Confidence:</strong> ${c.confidence ?? "n/a"}</p>
    <blockquote>${escapeHtml(c.snippet)}</blockquote>
  `;
  qs("citation-drawer").classList.remove("hidden");
}

async function loadFeedback() {
  const source = qs("feedback-source").value;
  const data = await fetchJson(`/reviews/recent?source_key=${source}&limit=8`);
  qs("feedback-list").innerHTML = data.items.map((r) => `
    <article class="feedback-item">
      <div class="feedback-meta">
        <strong>${r.source_key === "app_store" ? "iOS" : r.source_key === "play_store" ? "Android" : r.source_key}</strong>
        <span class="pill ${r.sentiment || "neutral"}">${(r.sentiment || "neutral").toUpperCase()}</span>
        <span class="stars">${stars(r.rating)}</span>
      </div>
      <p>${escapeHtml(r.text).slice(0, 220)}${r.text.length > 220 ? "…" : ""}</p>
    </article>
  `).join("") || "<p>No reviews found.</p>";
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function renderThemeBars(themes, containerId) {
  const el = qs(containerId);
  if (!themes.length) { el.innerHTML = "<p>No themes.</p>"; return; }
  const max = Math.max(...themes.map((t) => t.count));
  el.innerHTML = themes.map((t) => {
    const pct = Math.round((t.count / max) * 100);
    return `
      <div class="theme-row">
        <span>${t.label}</span>
        <div class="theme-bar-track"><div class="theme-bar-fill" style="width:${pct}%"></div></div>
        <span>${t.count}</span>
      </div>`;
  }).join("");
}

function renderWordCloud(items) {
  const el = qs("word-cloud");
  if (!items.length) { el.innerHTML = "<span style='color:#9ca3af'>No keywords</span>"; return; }
  el.innerHTML = items.map((w) => {
    const size = 0.75 + w.weight * 1.25;
    return `<span style="font-size:${size}rem" title="${w.count} mentions">${w.text}</span>`;
  }).join("");
}

async function loadThemes() {
  const suffix = sinceParam() ? `?${sinceParam()}&limit=8` : "?limit=8";
  const data = await fetchJson(`/aggregates/themes${suffix}`);
  renderThemeBars(data.items, "theme-bars");
  const wc = await fetchJson("/word-cloud");
  renderWordCloud(wc.items);
}

async function loadResearch() {
  const data = await fetchJson("/research-questions");
  researchData = data.items;
  renderRqTabs();
  renderActiveRq();
  qs("research-grid").innerHTML = researchData.map((rq) => {
    const topFactor = rq.problem_analysis?.root_causes?.[0];
    const factorHint = topFactor
      ? `<p class="research-factor-hint">Top driver: ${escapeHtml(topFactor.label)} (${topFactor.weight}%)</p>`
      : "";
    return `
    <article class="card research-card" data-rq="${rq.rq_id}">
      <div class="rq-panel-header"><span class="badge-active">${rq.readiness}</span><span>${rq.rq_id.toUpperCase()}</span></div>
      <h3>${rq.label}</h3>
      <p>${(rq.problem_summary || "").slice(0, 160)}${(rq.problem_summary || "").length > 160 ? "…" : ""}</p>
      ${factorHint}
      <div class="tag-row">${(rq.tags || []).slice(0,3).map(t => `<span class="tag">${t}</span>`).join("")}</div>
      <p><strong>${rq.review_count}</strong> reviews · Score <strong>${rq.readiness_score}/100</strong></p>
    </article>`;
  }).join("");
  document.querySelectorAll(".research-card").forEach((card) => {
    card.addEventListener("click", () => {
      activeRq = card.dataset.rq;
      switchView("overview");
      renderRqTabs();
      renderActiveRq();
    });
  });
}

async function loadSentiment() {
  const suffix = sinceParam() ? `?${sinceParam()}` : "";
  const data = await fetchJson(`/aggregates/sentiment${suffix}`);
  const rows = data.items;
  qs("sentiment-table").innerHTML = `
    <table><thead><tr><th>Source</th><th>Sentiment</th><th>Count</th></tr></thead>
    <tbody>${rows.map(r => `<tr><td>${r.source_key}</td><td>${r.sentiment}</td><td>${r.count}</td></tr>`).join("")}
    </tbody></table>`;
  const ratings = await fetchJson(`/aggregates/ratings${suffix}`);
  drawRatingsChart(ratings.items);
}

function drawRatingsChart(items) {
  const canvas = qs("ratings-chart");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  canvas.width = canvas.offsetWidth * dpr;
  canvas.height = 120 * dpr;
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const sources = ["app_store", "play_store"];
  const ratings = [1, 2, 3, 4, 5];
  const grouped = {};
  items.forEach((i) => {
    grouped[`${i.source_key}-${i.rating}`] = i.count;
  });
  const barW = 24;
  const gap = 12;
  let x = 30;
  ratings.forEach((r) => {
    sources.forEach((s, si) => {
      const count = grouped[`${s}-${r}`] || 0;
      const h = Math.min(count * 2, 90);
      ctx.fillStyle = si === 0 ? "#1db954" : "#86efac";
      ctx.fillRect(x, 100 - h, barW, h);
      x += barW + 4;
    });
    x += gap;
  });
}

async function loadUnmetNeeds() {
  const data = await fetchJson("/unmet-needs?limit=8");
  qs("unmet-needs-list").innerHTML = data.items.map((i) =>
    `<div class="theme-row"><span>${i.label}</span><div class="theme-bar-track"><div class="theme-bar-fill" style="width:${Math.min(i.severity_score * 5, 100)}%"></div></div><span>${i.severity_score}</span></div>`
  ).join("") || "<p>No unmet needs data.</p>";
}

async function refreshAll() {
  const suffix = sinceParam() ? `?${sinceParam()}` : "";
  const overview = await fetchJson(`/overview${suffix}`);
  renderOverview(overview);
  await loadResearch();
  await loadFeedback();
  await loadThemes();
  await loadSentiment();
  await loadUnmetNeeds();
  const themesFull = await fetchJson(`/aggregates/themes?limit=15${sinceParam() ? `&${sinceParam()}` : ""}`);
  renderThemeBars(themesFull.items, "themes-full-list");
}

function switchView(name) {
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach((n) => n.classList.remove("active"));
  qs(`view-${name}`)?.classList.add("active");
  document.querySelector(`.nav-item[data-view="${name}"]`)?.classList.add("active");
}

function setupNav() {
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.addEventListener("click", () => switchView(btn.dataset.view));
  });
}

function setupExports() {
  const csv = () => { window.open(`/api/export/csv?${sinceParam()}`, "_blank"); };
  const md = () => { window.open("/api/export/markdown", "_blank"); };
  qs("btn-export-csv")?.addEventListener("click", csv);
  qs("btn-export-md")?.addEventListener("click", md);
  qs("footer-export-csv")?.addEventListener("click", (e) => { e.preventDefault(); csv(); });
  qs("footer-export-md")?.addEventListener("click", (e) => { e.preventDefault(); md(); });
  qs("btn-export-rq")?.addEventListener("click", md);
}

function setupAgent() {
  qs("btn-ask-agent")?.addEventListener("click", async () => {
    const question = qs("agent-question").value.trim();
    if (!question) return;
    const rq = qs("agent-rq").value;
    const body = { question, rq_id: rq || null };
    qs("agent-answer").classList.remove("hidden");
    qs("agent-answer").textContent = "Thinking…";
    try {
      const res = await fetch(`${API}/agent/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      qs("agent-answer").textContent = data.answer + (data.citations?.length ? `\n\nCitations: ${data.citations.join(", ")}` : "");
    } catch (e) {
      qs("agent-answer").textContent = `Error: ${e.message}`;
    }
  });
}

function setupFilters() {
  ["filter-days", "filter-source", "feedback-source"].forEach((id) => {
    qs(id)?.addEventListener("change", refreshAll);
  });
}

qs("drawer-close")?.addEventListener("click", () => qs("citation-drawer").classList.add("hidden"));
qs("citation-drawer")?.addEventListener("click", (e) => {
  if (e.target.id === "citation-drawer") qs("citation-drawer").classList.add("hidden");
});

setupNav();
setupExports();
setupAgent();
setupFilters();
refreshAll().catch((e) => console.error(e));
