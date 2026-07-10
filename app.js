/* Team India Dashboard — app logic */

let DATA = null;
let OFFICIAL = null;
let PLAYER_IMGS = {}; // normalized name -> path
const charts = {};
const PAGE_SIZE = 40;
let matchPage = 0;
let officialFmt = "test";
let officialRendered = false;

function normalizePlayerName(name) {
  return String(name || "")
    .toLowerCase()
    .replace(/\./g, " ")
    .replace(/[^a-z0-9\s]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

const COMMON_SURNAMES = new Set([
  "singh", "kumar", "sharma", "khan", "patel", "yadav", "shah", "das", "roy", "dev",
]);

function registerPlayerImages(map, base = "images/players/") {
  PLAYER_IMGS = {};
  Object.entries(map || {}).forEach(([name, file]) => {
    const path = file.startsWith("images/") || file.startsWith("http") ? file : base + file;
    const n = normalizePlayerName(name);
    PLAYER_IMGS[n] = path;
    const parts = n.split(" ").filter(Boolean);
    if (parts.length >= 2) {
      PLAYER_IMGS[parts.slice(-2).join(" ")] = path;
      // only index unique last names (not Singh/Kumar/etc.)
      const last = parts[parts.length - 1];
      if (last.length > 3 && !COMMON_SURNAMES.has(last)) {
        PLAYER_IMGS[last] = PLAYER_IMGS[last] || path;
      }
    }
  });
}

function playerImgSrc(name) {
  if (!name) return null;
  const n = normalizePlayerName(name);
  if (PLAYER_IMGS[n]) return PLAYER_IMGS[n];
  const parts = n.split(" ").filter(Boolean);
  if (parts.length >= 2) {
    const last2 = parts.slice(-2).join(" ");
    if (PLAYER_IMGS[last2]) return PLAYER_IMGS[last2];
  }
  // Prefer longer key matches (full names) over short
  let best = null;
  let bestLen = 0;
  for (const [k, v] of Object.entries(PLAYER_IMGS)) {
    if (k.length < 5) continue;
    if (n === k) return v;
    if ((n.includes(k) || k.includes(n)) && k.length > bestLen) {
      best = v;
      bestLen = k.length;
    }
  }
  if (best) return best;
  if (parts.length) {
    const last = parts[parts.length - 1];
    if (last.length > 3 && !COMMON_SURNAMES.has(last) && PLAYER_IMGS[last]) return PLAYER_IMGS[last];
  }
  return null;
}

function playerAvatar(name, size = "md") {
  const src = playerImgSrc(name);
  const initials = String(name || "?")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
  if (src) {
    return `<span class="avatar avatar-${size}" title="${name}"><img src="${src}" alt="${name}" loading="lazy" onerror="this.parentElement.classList.add('no-img');this.remove()" /></span>`;
  }
  return `<span class="avatar avatar-${size} avatar-fallback" title="${name || ""}">${initials || "?"}</span>`;
}

function playerCell(name) {
  return `<span class="player-cell">${playerAvatar(name, "sm")}<span class="player">${name}</span></span>`;
}

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

const FMT_COLORS = {
  Test: "#4F8CFF",
  ODI: "#00E5FF",
  T20: "#FF2D78",
};

const RESULT_BADGE = {
  won: "badge-won",
  lost: "badge-lost",
  draw: "badge-draw",
  tied: "badge-tied",
  nr: "badge-nr",
};

function fmtNum(n) {
  if (n == null || Number.isNaN(n)) return "—";
  return Number(n).toLocaleString("en-IN");
}

function fmtPct(n) {
  if (n == null) return "—";
  return `${n}%`;
}

function resultLabel(r) {
  return ({ won: "Won", lost: "Lost", draw: "Draw", tied: "Tied", nr: "N/R" })[r] || r;
}

function destroyChart(key) {
  if (charts[key]) {
    charts[key].destroy();
    delete charts[key];
  }
}

function chartDefaults() {
  Chart.defaults.color = "#8B8B9E";
  Chart.defaults.borderColor = "rgba(30,30,42,0.9)";
  Chart.defaults.font.family = "Inter, system-ui, sans-serif";
}

/* ── Sidebar ── */
function openSidebar() {
  $("#sidebar")?.classList.add("open");
  $("#sidebarBackdrop")?.classList.add("open");
  document.body.style.overflow = "hidden";
}
function closeSidebar() {
  $("#sidebar")?.classList.remove("open");
  $("#sidebarBackdrop")?.classList.remove("open");
  document.body.style.overflow = "";
}

/* ── Navigation ── */
function showView(name) {
  $$(".view").forEach((v) => v.classList.add("hidden"));
  const el = $(`#view-${name}`);
  if (el) el.classList.remove("hidden");
  $$(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.view === name));
  closeSidebar();
  window.scrollTo({ top: 0, behavior: "smooth" });

  if (name === "official") renderOfficial();
  if (name === "formats") renderFormats();
  if (name === "batting") renderBatting();
  if (name === "bowling") renderBowling();
  if (name === "fielding") renderFielding();
  if (name === "h2h") renderH2H();
  if (name === "venues") renderVenues();
  if (name === "records") renderRecords();
  if (name === "matches") renderMatches();
  if (name === "missing") renderMissing();
}

/* ── Official Records ── */
function renderOfficial() {
  if (!OFFICIAL) return;

  if (!officialRendered) {
    officialRendered = true;
    const o = OFFICIAL.overall;
    $("#officialAsOf").textContent = `Compiled as of ${OFFICIAL.meta.as_of} · Tests ${o.tests.as_of} · ODIs ${o.odis.as_of} · T20Is ${o.t20is.as_of}`;
    $("#officialNote").textContent = OFFICIAL.meta.note;

    const tiles = [
      { label: "Tests", value: o.tests.played, sub: `${o.tests.won}W · ${o.tests.lost}L · ${o.tests.draw}D · ${o.tests.win_pct}%`, accent: "#4F8CFF" },
      { label: "Test wins", value: o.tests.won, sub: `${o.tests.lost} losses · 1 tie`, accent: "#22C55E" },
      { label: "ODIs", value: o.odis.played, sub: `${o.odis.won}W · ${o.odis.lost}L · ${o.odis.win_pct}%`, accent: "#00E5FF" },
      { label: "ODI wins", value: o.odis.won, sub: `${o.odis.tied} ties · ${o.odis.nr} NR`, accent: "#22C55E" },
      { label: "T20Is", value: o.t20is.played, sub: `${o.t20is.won}W · ${o.t20is.lost}L · ${o.t20is.win_pct}%`, accent: "#FF2D78" },
      { label: "T20I wins", value: o.t20is.won, sub: `+${o.t20is.tie_win || 0} super-over wins`, accent: "#22C55E" },
    ];
    $("#officialOverall").innerHTML = tiles
      .map(
        (t) => `
      <div class="stat-tile" style="--accent:${t.accent}">
        <div class="label">${t.label}</div>
        <div class="value">${fmtNum(t.value)}</div>
        <div class="sub">${t.sub}</div>
      </div>`
      )
      .join("");

    $("#trophyList").innerHTML = OFFICIAL.icc_trophies
      .map(
        (t) => `
      <div class="trophy-row">
        <div class="trophy-count">${t.count}</div>
        <div>
          <div class="t-title">${t.title}</div>
          <div class="t-years">${t.years.length ? t.years.join(" · ") : "—"}</div>
          ${t.note ? `<div class="t-note">${t.note}</div>` : ""}
        </div>
      </div>`
      )
      .join("");

    $("#milestoneList").innerHTML = OFFICIAL.milestones
      .map(
        (m) => `
      <div class="milestone-row">
        <div class="m-label">${m.label}</div>
        <div>
          <div class="m-value">${m.value}</div>
          <div class="m-detail">${m.detail}</div>
        </div>
      </div>`
      )
      .join("");

    $("#iconGrid").innerHTML = OFFICIAL.all_time_icons
      .map(
        (p) => `
      <div class="icon-card">
        <div class="icon-card-top">
          ${playerAvatar(p.player, "lg")}
          <div>
            <h3>${p.player}</h3>
            <div class="tagline">${p.tagline}</div>
          </div>
        </div>
        <ul>${p.highlights.map((h) => `<li>${h}</li>`).join("")}</ul>
      </div>`
      )
      .join("");

    // Unique gallery from official + image map
    const galleryNames = new Map();
    OFFICIAL.all_time_icons.forEach((p) => galleryNames.set(p.player, true));
    ["test", "odi", "t20i"].forEach((fmt) => {
      (OFFICIAL[fmt]?.batting || []).forEach((p) => galleryNames.set(p.player, true));
      (OFFICIAL[fmt]?.bowling || []).forEach((p) => galleryNames.set(p.player, true));
    });
    $("#playersGallery").innerHTML = [...galleryNames.keys()]
      .map(
        (name) => `
      <div class="gallery-card">
        ${playerAvatar(name, "lg")}
        <div class="g-name">${name}</div>
      </div>`
      )
      .join("");

    $("#officialH2H tbody").innerHTML = OFFICIAL.h2h_tests_top
      .map(
        (r) => `<tr>
        <td class="player">${r.opponent}</td>
        <td class="mono">${r.played}</td>
        <td class="mono" style="color:#4ade80">${r.won}</td>
        <td class="mono" style="color:#fb7185">${r.lost}</td>
        <td class="mono">${r.draw}</td>
        <td class="mono">${r.tied}</td>
      </tr>`
      )
      .join("");

    $("#sourceList").innerHTML = OFFICIAL.meta.sources
      .map(
        (s) => `<li>
        <a href="${s.url}" target="_blank" rel="noopener">${s.name}</a>
        <span>${s.url}</span>
      </li>`
      )
      .join("");

    $$("#officialFormatTabs .seg-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        $$("#officialFormatTabs .seg-btn").forEach((x) => x.classList.remove("active"));
        btn.classList.add("active");
        officialFmt = btn.dataset.ofmt;
        renderOfficialFormatPanel();
      });
    });
  }

  renderOfficialFormatPanel();
}

function renderOfficialFormatPanel() {
  if (!OFFICIAL) return;
  const key = officialFmt;
  const block = OFFICIAL[key];
  if (!block) return;

  const labels = { test: "Test cricket", odi: "One-Day Internationals", t20i: "T20 Internationals" };
  const overallKey = { test: "tests", odi: "odis", t20i: "t20is" }[key];
  const ov = OFFICIAL.overall[overallKey];

  let landmarks = "";
  if (block.team) {
    const t = block.team;
    const items = [];
    if (t.highest_total) items.push({ label: "Highest total", score: t.highest_total.score, meta: `vs ${t.highest_total.vs} · ${t.highest_total.venue} · ${t.highest_total.date}` });
    if (t.lowest_total) items.push({ label: "Lowest total", score: t.lowest_total.score, meta: `vs ${t.lowest_total.vs} · ${t.lowest_total.venue} · ${t.lowest_total.date}` });
    if (t.highest_chase) items.push({ label: "Highest successful chase", score: t.highest_chase.score, meta: `vs ${t.highest_chase.vs} · ${t.highest_chase.venue} · ${t.highest_chase.date}` });
    if (t.highest_conceded) items.push({ label: "Highest conceded", score: t.highest_conceded.score, meta: `by ${t.highest_conceded.by} · ${t.highest_conceded.venue} · ${t.highest_conceded.date}` });
    if (t.highest_individual) items.push({ label: "Highest individual", score: `${t.highest_individual.score} (${t.highest_individual.player})`, meta: `vs ${t.highest_individual.vs} · ${t.highest_individual.venue} · ${t.highest_individual.date}` });
    if (t.note) items.push({ label: "Note", score: "—", meta: t.note });
    landmarks = items
      .map(
        (i) => `<div class="landmark">
        <div class="l-label">${i.label}</div>
        <div class="l-score">${i.score}</div>
        <div class="l-meta">${i.meta}</div>
      </div>`
      )
      .join("");
  }

  const batRows = (block.batting || [])
    .map(
      (p) => `<tr>
      <td class="mono">${p.rank}</td>
      <td>${playerCell(p.player)}</td>
      <td class="mono" style="color:var(--cyan);font-weight:600">${fmtNum(p.runs)}</td>
      <td class="mono">${p.mat}</td>
      <td class="mono">${p.avg ?? "—"}</td>
      <td class="mono">${p.hundreds != null ? p.hundreds : p.sr ?? "—"}</td>
      <td class="mono">${p.hs || "—"}</td>
    </tr>`
    )
    .join("");

  const bowlRows = (block.bowling || [])
    .map(
      (p) => `<tr>
      <td class="mono">${p.rank}</td>
      <td>${playerCell(p.player)}</td>
      <td class="mono" style="color:var(--magenta);font-weight:600">${fmtNum(p.wickets)}</td>
      <td class="mono">${p.mat}</td>
      <td class="mono">${p.avg ?? "—"}</td>
      <td class="mono">${p.bbi || "—"}</td>
      <td class="mono">${p.five != null ? p.five : p.econ ?? "—"}</td>
    </tr>`
    )
    .join("");

  const batExtra = key === "t20i" ? "SR" : "100s";
  const bowlExtra = key === "t20i" ? "Econ*" : "5W";

  $("#officialFormatPanel").innerHTML = `
    <div class="card mb-4" style="margin-bottom:1rem">
      <div class="card-head">
        <h2>${labels[key]}</h2>
        <span class="chip">As of ${ov.as_of}</span>
      </div>
      <div class="mini-stats" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:0.5rem">
        <div class="mini-row"><span class="k">Played</span><span class="v">${fmtNum(ov.played)}</span></div>
        <div class="mini-row"><span class="k">Won</span><span class="v" style="color:#4ade80">${fmtNum(ov.won)}</span></div>
        <div class="mini-row"><span class="k">Lost</span><span class="v" style="color:#fb7185">${fmtNum(ov.lost)}</span></div>
        ${ov.draw ? `<div class="mini-row"><span class="k">Drawn</span><span class="v">${fmtNum(ov.draw)}</span></div>` : ""}
        ${ov.tied != null ? `<div class="mini-row"><span class="k">Tied</span><span class="v">${fmtNum(ov.tied)}</span></div>` : ""}
        ${ov.nr ? `<div class="mini-row"><span class="k">No result</span><span class="v">${fmtNum(ov.nr)}</span></div>` : ""}
        <div class="mini-row"><span class="k">Win %</span><span class="v">${ov.win_pct}%</span></div>
      </div>
    </div>
    ${landmarks ? `<div class="landmark-grid" style="margin-bottom:1rem">${landmarks}</div>` : ""}
    <div class="grid-2">
      <div class="card">
        <div class="card-head"><h2>Most runs</h2><span class="chip">Career leaders</span></div>
        <div class="table-scroll">
          <table class="data-table">
            <thead><tr><th>#</th><th>Player</th><th>Runs</th><th>Mat</th><th>Avg</th><th>${batExtra}</th><th>HS</th></tr></thead>
            <tbody>${batRows}</tbody>
          </table>
        </div>
        <p class="footnote">Active players’ tallies may edge higher since the last full source refresh. Landmark team figures are fixed historical records.</p>
      </div>
      <div class="card">
        <div class="card-head"><h2>Most wickets</h2><span class="chip">Career leaders</span></div>
        <div class="table-scroll">
          <table class="data-table">
            <thead><tr><th>#</th><th>Player</th><th>Wkts</th><th>Mat</th><th>Avg</th><th>BBI</th><th>${bowlExtra}</th></tr></thead>
            <tbody>${bowlRows}</tbody>
          </table>
        </div>
        <p class="footnote">*T20I table shows economy where five-fors are rare. Cross-check ESPNcricinfo for live updates.</p>
      </div>
    </div>
  `;
}

/* ── Overview ── */
function renderOverview() {
  const o = DATA.overall;
  const f = DATA.by_format;
  const tiles = [
    { label: "Matches", value: o.played, sub: `${DATA.meta.date_range[0]} → ${DATA.meta.date_range[1]}`, accent: "#00E5FF" },
    { label: "Won", value: o.won, sub: `${o.win_pct}% win rate`, accent: "#22C55E" },
    { label: "Lost", value: o.lost, sub: `${fmtPct(Math.round((o.lost / o.played) * 1000) / 10)} of all`, accent: "#F43F5E" },
    { label: "Test W/L", value: `${f.Test?.won || 0}/${f.Test?.lost || 0}`, sub: `${f.Test?.played || 0} Tests · ${f.Test?.draw || 0} draws`, accent: "#4F8CFF" },
    { label: "ODI wins", value: f.ODI?.won || 0, sub: `${f.ODI?.played || 0} ODIs · ${f.ODI?.win_pct || 0}%`, accent: "#00E5FF" },
    { label: "T20I wins", value: f.T20?.won || 0, sub: `${f.T20?.played || 0} T20s · ${f.T20?.win_pct || 0}%`, accent: "#FF2D78" },
  ];

  $("#overviewStats").innerHTML = tiles
    .map(
      (t) => `
    <div class="stat-tile" style="--accent:${t.accent}">
      <div class="label">${t.label}</div>
      <div class="value">${typeof t.value === "number" ? fmtNum(t.value) : t.value}</div>
      <div class="sub">${t.sub}</div>
    </div>`
    )
    .join("");

  // Home / Away
  const ha = DATA.by_home_away;
  $("#homeAwayCards").innerHTML = ["home", "away"]
    .map((k) => {
      const s = ha[k] || { played: 0, won: 0, win_pct: 0 };
      return `<div class="mini-row"><span class="k">${k === "home" ? "Home" : "Away"}</span>
        <span class="v">${s.won}/${s.played} · ${s.win_pct}%</span></div>`;
    })
    .join("");

  // Toss
  const t = DATA.toss;
  const tossWinRate = t.won_toss ? Math.round((t.toss_and_win / t.won_toss) * 1000) / 10 : 0;
  $("#tossCards").innerHTML = `
    <div class="mini-row"><span class="k">Toss won</span><span class="v">${t.won_toss}</span></div>
    <div class="mini-row"><span class="k">Toss lost</span><span class="v">${t.lost_toss}</span></div>
    <div class="mini-row"><span class="k">Win after winning toss</span><span class="v">${t.toss_and_win} (${tossWinRate}%)</span></div>
  `;

  // Chase
  const bfWin = t.bat_first_matches ? Math.round((t.won_bat_first / t.bat_first_matches) * 1000) / 10 : 0;
  const chWin = t.chase_matches ? Math.round((t.won_chase / t.chase_matches) * 1000) / 10 : 0;
  $("#chaseCards").innerHTML = `
    <div class="mini-row"><span class="k">Bat first</span><span class="v">${t.won_bat_first}/${t.bat_first_matches} · ${bfWin}%</span></div>
    <div class="mini-row"><span class="k">Chasing</span><span class="v">${t.won_chase}/${t.chase_matches} · ${chWin}%</span></div>
  `;

  // Top batters / bowlers
  $("#topBatters").innerHTML = DATA.batting
    .slice(0, 8)
    .map(
      (p, i) => `
    <div class="rank-item">
      <span class="pos">${i + 1}</span>
      ${playerAvatar(p.name, "sm")}
      <div><div class="name">${p.name}</div><div class="meta">${p.matches} mat · avg ${p.avg ?? "—"} · SR ${p.sr}</div></div>
      <span class="num">${fmtNum(p.runs)}</span>
    </div>`
    )
    .join("");

  $("#topBowlers").innerHTML = DATA.bowling
    .slice(0, 8)
    .map(
      (p, i) => `
    <div class="rank-item">
      <span class="pos">${i + 1}</span>
      ${playerAvatar(p.name, "sm")}
      <div><div class="name">${p.name}</div><div class="meta">${p.matches} mat · avg ${p.avg ?? "—"} · ${p.best}</div></div>
      <span class="num magenta">${fmtNum(p.wickets)}</span>
    </div>`
    )
    .join("");

  // Recent matches
  const tbody = $("#recentTable tbody");
  tbody.innerHTML = DATA.matches
    .slice(0, 12)
    .map(
      (m) => `
    <tr>
      <td class="mono">${m.date}</td>
      <td><span class="badge badge-fmt">${m.format}</span></td>
      <td>${m.opponent}</td>
      <td><span class="badge ${RESULT_BADGE[m.result] || ""}">${resultLabel(m.result)}</span></td>
      <td class="mono">${m.margin || "—"}</td>
      <td>${m.venue || "—"}</td>
      <td>${(m.pom || []).join(", ") || "—"}</td>
    </tr>`
    )
    .join("");

  renderOverviewCharts();
}

function renderOverviewCharts() {
  chartDefaults();
  const f = DATA.by_format;

  destroyChart("formatResults");
  charts.formatResults = new Chart($("#chartFormatResults"), {
    type: "bar",
    data: {
      labels: ["Test", "ODI", "T20"],
      datasets: [
        { label: "Won", data: [f.Test.won, f.ODI.won, f.T20.won], backgroundColor: "#22C55E", borderRadius: 4 },
        { label: "Lost", data: [f.Test.lost, f.ODI.lost, f.T20.lost], backgroundColor: "#F43F5E", borderRadius: 4 },
        { label: "Draw / Tie / NR", data: [
          f.Test.draw + f.Test.tied + f.Test.nr,
          f.ODI.draw + f.ODI.tied + f.ODI.nr,
          f.T20.draw + f.T20.tied + f.T20.nr,
        ], backgroundColor: "#5C5C70", borderRadius: 4 },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: "bottom", labels: { boxWidth: 10, padding: 14 } } },
      scales: {
        x: { stacked: true, grid: { display: false } },
        y: { stacked: true, grid: { color: "rgba(30,30,42,0.9)" } },
      },
    },
  });

  destroyChart("yearly");
  const years = DATA.years.filter((y) => Number(y.year) >= 2002);
  charts.yearly = new Chart($("#chartYearly"), {
    type: "line",
    data: {
      labels: years.map((y) => y.year),
      datasets: [
        {
          label: "Win %",
          data: years.map((y) => y.win_pct),
          borderColor: "#00E5FF",
          backgroundColor: "rgba(0,229,255,0.12)",
          fill: true,
          tension: 0.3,
          pointRadius: 2,
          pointHoverRadius: 5,
          borderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { maxTicksLimit: 12 } },
        y: { min: 0, max: 100, grid: { color: "rgba(30,30,42,0.9)" }, ticks: { callback: (v) => v + "%" } },
      },
    },
  });
}

/* ── Formats ── */
let formatsRendered = false;
function renderFormats() {
  if (formatsRendered) return;
  formatsRendered = true;

  const accents = { Test: "#4F8CFF", ODI: "#00E5FF", T20: "#FF2D78" };
  const labels = { Test: "Test cricket", ODI: "One-Day Internationals", T20: "T20 Internationals" };

  $("#formatCards").innerHTML = ["Test", "ODI", "T20"]
    .map((fmt) => {
      const s = DATA.by_format[fmt];
      return `
      <div class="format-card" style="--accent:${accents[fmt]}">
        <h3>${labels[fmt]}</h3>
        <div class="played">${fmtNum(s.played)}</div>
        <div style="color:var(--text-muted);font-size:0.85rem">matches · <strong style="color:${accents[fmt]}">${s.win_pct}%</strong> win rate</div>
        <div class="rows">
          <div class="row"><span>Won</span><strong style="color:#4ade80">${s.won}</strong></div>
          <div class="row"><span>Lost</span><strong style="color:#fb7185">${s.lost}</strong></div>
          <div class="row"><span>Draw</span><strong>${s.draw}</strong></div>
          <div class="row"><span>Tied / NR</span><strong>${s.tied + s.nr}</strong></div>
        </div>
      </div>`;
    })
    .join("");

  chartDefaults();
  const years = DATA.years.filter((y) => Number(y.year) >= 2002);
  destroyChart("yearFormat");
  charts.yearFormat = new Chart($("#chartYearFormat"), {
    type: "bar",
    data: {
      labels: years.map((y) => y.year),
      datasets: ["Test", "ODI", "T20"].map((fmt) => ({
        label: fmt,
        data: years.map((y) => y.by_format[fmt]?.played || 0),
        backgroundColor: FMT_COLORS[fmt],
        borderRadius: 2,
        stack: "s",
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: "bottom", labels: { boxWidth: 10 } } },
      scales: {
        x: { stacked: true, grid: { display: false }, ticks: { maxTicksLimit: 12 } },
        y: { stacked: true, grid: { color: "rgba(30,30,42,0.9)" } },
      },
    },
  });

  destroyChart("formatPie");
  charts.formatPie = new Chart($("#chartFormatPie"), {
    type: "doughnut",
    data: {
      labels: ["Test wins", "ODI wins", "T20 wins"],
      datasets: [
        {
          data: [DATA.by_format.Test.won, DATA.by_format.ODI.won, DATA.by_format.T20.won],
          backgroundColor: ["#4F8CFF", "#00E5FF", "#FF2D78"],
          borderWidth: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "62%",
      plugins: {
        legend: { position: "bottom", labels: { boxWidth: 10, padding: 14 } },
      },
    },
  });
}

/* ── Batting ── */
function getBatRow(p, fmt) {
  if (fmt === "all") return p;
  const bf = p.by_format[fmt];
  if (!bf || !bf.innings) return null;
  return {
    name: p.name,
    matches: bf.matches,
    innings: bf.innings,
    runs: bf.runs,
    highest: bf.highest,
    avg: bf.avg,
    sr: bf.sr,
    fifties: bf.fifties,
    hundreds: bf.hundreds,
    fours: bf.fours,
    sixes: bf.sixes,
    not_outs: bf.not_outs,
    ducks: p.ducks, // ducks not split easily; show overall only for all
  };
}

function renderBatting() {
  const fmt = $("#batFormatSeg .seg-btn.active")?.dataset.fmt || "all";
  const q = ($("#batSearch").value || "").toLowerCase().trim();
  const sort = $("#batSort").value;

  let rows = DATA.batting
    .map((p) => getBatRow(p, fmt))
    .filter(Boolean)
    .filter((p) => !q || p.name.toLowerCase().includes(q));

  rows.sort((a, b) => {
    const av = a[sort] ?? -1;
    const bv = b[sort] ?? -1;
    // null averages go last for avg/sr
    if (sort === "avg" || sort === "sr") {
      if (av == null) return 1;
      if (bv == null) return -1;
    }
    return bv - av;
  });

  // min filter for rate stats
  if (sort === "avg" || sort === "sr") {
    rows = rows.filter((p) => p.innings >= 10 && p.runs >= 200);
  }

  const tbody = $("#battingTable tbody");
  tbody.innerHTML = rows
    .slice(0, 100)
    .map((p, i) => {
      return `<tr>
        <td class="mono">${i + 1}</td>
        <td>${playerCell(p.name)}</td>
        <td class="mono">${p.matches}</td>
        <td class="mono">${p.innings}</td>
        <td class="mono" style="color:var(--cyan);font-weight:600">${fmtNum(p.runs)}</td>
        <td class="mono">${p.highest}</td>
        <td class="mono">${p.avg ?? "—"}</td>
        <td class="mono">${p.sr ?? "—"}</td>
        <td class="mono">${p.fifties}</td>
        <td class="mono">${p.hundreds}</td>
        <td class="mono">${fmtNum(p.fours)}</td>
        <td class="mono">${fmtNum(p.sixes)}</td>
        <td class="mono">${p.not_outs}</td>
        <td class="mono">${fmt === "all" ? p.ducks : "—"}</td>
      </tr>`;
    })
    .join("");
}

/* ── Bowling ── */
function getBowlRow(p, fmt) {
  if (fmt === "all") return p;
  const bf = p.by_format[fmt];
  if (!bf || !bf.innings) return null;
  return {
    name: p.name,
    matches: bf.matches,
    innings: bf.innings,
    overs: bf.overs,
    runs: bf.runs,
    wickets: bf.wickets,
    best: bf.best,
    avg: bf.avg,
    econ: bf.econ,
    sr: bf.sr,
    four_w: bf.four_w,
    five_w: bf.five_w,
    maidens: bf.maidens,
  };
}

function renderBowling() {
  const fmt = $("#bowlFormatSeg .seg-btn.active")?.dataset.fmt || "all";
  const q = ($("#bowlSearch").value || "").toLowerCase().trim();
  const sort = $("#bowlSort").value;

  let rows = DATA.bowling
    .map((p) => getBowlRow(p, fmt))
    .filter(Boolean)
    .filter((p) => !q || p.name.toLowerCase().includes(q));

  rows.sort((a, b) => {
    const av = a[sort] ?? 9999;
    const bv = b[sort] ?? 9999;
    // lower is better for avg, econ, sr
    if (sort === "avg" || sort === "econ" || sort === "sr") {
      if (a[sort] == null) return 1;
      if (b[sort] == null) return -1;
      return av - bv;
    }
    return bv - av;
  });

  if (sort === "avg" || sort === "econ" || sort === "sr") {
    rows = rows.filter((p) => p.wickets >= 20);
  }

  $("#bowlingTable tbody").innerHTML = rows
    .slice(0, 100)
    .map(
      (p, i) => `<tr>
      <td class="mono">${i + 1}</td>
      <td>${playerCell(p.name)}</td>
      <td class="mono">${p.matches}</td>
      <td class="mono">${p.innings}</td>
      <td class="mono">${p.overs}</td>
      <td class="mono">${fmtNum(p.runs)}</td>
      <td class="mono" style="color:var(--magenta);font-weight:600">${fmtNum(p.wickets)}</td>
      <td class="mono">${p.best}</td>
      <td class="mono">${p.avg ?? "—"}</td>
      <td class="mono">${p.econ ?? "—"}</td>
      <td class="mono">${p.sr ?? "—"}</td>
      <td class="mono">${p.four_w}</td>
      <td class="mono">${p.five_w}</td>
      <td class="mono">${p.maidens}</td>
    </tr>`
    )
    .join("");
}

/* ── Fielding ── */
function renderFielding() {
  $("#fieldingTable tbody").innerHTML = DATA.fielding
    .slice(0, 80)
    .map(
      (p, i) => `<tr>
      <td class="mono">${i + 1}</td>
      <td>${playerCell(p.name)}</td>
      <td class="mono">${p.matches}</td>
      <td class="mono">${p.catches}</td>
      <td class="mono">${p.stumpings}</td>
      <td class="mono">${p.runouts}</td>
      <td class="mono" style="color:var(--lime);font-weight:600">${p.dismissals}</td>
    </tr>`
    )
    .join("");

  $("#pomList").innerHTML = DATA.pom
    .slice(0, 24)
    .map(
      (p, i) => `
    <div class="rank-item">
      <span class="pos">${i + 1}</span>
      ${playerAvatar(p.player, "sm")}
      <div><div class="name">${p.player}</div></div>
      <span class="num amber">${p.awards}</span>
    </div>`
    )
    .join("");
}

/* ── H2H ── */
let h2hChartDone = false;
function renderH2H() {
  const q = ($("#h2hSearch").value || "").toLowerCase().trim();
  const sort = $("#h2hSort").value;

  let rows = DATA.opponents.filter((o) => !q || o.opponent.toLowerCase().includes(q));
  rows = [...rows].sort((a, b) => b[sort] - a[sort]);

  $("#h2hTable tbody").innerHTML = rows
    .map((o) => {
      const fmtBits = Object.entries(o.by_format || {})
        .map(([k, v]) => `${k}: ${v.won || 0}/${v.played || 0}`)
        .join(" · ");
      return `<tr>
        <td class="player">${o.opponent}</td>
        <td class="mono">${o.played}</td>
        <td class="mono" style="color:#4ade80">${o.won}</td>
        <td class="mono" style="color:#fb7185">${o.lost}</td>
        <td class="mono">${o.draw}</td>
        <td class="mono">${o.tied}</td>
        <td class="mono">${o.nr}</td>
        <td class="mono" style="color:var(--cyan);font-weight:600">${o.win_pct}%</td>
        <td style="font-size:0.72rem;color:var(--text-muted);white-space:normal;min-width:160px">${fmtBits}</td>
      </tr>`;
    })
    .join("");

  if (!h2hChartDone) {
    h2hChartDone = true;
    chartDefaults();
    const top = DATA.opponents.filter((o) => o.played >= 10).sort((a, b) => b.win_pct - a.win_pct);
    destroyChart("h2h");
    charts.h2h = new Chart($("#chartH2H"), {
      type: "bar",
      data: {
        labels: top.map((o) => o.opponent),
        datasets: [
          {
            label: "Win %",
            data: top.map((o) => o.win_pct),
            backgroundColor: top.map((o) =>
              o.win_pct >= 60 ? "#22C55E" : o.win_pct >= 45 ? "#00E5FF" : "#F43F5E"
            ),
            borderRadius: 4,
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { min: 0, max: 100, grid: { color: "rgba(30,30,42,0.9)" }, ticks: { callback: (v) => v + "%" } },
          y: { grid: { display: false }, ticks: { font: { size: 11 } } },
        },
      },
    });
  }
}

/* ── Venues ── */
function renderVenues() {
  const q = ($("#venueSearch").value || "").toLowerCase().trim();
  const filter = $("#venueFilter").value;

  let rows = DATA.venues.filter((v) => {
    if (filter === "home" && !v.home) return false;
    if (filter === "away" && v.home) return false;
    if (q && !(`${v.venue} ${v.city}`.toLowerCase().includes(q))) return false;
    return true;
  });

  $("#venueTable tbody").innerHTML = rows
    .map((v) => {
      const dtn = (v.draw || 0) + (v.tied || 0) + (v.nr || 0);
      return `<tr>
        <td class="player" style="white-space:normal;min-width:180px">${v.venue}</td>
        <td>${v.city || "—"}</td>
        <td><span class="badge ${v.home ? "badge-home" : "badge-away"}">${v.home ? "Home" : "Away"}</span></td>
        <td class="mono">${v.played}</td>
        <td class="mono" style="color:#4ade80">${v.won}</td>
        <td class="mono" style="color:#fb7185">${v.lost}</td>
        <td class="mono">${dtn}</td>
        <td class="mono" style="color:var(--cyan);font-weight:600">${v.win_pct}%</td>
      </tr>`;
    })
    .join("");
}

/* ── Records ── */
function renderRecords() {
  const r = DATA.records;

  $("#highTotals tbody").innerHTML = r.highest_totals
    .slice(0, 25)
    .map(
      (t) => `<tr>
      <td class="mono" style="color:var(--cyan);font-weight:600">${t.runs}/${t.wickets} <span style="color:var(--text-dim)">(${t.overs})</span></td>
      <td><span class="badge badge-fmt">${t.format}</span></td>
      <td>${t.opponent}</td>
      <td class="mono">${t.date}</td>
      <td style="white-space:normal">${t.venue}</td>
    </tr>`
    )
    .join("");

  $("#lowTotals tbody").innerHTML = r.lowest_totals
    .slice(0, 20)
    .map(
      (t) => `<tr>
      <td class="mono" style="color:var(--magenta);font-weight:600">${t.runs}/${t.wickets}</td>
      <td><span class="badge badge-fmt">${t.format}</span></td>
      <td>${t.opponent}</td>
      <td class="mono">${t.date}</td>
      <td style="white-space:normal">${t.venue}</td>
    </tr>`
    )
    .join("");

  $("#highInd tbody").innerHTML = r.highest_individual
    .slice(0, 30)
    .map((t) => {
      const rs = t.not_out ? `${t.runs}*` : t.runs;
      return `<tr>
        <td>${playerCell(t.player)}</td>
        <td class="mono" style="color:var(--lime);font-weight:600">${rs} <span style="color:var(--text-dim)">(${t.balls})</span></td>
        <td class="mono">${t.balls}</td>
        <td><span class="badge badge-fmt">${t.format}</span></td>
        <td>${t.opponent}</td>
        <td class="mono">${t.date}</td>
      </tr>`;
    })
    .join("");

  $("#bestBowl tbody").innerHTML = r.best_bowling
    .slice(0, 30)
    .map(
      (t) => `<tr>
      <td>${playerCell(t.player)}</td>
      <td class="mono" style="color:var(--magenta);font-weight:600">${t.wickets}/${t.runs}</td>
      <td class="mono">${t.overs}</td>
      <td><span class="badge badge-fmt">${t.format}</span></td>
      <td>${t.opponent}</td>
      <td class="mono">${t.date}</td>
    </tr>`
    )
    .join("");

  $("#bigWinsR tbody").innerHTML = r.biggest_wins_runs
    .slice(0, 20)
    .map(
      (t) => `<tr>
      <td class="mono" style="color:#4ade80;font-weight:600">${t.margin} runs</td>
      <td><span class="badge badge-fmt">${t.format}</span></td>
      <td>${t.opponent}</td>
      <td class="mono">${t.date}</td>
      <td style="white-space:normal">${t.venue}</td>
    </tr>`
    )
    .join("");

  $("#bigWinsW tbody").innerHTML = r.biggest_wins_wickets
    .slice(0, 20)
    .map(
      (t) => `<tr>
      <td class="mono" style="color:#4ade80;font-weight:600">${t.margin} wkts</td>
      <td><span class="badge badge-fmt">${t.format}</span></td>
      <td>${t.opponent}</td>
      <td class="mono">${t.date}</td>
      <td style="white-space:normal">${t.venue}</td>
    </tr>`
    )
    .join("");
}

/* ── Matches ── */
function filteredMatches() {
  const q = ($("#matchSearch").value || "").toLowerCase().trim();
  const fmt = $("#matchFormat").value;
  const res = $("#matchResult").value;
  const home = $("#matchHome").value;

  return DATA.matches.filter((m) => {
    if (fmt !== "all" && m.format !== fmt) return false;
    if (res !== "all" && m.result !== res) return false;
    if (home === "home" && !m.home) return false;
    if (home === "away" && m.home) return false;
    if (q) {
      const hay = `${m.opponent} ${m.venue} ${m.city} ${m.event} ${(m.pom || []).join(" ")}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

function renderMatches() {
  const rows = filteredMatches();
  const totalPages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  if (matchPage >= totalPages) matchPage = totalPages - 1;
  if (matchPage < 0) matchPage = 0;

  const slice = rows.slice(matchPage * PAGE_SIZE, (matchPage + 1) * PAGE_SIZE);
  $("#matchCount").textContent = `${fmtNum(rows.length)} matches · page ${matchPage + 1} of ${totalPages}`;

  $("#matchesTable tbody").innerHTML = slice
    .map(
      (m) => `<tr>
      <td class="mono">${m.date}</td>
      <td><span class="badge badge-fmt">${m.format}</span></td>
      <td class="player">${m.opponent}</td>
      <td><span class="badge ${RESULT_BADGE[m.result] || ""}">${resultLabel(m.result)}</span></td>
      <td class="mono">${m.margin || "—"}</td>
      <td style="white-space:normal;min-width:140px">${m.venue || "—"}</td>
      <td style="white-space:normal;min-width:120px;color:var(--text-muted)">${m.event || "—"}${m.stage ? " · " + m.stage : ""}</td>
      <td>${(m.pom || []).join(", ") || "—"}</td>
    </tr>`
    )
    .join("");

  // pager
  const pager = $("#matchPager");
  let html = `<button ${matchPage === 0 ? "disabled" : ""} data-p="${matchPage - 1}">← Prev</button>`;
  html += `<span>${matchPage + 1} / ${totalPages}</span>`;
  html += `<button ${matchPage >= totalPages - 1 ? "disabled" : ""} data-p="${matchPage + 1}">Next →</button>`;
  pager.innerHTML = html;
  pager.querySelectorAll("button[data-p]").forEach((btn) => {
    btn.addEventListener("click", () => {
      matchPage = Number(btn.dataset.p);
      renderMatches();
    });
  });
}

/* ── Missing ── */
let missingRendered = false;
function renderMissing() {
  const m = DATA.missing;
  const cov = m.by_format_vs_official;

  $("#missingCoverage").innerHTML = ["Test", "ODI", "T20"]
    .map((fmt) => {
      const c = cov[fmt];
      const accent = FMT_COLORS[fmt];
      return `
      <div class="stat-tile" style="--accent:${accent}">
        <div class="label">${fmt} coverage</div>
        <div class="value">${c.coverage_pct}%</div>
        <div class="sub">${fmtNum(c.in_dataset)} of ~${fmtNum(c.official_approx)}</div>
      </div>`;
    })
    .join("") +
    `
    <div class="stat-tile" style="--accent:#FFB800">
      <div class="label">In folder</div>
      <div class="value">${fmtNum(m.summary.dataset_matches)}</div>
      <div class="sub">Cricsheet JSON files</div>
    </div>
    <div class="stat-tile" style="--accent:#F43F5E">
      <div class="label">Withheld (AFG policy)</div>
      <div class="value">${m.withheld.count}</div>
      <div class="sub">Not shipped in archive</div>
    </div>
    <div class="stat-tile" style="--accent:#8B8B9E">
      <div class="label">Est. career missing</div>
      <div class="value">${fmtNum(
        cov.Test.estimated_missing + cov.ODI.estimated_missing + cov.T20.estimated_missing
      )}</div>
      <div class="sub">vs official totals</div>
    </div>`;

  $("#missingBlocks").innerHTML = `
    <div class="missing-block">
      <h3>1. Historical pre-archive gap</h3>
      <p><strong>Tests:</strong> ${m.historical_gap.tests_before_dataset}<br/>
      <strong>ODIs:</strong> ${m.historical_gap.odis_before_dataset}<br/>
      <strong>T20Is:</strong> ${m.historical_gap.t20_coverage}</p>
    </div>
    <div class="missing-block">
      <h3>2. Afghanistan policy withholdings</h3>
      <p>${m.withheld.reason} Count: <strong>${m.withheld.count}</strong>. See <a href="${m.withheld.url}" target="_blank" rel="noopener">cricsheet.org/withheld-matches</a>. ${m.withheld.impact}</p>
    </div>
    <div class="missing-block">
      <h3>3. What this means for stats</h3>
      <p>Player and team numbers on this dashboard reflect <em>only</em> the ${m.summary.dataset_matches} matches present (from ${m.summary.date_range[0]} to ${m.summary.date_range[1]}). Career greats who peaked earlier (e.g. large parts of Gavaskar, Kapil, Tendulkar pre-2002) are under-counted or absent.</p>
    </div>
  `;

  $("#missingWindow").innerHTML = `
    <div class="mw-item"><label>Earliest match</label><strong>${m.summary.date_range[0]}</strong></div>
    <div class="mw-item"><label>Latest match</label><strong>${m.summary.date_range[1]}</strong></div>
    <div class="mw-item"><label>Archive note</label><strong style="font-size:0.85rem;line-height:1.4;color:var(--text-muted)">${m.summary.note}</strong></div>
  `;

  const notes = {
    Test: "Most missing Tests are 1932–2001 (pre ball-by-ball Cricsheet coverage for this pack).",
    ODI: "Large 1974–2002 gap; plus any AFG ODIs withheld under policy.",
    T20: "Near-complete; remaining gap is largely India vs Afghanistan T20Is and edge cases.",
  };

  $("#missingTable tbody").innerHTML = ["Test", "ODI", "T20"]
    .map((fmt) => {
      const c = cov[fmt];
      return `<tr>
        <td><span class="badge badge-fmt">${fmt}</span></td>
        <td class="mono">${fmtNum(c.in_dataset)}</td>
        <td class="mono">~${fmtNum(c.official_approx)}</td>
        <td class="mono" style="color:var(--amber);font-weight:600">~${fmtNum(c.estimated_missing)}</td>
        <td class="mono" style="color:var(--cyan)">${c.coverage_pct}%</td>
        <td style="white-space:normal;min-width:220px;color:var(--text-muted)">${notes[fmt]}</td>
      </tr>`;
    })
    .join("");

  if (!missingRendered) {
    missingRendered = true;
    chartDefaults();
    destroyChart("coverage");
    charts.coverage = new Chart($("#chartCoverage"), {
      type: "bar",
      data: {
        labels: ["Test", "ODI", "T20I"],
        datasets: [
          {
            label: "In dataset",
            data: [cov.Test.in_dataset, cov.ODI.in_dataset, cov.T20.in_dataset],
            backgroundColor: "#00E5FF",
            borderRadius: 4,
          },
          {
            label: "Estimated missing",
            data: [cov.Test.estimated_missing, cov.ODI.estimated_missing, cov.T20.estimated_missing],
            backgroundColor: "#FFB800",
            borderRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom", labels: { boxWidth: 10, padding: 14 } } },
        scales: {
          x: { stacked: true, grid: { display: false } },
          y: { stacked: true, grid: { color: "rgba(30,30,42,0.9)" } },
        },
      },
    });
  }
}

/* ── Events ── */
function bindEvents() {
  $$(".nav-item").forEach((btn) => {
    btn.addEventListener("click", () => showView(btn.dataset.view));
  });

  $("#menuToggle")?.addEventListener("click", openSidebar);
  $("#sidebarClose")?.addEventListener("click", closeSidebar);
  $("#sidebarBackdrop")?.addEventListener("click", closeSidebar);
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeSidebar();
  });

  // batting controls
  $$("#batFormatSeg .seg-btn").forEach((b) =>
    b.addEventListener("click", () => {
      $$("#batFormatSeg .seg-btn").forEach((x) => x.classList.remove("active"));
      b.classList.add("active");
      renderBatting();
    })
  );
  $("#batSearch")?.addEventListener("input", () => renderBatting());
  $("#batSort")?.addEventListener("change", () => renderBatting());

  // bowling
  $$("#bowlFormatSeg .seg-btn").forEach((b) =>
    b.addEventListener("click", () => {
      $$("#bowlFormatSeg .seg-btn").forEach((x) => x.classList.remove("active"));
      b.classList.add("active");
      renderBowling();
    })
  );
  $("#bowlSearch")?.addEventListener("input", () => renderBowling());
  $("#bowlSort")?.addEventListener("change", () => renderBowling());

  // h2h
  $("#h2hSearch")?.addEventListener("input", () => renderH2H());
  $("#h2hSort")?.addEventListener("change", () => renderH2H());

  // venues
  $("#venueSearch")?.addEventListener("input", () => renderVenues());
  $("#venueFilter")?.addEventListener("change", () => renderVenues());

  // matches
  ["matchSearch", "matchFormat", "matchResult", "matchHome"].forEach((id) => {
    const el = $("#" + id);
    if (!el) return;
    el.addEventListener(id === "matchSearch" ? "input" : "change", () => {
      matchPage = 0;
      renderMatches();
    });
  });
}

/* ── Boot ── */
async function init() {
  try {
    const [statsRes, offRes, imgRes] = await Promise.all([
      fetch("stats.json"),
      fetch("official_records.json"),
      fetch("player_images.json"),
    ]);
    if (!statsRes.ok) throw new Error(`Failed to load stats.json (${statsRes.status})`);
    DATA = await statsRes.json();
    if (offRes.ok) {
      OFFICIAL = await offRes.json();
    } else {
      console.warn("official_records.json not loaded", offRes.status);
    }
    if (imgRes.ok) {
      const imgData = await imgRes.json();
      registerPlayerImages(imgData.players, imgData.meta?.base || "images/players/");
    } else {
      console.warn("player_images.json not loaded", imgRes.status);
    }

    $("#loading").classList.add("hidden");
    const metaLine = `${DATA.meta.matches} matches · ${DATA.meta.date_range[0]} – ${DATA.meta.date_range[1]}`;
    $("#headerMeta").textContent = metaLine;
    const mm = $("#mobileMeta");
    if (mm) mm.textContent = `${DATA.meta.matches} mat`;
    $("#footerMeta").textContent = `Generated ${DATA.meta.generated} · ${DATA.meta.matches} matches · Official page as of ${OFFICIAL?.meta?.as_of || "—"}`;

    bindEvents();
    renderOverview();
    // Default to Official Records so the verified page is front-and-centre
    showView("official");
  } catch (err) {
    $("#loading").innerHTML = `
      <p style="color:var(--magenta)">Failed to load data.</p>
      <p style="color:var(--text-muted);max-width:420px;text-align:center;margin-top:0.5rem">
        ${err.message}<br/><br/>
        Serve this folder over HTTP (browsers block local fetch). Example:<br/>
        <code style="font-family:var(--font-mono);color:var(--cyan)">cd dashboard && python3 -m http.server 8765</code>
      </p>`;
    console.error(err);
  }
}

init();
