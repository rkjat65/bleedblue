/* Team India Dashboard — full records SPA */

let DATA = null;
let OFFICIAL = null;
let PLAYER_IMGS = {}; // normalized name -> path
let MATCH_BY_ID = null;
const charts = {};
const PAGE_SIZE = 40;
let matchPage = 0;
let officialFmt = "test";
let officialRendered = false;
let overviewRendered = false;
let formatsRendered = false;
let h2hChartDone = false;
let missingRendered = false;
let routeParams = {};
let applyingHash = false;

const NAV_VIEWS = new Set([
  "official",
  "overview",
  "tournaments",
  "series",
  "search",
  "formats",
  "batting",
  "bowling",
  "fielding",
  "h2h",
  "venues",
  "records",
  "matches",
  "missing",
  "about",
]);

const DETAIL_VIEWS = new Set(["player", "match", "series-detail"]);

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

function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function escapeAttr(s) {
  return escapeHtml(s).replace(/'/g, "&#39;");
}

function playerAvatar(name, size = "md") {
  const src = playerImgSrc(name);
  const safe = escapeAttr(name);
  const initials = String(name || "?")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
  if (src) {
    return `<span class="avatar avatar-${size}" title="${safe}"><img src="${src}" alt="${safe}" loading="lazy" onerror="this.parentElement.classList.add('no-img');this.remove()" /></span>`;
  }
  return `<span class="avatar avatar-${size} avatar-fallback" title="${safe}">${initials || "?"}</span>`;
}

function playerCell(name) {
  const safe = escapeAttr(name);
  const label = escapeHtml(name);
  return `<button type="button" class="player-cell player-link" data-player="${safe}" title="Open ${safe}">${playerAvatar(name, "sm")}<span class="player">${label}</span></button>`;
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

function qualityBadge(q) {
  const map = {
    full: ["quality-full", "Full"],
    partial: ["quality-partial", "Partial"],
    empty: ["quality-empty", "Empty"],
  };
  const [cls, label] = map[q] || ["quality-empty", q || "—"];
  return `<span class="quality-badge ${cls}">${label}</span>`;
}

function oversFromBalls(balls) {
  if (balls == null || balls === "") return "—";
  const b = Number(balls);
  if (Number.isNaN(b)) return String(balls);
  return `${Math.floor(b / 6)}.${b % 6}`;
}

function formatInningsTotal(t) {
  if (!t) return "—";
  const wk = t.wickets != null ? `/${t.wickets}` : "";
  const ov = t.balls != null ? ` (${oversFromBalls(t.balls)} ov)` : "";
  return `${t.runs ?? "—"}${wk}${ov}`;
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

function buildMatchIndex() {
  MATCH_BY_ID = new Map();
  (DATA?.matches || []).forEach((m) => MATCH_BY_ID.set(String(m.id), m));
}

/* ── Fuzzy player lookup ── */
function nameScore(query, candidate) {
  const q = normalizePlayerName(query);
  const c = normalizePlayerName(candidate);
  if (!q || !c) return 0;
  if (q === c) return 100;
  if (c.startsWith(q) || q.startsWith(c)) return 90;
  if (c.includes(q) || q.includes(c)) return 75;
  const qp = q.split(" ").filter(Boolean);
  const cp = c.split(" ").filter(Boolean);
  if (!qp.length || !cp.length) return 0;
  const lastQ = qp[qp.length - 1];
  const lastC = cp[cp.length - 1];
  if (lastQ === lastC && lastQ.length > 2) {
    // initial match: "v kohli" vs "virat kohli"
    if (qp.length === 1) return 60;
    const firstQ = qp[0];
    if (cp[0].startsWith(firstQ) || firstQ.startsWith(cp[0][0])) return 85;
    return 55;
  }
  // token overlap
  const setC = new Set(cp);
  let hits = 0;
  qp.forEach((t) => {
    if (setC.has(t) || [...setC].some((x) => x.startsWith(t) || t.startsWith(x))) hits++;
  });
  if (hits === qp.length) return 70;
  if (hits > 0) return 40 + hits * 10;
  return 0;
}

function findBatting(name) {
  if (!DATA?.batting) return null;
  let best = null;
  let score = 0;
  for (const p of DATA.batting) {
    const s = nameScore(name, p.name);
    if (s > score) {
      score = s;
      best = p;
    }
  }
  return score >= 55 ? best : null;
}

function findBowling(name) {
  if (!DATA?.bowling) return null;
  let best = null;
  let score = 0;
  for (const p of DATA.bowling) {
    const s = nameScore(name, p.name);
    if (s > score) {
      score = s;
      best = p;
    }
  }
  return score >= 55 ? best : null;
}

function findFielding(name) {
  if (!DATA?.fielding) return null;
  let best = null;
  let score = 0;
  for (const p of DATA.fielding) {
    const s = nameScore(name, p.name);
    if (s > score) {
      score = s;
      best = p;
    }
  }
  return score >= 55 ? best : null;
}

function findPom(name) {
  if (!DATA?.pom) return null;
  let best = null;
  let score = 0;
  for (const p of DATA.pom) {
    const s = nameScore(name, p.player);
    if (s > score) {
      score = s;
      best = p;
    }
  }
  return score >= 55 ? best : null;
}

function resolveDisplayName(name) {
  const bat = findBatting(name);
  const bowl = findBowling(name);
  if (bat && bowl) {
    // prefer longer / more complete name
    return bat.matches >= (bowl.matches || 0) ? bat.name : bowl.name;
  }
  return bat?.name || bowl?.name || findFielding(name)?.name || findPom(name)?.player || name;
}

function namesMatch(a, b) {
  return nameScore(a, b) >= 55;
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

/* ── Hash routing ── */
function parseHash() {
  const raw = (location.hash || "").replace(/^#/, "").trim();
  if (!raw) return { view: "official", params: {} };
  const params = {};
  raw.split("&").forEach((part) => {
    const [k, ...rest] = part.split("=");
    if (!k) return;
    params[decodeURIComponent(k)] = decodeURIComponent(rest.join("=") || "");
  });
  const view = params.view || "official";
  delete params.view;
  return { view, params };
}

function buildHash(view, params = {}) {
  const parts = [`view=${encodeURIComponent(view)}`];
  Object.entries(params).forEach(([k, v]) => {
    if (v == null || v === "") return;
    parts.push(`${encodeURIComponent(k)}=${encodeURIComponent(v)}`);
  });
  return "#" + parts.join("&");
}

function setHash(view, params = {}) {
  const next = buildHash(view, params);
  if (location.hash === next) return;
  applyingHash = true;
  location.hash = next;
  // hashchange is sync in modern browsers; clear on next macrotask
  setTimeout(() => {
    applyingHash = false;
  }, 0);
}

function showView(name, params = {}, opts = {}) {
  const fromHash = !!opts.fromHash;
  routeParams = { ...(params || {}) };

  // Map series detail view name
  let section = name;
  if (name === "series" && routeParams.name) {
    section = "series-detail";
  }

  $$(".view").forEach((v) => v.classList.add("hidden"));
  const el = $(`#view-${section}`);
  if (el) {
    el.classList.remove("hidden");
  } else {
    // fallback
    $("#view-official")?.classList.remove("hidden");
    name = "official";
    section = "official";
  }

  // Highlight nav for detail views to closest parent
  let navName = name;
  if (name === "player") navName = "batting";
  if (name === "match") navName = "matches";
  if (name === "series-detail" || (name === "series" && routeParams.name)) navName = "series";
  $$(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.view === navName));

  closeSidebar();
  if (!opts.noScroll) window.scrollTo({ top: 0, behavior: "smooth" });

  if (!fromHash) {
    if (name === "series-detail") {
      setHash("series", routeParams);
    } else if (name === "series" && !routeParams.name) {
      setHash("series", {});
    } else if (DETAIL_VIEWS.has(name) || NAV_VIEWS.has(name)) {
      setHash(name, routeParams);
    }
  }

  // Render
  if (section === "official") renderOfficial();
  if (section === "overview") renderOverview();
  if (section === "tournaments") renderTournaments();
  if (section === "series") renderSeriesList();
  if (section === "series-detail") renderSeriesDetail(routeParams.name);
  if (section === "match") renderMatchDetail(routeParams.id);
  if (section === "player") renderPlayerProfile(routeParams.name);
  if (section === "search") renderSearch(routeParams.q || "");
  if (section === "about") renderAbout();
  if (section === "formats") renderFormats();
  if (section === "batting") renderBatting();
  if (section === "bowling") renderBowling();
  if (section === "fielding") renderFielding();
  if (section === "h2h") renderH2H();
  if (section === "venues") renderVenues();
  if (section === "records") renderRecords();
  if (section === "matches") renderMatches();
  if (section === "missing") renderMissing();
}

function applyRouteFromHash() {
  const { view, params } = parseHash();
  let name = view;
  if (view === "series" && params.name) {
    name = "series-detail";
  }
  showView(name, params, { fromHash: true });
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

    $("#trophyList").innerHTML = (OFFICIAL.icc_trophies || [])
      .map(
        (t) => `
      <div class="trophy-row">
        <div class="trophy-count">${t.count}</div>
        <div>
          <div class="t-title">${escapeHtml(t.title)}</div>
          <div class="t-years">${t.years?.length ? t.years.join(" · ") : "—"}</div>
          ${t.note ? `<div class="t-note">${escapeHtml(t.note)}</div>` : ""}
        </div>
      </div>`
      )
      .join("");

    $("#milestoneList").innerHTML = (OFFICIAL.milestones || [])
      .map(
        (m) => `
      <div class="milestone-row">
        <div class="m-label">${escapeHtml(m.label)}</div>
        <div>
          <div class="m-value">${escapeHtml(m.value)}</div>
          <div class="m-detail">${escapeHtml(m.detail)}</div>
        </div>
      </div>`
      )
      .join("");

    // Captaincy
    const capEl = $("#captaincyGrid");
    if (capEl) {
      capEl.innerHTML = (OFFICIAL.captaincy || [])
        .map(
          (c) => `
        <div class="captain-card">
          ${playerAvatar(c.player, "lg")}
          <div class="captain-body">
            <h3><button type="button" class="player-link text-link" data-player="${escapeAttr(c.player)}">${escapeHtml(c.player)}</button></h3>
            <div class="tagline">${escapeHtml(c.formats || "")}</div>
            <p class="captain-note">${escapeHtml(c.note || "")}</p>
            ${c.highlight ? `<div class="captain-hl">${escapeHtml(c.highlight)}</div>` : ""}
          </div>
        </div>`
        )
        .join("");
    }

    // Fielding / keeping
    const fk = OFFICIAL.fielding_keeping;
    if (fk) {
      if ($("#fieldingKeepingNote")) $("#fieldingKeepingNote").textContent = fk.notes || "Landmark keepers and fielders";
      const grid = $("#fieldingKeepingGrid");
      if (grid) {
        grid.innerHTML = `
          <div class="card">
            <div class="card-head"><h2>Keepers</h2></div>
            <div class="fk-list">
              ${(fk.keepers || [])
                .map(
                  (p) => `
                <div class="fk-row">
                  ${playerAvatar(p.player, "md")}
                  <div>
                    <button type="button" class="player-link text-link" data-player="${escapeAttr(p.player)}"><strong>${escapeHtml(p.player)}</strong></button>
                    <span class="chip chip-sm">${escapeHtml(p.role || "WK")}</span>
                    <p>${escapeHtml(p.highlight || "")}</p>
                  </div>
                </div>`
                )
                .join("")}
            </div>
          </div>
          <div class="card">
            <div class="card-head"><h2>Fielders</h2></div>
            <div class="fk-list">
              ${(fk.fielders || [])
                .map(
                  (p) => `
                <div class="fk-row">
                  ${playerAvatar(p.player, "md")}
                  <div>
                    <button type="button" class="player-link text-link" data-player="${escapeAttr(p.player)}"><strong>${escapeHtml(p.player)}</strong></button>
                    <span class="chip chip-sm">${escapeHtml(p.role || "")}</span>
                    <p>${escapeHtml(p.highlight || "")}</p>
                  </div>
                </div>`
                )
                .join("")}
            </div>
          </div>`;
      }
    }

    $("#iconGrid").innerHTML = (OFFICIAL.all_time_icons || [])
      .map(
        (p) => `
      <div class="icon-card">
        <div class="icon-card-top">
          ${playerAvatar(p.player, "lg")}
          <div>
            <h3><button type="button" class="player-link text-link" data-player="${escapeAttr(p.player)}">${escapeHtml(p.player)}</button></h3>
            <div class="tagline">${escapeHtml(p.tagline || "")}</div>
          </div>
        </div>
        <ul>${(p.highlights || []).map((h) => `<li>${escapeHtml(h)}</li>`).join("")}</ul>
      </div>`
      )
      .join("");

    const galleryNames = new Map();
    (OFFICIAL.all_time_icons || []).forEach((p) => galleryNames.set(p.player, true));
    (OFFICIAL.captaincy || []).forEach((p) => galleryNames.set(p.player, true));
    ["test", "odi", "t20i"].forEach((fmt) => {
      (OFFICIAL[fmt]?.batting || []).forEach((p) => galleryNames.set(p.player, true));
      (OFFICIAL[fmt]?.bowling || []).forEach((p) => galleryNames.set(p.player, true));
    });
    $("#playersGallery").innerHTML = [...galleryNames.keys()]
      .map(
        (name) => `
      <button type="button" class="gallery-card player-link" data-player="${escapeAttr(name)}">
        ${playerAvatar(name, "lg")}
        <div class="g-name">${escapeHtml(name)}</div>
      </button>`
      )
      .join("");

    $("#officialH2H tbody").innerHTML = (OFFICIAL.h2h_tests_top || [])
      .map(
        (r) => `<tr>
        <td class="player">${escapeHtml(r.opponent)}</td>
        <td class="mono">${r.played}</td>
        <td class="mono" style="color:#4ade80">${r.won}</td>
        <td class="mono" style="color:#fb7185">${r.lost}</td>
        <td class="mono">${r.draw}</td>
        <td class="mono">${r.tied}</td>
      </tr>`
      )
      .join("");

    $("#sourceList").innerHTML = (OFFICIAL.meta.sources || [])
      .map(
        (s) => `<li>
        <a href="${escapeAttr(s.url)}" target="_blank" rel="noopener">${escapeHtml(s.name)}</a>
        <span>${escapeHtml(s.url)}</span>
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
    if (t.highest_individual) {
      items.push({
        label: "Highest individual",
        score: `${t.highest_individual.score} (${t.highest_individual.player})`,
        meta: `vs ${t.highest_individual.vs} · ${t.highest_individual.venue} · ${t.highest_individual.date}`,
        player: t.highest_individual.player,
      });
    }
    if (t.note) items.push({ label: "Note", score: "—", meta: t.note });
    landmarks = items
      .map(
        (i) => `<div class="landmark">
        <div class="l-label">${escapeHtml(i.label)}</div>
        <div class="l-score">${i.player ? playerCell(i.player) + " · " + escapeHtml(String(i.score).replace(i.player, "").replace(/[()]/g, "").trim() || i.score) : escapeHtml(i.score)}</div>
        <div class="l-meta">${escapeHtml(i.meta)}</div>
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

/* ── Tournaments ── */
function renderTournaments() {
  const list = OFFICIAL?.tournaments || [];
  const root = $("#tournamentGrid");
  if (!root) return;
  if (!list.length) {
    root.innerHTML = `<div class="card"><p class="footnote">No tournament data loaded.</p></div>`;
    return;
  }
  root.innerHTML = list
    .map((t) => {
      const years = (t.title_years || []).join(" · ") || "—";
      const highlights = (t.highlights || [])
        .map(
          (h) => `
        <div class="tour-hl">
          <span class="tour-year mono">${escapeHtml(h.year)}</span>
          <div>
            <strong>${escapeHtml(h.result)}</strong>
            <p>${escapeHtml(h.detail || "")}</p>
          </div>
        </div>`
        )
        .join("");
      return `
      <article class="tournament-card" data-id="${escapeAttr(t.id)}">
        <div class="tournament-top">
          <div class="tour-titles">${t.titles ?? 0}</div>
          <div>
            <h2>${escapeHtml(t.name)}</h2>
            <div class="tour-best">${escapeHtml(t.best || "")}</div>
            <div class="tour-years">Titles: ${escapeHtml(years)}</div>
          </div>
        </div>
        ${t.notes ? `<p class="tour-notes">${escapeHtml(t.notes)}</p>` : ""}
        <div class="tour-highlights">${highlights}</div>
      </article>`;
    })
    .join("");
}

/* ── Series list ── */
function renderSeriesList() {
  if (!DATA?.events) return;
  const q = ($("#seriesSearch")?.value || "").toLowerCase().trim();
  const sort = $("#seriesSort")?.value || "played";

  let rows = [...DATA.events];
  if (q) rows = rows.filter((e) => e.name.toLowerCase().includes(q));

  rows.sort((a, b) => {
    if (sort === "name") return a.name.localeCompare(b.name);
    if (sort === "last") return String(b.last || "").localeCompare(String(a.last || ""));
    return (b[sort] ?? 0) - (a[sort] ?? 0);
  });

  $("#seriesTable tbody").innerHTML = rows
    .map((e) => {
      const dtn = (e.draw || 0) + (e.tied || 0) + (e.nr || 0);
      return `<tr class="clickable-row" data-series="${escapeAttr(e.name)}">
        <td class="player" style="white-space:normal;min-width:200px">${escapeHtml(e.name)}</td>
        <td class="mono">${e.played}</td>
        <td class="mono" style="color:#4ade80">${e.won}</td>
        <td class="mono" style="color:#fb7185">${e.lost}</td>
        <td class="mono">${dtn}</td>
        <td class="mono" style="color:var(--cyan);font-weight:600">${e.win_pct}%</td>
        <td style="font-size:0.75rem;color:var(--text-muted)">${(e.formats || []).join(" · ")}</td>
        <td class="mono">${e.first || "—"}</td>
        <td class="mono">${e.last || "—"}</td>
      </tr>`;
    })
    .join("");
}

function renderSeriesDetail(name) {
  const root = $("#seriesDetailRoot");
  if (!root) return;
  if (!name || !DATA?.events) {
    root.innerHTML = `<div class="card"><p>Series not found.</p><button type="button" class="link-btn" onclick="showView('series')">← Back to series</button></div>`;
    return;
  }
  const ev = DATA.events.find((e) => e.name === name) || DATA.events.find((e) => e.name.toLowerCase() === name.toLowerCase());
  if (!ev) {
    root.innerHTML = `<div class="card"><p>Series “${escapeHtml(name)}” not found.</p><button type="button" class="link-btn" onclick="showView('series')">← Back</button></div>`;
    return;
  }

  const matches = (ev.match_ids || [])
    .map((id) => MATCH_BY_ID?.get(String(id)))
    .filter(Boolean)
    .sort((a, b) => String(b.date).localeCompare(String(a.date)));

  const dtn = (ev.draw || 0) + (ev.tied || 0) + (ev.nr || 0);

  root.innerHTML = `
    <div class="detail-back">
      <button type="button" class="link-btn" onclick="showView('series')">← All series</button>
    </div>
    <div class="section-head">
      <h1>${escapeHtml(ev.name)}</h1>
      <p>${fmtNum(ev.played)} matches · ${escapeHtml((ev.formats || []).join(" · "))} · ${ev.first || "?"} → ${ev.last || "?"}</p>
    </div>
    <div class="stat-grid stagger">
      <div class="stat-tile" style="--accent:#00E5FF"><div class="label">Played</div><div class="value">${fmtNum(ev.played)}</div></div>
      <div class="stat-tile" style="--accent:#22C55E"><div class="label">Won</div><div class="value">${fmtNum(ev.won)}</div><div class="sub">${ev.win_pct}% win rate</div></div>
      <div class="stat-tile" style="--accent:#F43F5E"><div class="label">Lost</div><div class="value">${fmtNum(ev.lost)}</div></div>
      <div class="stat-tile" style="--accent:#8B8B9E"><div class="label">Draw / T / NR</div><div class="value">${dtn}</div></div>
    </div>
    <div class="card mt-6">
      <div class="card-head"><h2>Matches</h2><span class="chip">${matches.length} listed</span></div>
      <div class="table-scroll">
        <table class="data-table">
          <thead><tr><th>Date</th><th>Fmt</th><th>Opponent</th><th>Result</th><th>Margin</th><th>Venue</th><th>PoM</th><th>Quality</th></tr></thead>
          <tbody>
            ${matches
              .map(
                (m) => `<tr class="clickable-row" data-match="${escapeAttr(m.id)}">
              <td class="mono match-link">${m.date}</td>
              <td><span class="badge badge-fmt">${m.format}</span></td>
              <td class="player match-link">${escapeHtml(m.opponent)}</td>
              <td><span class="badge ${RESULT_BADGE[m.result] || ""}">${resultLabel(m.result)}</span></td>
              <td class="mono">${escapeHtml(m.margin || "—")}</td>
              <td style="white-space:normal">${escapeHtml(m.venue || "—")}</td>
              <td>${(m.pom || []).map((p) => escapeHtml(p)).join(", ") || "—"}</td>
              <td>${qualityBadge(m.quality)}</td>
            </tr>`
              )
              .join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

/* ── Match detail ── */
function renderMatchDetail(id) {
  const root = $("#matchDetailRoot");
  if (!root) return;
  const m = MATCH_BY_ID?.get(String(id)) || DATA?.matches?.find((x) => String(x.id) === String(id));
  if (!m) {
    root.innerHTML = `<div class="card"><p>Match not found.</p><button type="button" class="link-btn" onclick="showView('matches')">← Match browser</button></div>`;
    return;
  }

  const batRows = (m.bat_card || [])
    .map((b) => {
      const rs = b.out === false ? `${b.runs}*` : b.runs;
      const sr = b.balls ? Math.round((b.runs / b.balls) * 1000) / 10 : "—";
      return `<tr>
        <td>${playerCell(b.player)}</td>
        <td class="mono" style="color:var(--cyan);font-weight:600">${rs}</td>
        <td class="mono">${b.balls ?? "—"}</td>
        <td class="mono">${b.fours ?? "—"}</td>
        <td class="mono">${b.sixes ?? "—"}</td>
        <td class="mono">${sr}</td>
        <td class="mono">${b.innings ?? "—"}</td>
      </tr>`;
    })
    .join("");

  const bowlRows = (m.bowl_card || [])
    .map((b) => {
      const econ = b.balls ? Math.round((b.runs / (b.balls / 6)) * 100) / 100 : "—";
      return `<tr>
        <td>${playerCell(b.player)}</td>
        <td class="mono">${oversFromBalls(b.balls)}</td>
        <td class="mono">${b.maidens ?? 0}</td>
        <td class="mono">${b.runs ?? "—"}</td>
        <td class="mono" style="color:var(--magenta);font-weight:600">${b.wickets ?? 0}</td>
        <td class="mono">${econ}</td>
        <td class="mono">${b.innings ?? "—"}</td>
      </tr>`;
    })
    .join("");

  const xi = (m.xi || [])
    .map((p) => `<li class="xi-item">${playerCell(p)}</li>`)
    .join("");

  const indiaTotals = (m.india_totals || [])
    .map((t, i) => `<div class="total-pill">Inn ${t.innings ?? i + 1}: <strong>${formatInningsTotal(t)}</strong></div>`)
    .join("") || `<div class="total-pill muted">No India totals</div>`;

  const oppTotals = (m.opp_totals || [])
    .map((t, i) => `<div class="total-pill">Inn ${t.innings ?? i + 1}: <strong>${formatInningsTotal(t)}</strong></div>`)
    .join("") || `<div class="total-pill muted">No opposition totals</div>`;

  const eventLink = m.event
    ? `<button type="button" class="inline-link" onclick="showView('series-detail',{name:${JSON.stringify(m.event)}})">${escapeHtml(m.event)}</button>`
    : "—";

  root.innerHTML = `
    <div class="detail-back">
      <button type="button" class="link-btn" onclick="showView('matches')">← Match browser</button>
      ${m.event ? `<button type="button" class="link-btn" onclick="showView('series-detail',{name:${JSON.stringify(m.event)}})">Series →</button>` : ""}
    </div>
    <div class="match-header">
      <div class="match-header-main">
        <div class="match-meta-row">
          <span class="badge badge-fmt">${escapeHtml(m.format)}</span>
          ${qualityBadge(m.quality)}
          <span class="mono text-muted">${escapeHtml(m.date)}</span>
          <span class="badge ${m.home ? "badge-home" : "badge-away"}">${m.home ? "Home" : "Away"}</span>
        </div>
        <h1>India vs ${escapeHtml(m.opponent)}</h1>
        <p class="match-sub">${escapeHtml(m.venue || "")}${m.city ? " · " + escapeHtml(m.city) : ""}</p>
        <p class="match-event">${eventLink}${m.stage ? " · " + escapeHtml(m.stage) : ""}</p>
      </div>
      <div class="match-result-panel">
        <span class="badge ${RESULT_BADGE[m.result] || ""} result-lg">${resultLabel(m.result)}</span>
        <div class="margin mono">${escapeHtml(m.margin || (m.winner ? `Winner: ${m.winner}` : "—"))}</div>
        <div class="toss-line">Toss: ${escapeHtml(m.toss || "—")}</div>
        ${(m.pom || []).length ? `<div class="pom-line">PoM: ${(m.pom || []).map((p) => playerCell(p)).join(" ")}</div>` : ""}
      </div>
    </div>

    <div class="grid-2 mt-6">
      <div class="card">
        <div class="card-head"><h2>India totals</h2></div>
        <div class="totals-row">${indiaTotals}</div>
      </div>
      <div class="card">
        <div class="card-head"><h2>${escapeHtml(m.opponent)} totals</h2></div>
        <div class="totals-row">${oppTotals}</div>
      </div>
    </div>

    <div class="grid-2 mt-6">
      <div class="card">
        <div class="card-head"><h2>India XI</h2><span class="chip">${(m.xi || []).length} players</span></div>
        <ul class="xi-list">${xi || "<li class='text-muted'>—</li>"}</ul>
      </div>
      <div class="card">
        <div class="card-head"><h2>Match info</h2></div>
        <div class="mini-stats">
          <div class="mini-row"><span class="k">Match ID</span><span class="v mono">${escapeHtml(m.id)}</span></div>
          <div class="mini-row"><span class="k">Season</span><span class="v">${escapeHtml(m.season || "—")}</span></div>
          <div class="mini-row"><span class="k">Balls in file</span><span class="v mono">${fmtNum(m.balls)}</span></div>
          <div class="mini-row"><span class="k">Quality</span><span class="v">${qualityBadge(m.quality)}</span></div>
          <div class="mini-row"><span class="k">Match type #</span><span class="v mono">${m.match_type_number ?? "—"}</span></div>
        </div>
      </div>
    </div>

    <div class="grid-2 mt-6">
      <div class="card">
        <div class="card-head"><h2>Batting card</h2><span class="chip">India</span></div>
        ${
          batRows
            ? `<div class="table-scroll"><table class="data-table">
          <thead><tr><th>Batter</th><th>R</th><th>B</th><th>4s</th><th>6s</th><th>SR</th><th>Inn</th></tr></thead>
          <tbody>${batRows}</tbody>
        </table></div>`
            : `<p class="empty-card">No batting card (quality: ${escapeHtml(m.quality || "unknown")})</p>`
        }
      </div>
      <div class="card">
        <div class="card-head"><h2>Bowling card</h2><span class="chip">India</span></div>
        ${
          bowlRows
            ? `<div class="table-scroll"><table class="data-table">
          <thead><tr><th>Bowler</th><th>O</th><th>M</th><th>R</th><th>W</th><th>Econ</th><th>Inn</th></tr></thead>
          <tbody>${bowlRows}</tbody>
        </table></div>`
            : `<p class="empty-card">No bowling card (quality: ${escapeHtml(m.quality || "unknown")})</p>`
        }
      </div>
    </div>
  `;
}

/* ── Player profile ── */
function renderPlayerProfile(name) {
  const root = $("#playerDetailRoot");
  if (!root) return;
  if (!name) {
    root.innerHTML = `<div class="card"><p>No player specified.</p></div>`;
    return;
  }

  const display = resolveDisplayName(name);
  const bat = findBatting(name) || findBatting(display);
  const bowl = findBowling(name) || findBowling(display);
  const fld = findFielding(name) || findFielding(display);
  const pom = findPom(name) || findPom(display);

  if (!bat && !bowl && !fld && !pom) {
    root.innerHTML = `
      <div class="detail-back"><button type="button" class="link-btn" onclick="history.back()">← Back</button></div>
      <div class="card"><p>No archive stats found for “${escapeHtml(name)}”.</p>
      <p class="footnote">Official career leaders may pre-date ball-by-ball coverage. Try <button type="button" class="inline-link" onclick="showView('search',{q:${JSON.stringify(name)}})">Search</button>.</p></div>`;
    return;
  }

  const matchName = display;
  const matches = (DATA.matches || [])
    .filter((m) => {
      const inXi = (m.xi || []).some((p) => namesMatch(p, matchName) || namesMatch(p, name));
      const inPom = (m.pom || []).some((p) => namesMatch(p, matchName) || namesMatch(p, name));
      return inXi || inPom;
    })
    .slice(0, 40);

  const fmtRows = (obj, keys) => {
    if (!obj?.by_format) return "";
    return ["Test", "ODI", "T20"]
      .filter((f) => obj.by_format[f])
      .map((f) => {
        const s = obj.by_format[f];
        return `<tr>
          <td><span class="badge badge-fmt">${f}</span></td>
          ${keys.map((k) => `<td class="mono">${s[k] ?? "—"}</td>`).join("")}
        </tr>`;
      })
      .join("");
  };

  root.innerHTML = `
    <div class="detail-back">
      <button type="button" class="link-btn" onclick="history.back()">← Back</button>
      <button type="button" class="link-btn" onclick="showView('batting')">Batting</button>
      <button type="button" class="link-btn" onclick="showView('bowling')">Bowling</button>
    </div>
    <div class="player-hero">
      ${playerAvatar(display, "xl")}
      <div class="player-hero-text">
        <h1>${escapeHtml(display)}</h1>
        <p class="hero-sub">Archive profile · figures from ball-by-ball matches in this dataset only</p>
        <div class="player-badges">
          ${pom ? `<span class="chip">PoM × ${pom.awards}</span>` : ""}
          ${bat ? `<span class="chip">${fmtNum(bat.runs)} runs</span>` : ""}
          ${bowl ? `<span class="chip">${fmtNum(bowl.wickets)} wickets</span>` : ""}
          ${fld ? `<span class="chip">${fld.dismissals} dismissals</span>` : ""}
        </div>
      </div>
    </div>

    <div class="grid-2 mt-6">
      ${
        bat
          ? `<div class="card">
        <div class="card-head"><h2>Batting</h2><span class="chip">${bat.matches} matches</span></div>
        <div class="stat-grid player-stats">
          <div class="stat-tile" style="--accent:#00E5FF"><div class="label">Runs</div><div class="value">${fmtNum(bat.runs)}</div></div>
          <div class="stat-tile" style="--accent:#4F8CFF"><div class="label">Average</div><div class="value">${bat.avg ?? "—"}</div></div>
          <div class="stat-tile" style="--accent:#B8FF00"><div class="label">SR</div><div class="value">${bat.sr ?? "—"}</div></div>
          <div class="stat-tile" style="--accent:#FFB800"><div class="label">HS</div><div class="value">${bat.highest ?? "—"}</div></div>
          <div class="stat-tile" style="--accent:#FF2D78"><div class="label">100s / 50s</div><div class="value">${bat.hundreds ?? 0} / ${bat.fifties ?? 0}</div></div>
          <div class="stat-tile" style="--accent:#8B8B9E"><div class="label">4s / 6s</div><div class="value">${fmtNum(bat.fours)} / ${fmtNum(bat.sixes)}</div></div>
        </div>
        <div class="table-scroll mt-4">
          <table class="data-table">
            <thead><tr><th>Format</th><th>Mat</th><th>Inn</th><th>Runs</th><th>Avg</th><th>SR</th><th>100s</th><th>50s</th><th>HS</th></tr></thead>
            <tbody>${fmtRows(bat, ["matches", "innings", "runs", "avg", "sr", "hundreds", "fifties", "highest"])}</tbody>
          </table>
        </div>
      </div>`
          : `<div class="card"><div class="card-head"><h2>Batting</h2></div><p class="empty-card">No batting innings in archive</p></div>`
      }

      ${
        bowl
          ? `<div class="card">
        <div class="card-head"><h2>Bowling</h2><span class="chip">${bowl.matches} matches</span></div>
        <div class="stat-grid player-stats">
          <div class="stat-tile" style="--accent:#FF2D78"><div class="label">Wickets</div><div class="value">${fmtNum(bowl.wickets)}</div></div>
          <div class="stat-tile" style="--accent:#00E5FF"><div class="label">Average</div><div class="value">${bowl.avg ?? "—"}</div></div>
          <div class="stat-tile" style="--accent:#FFB800"><div class="label">Econ</div><div class="value">${bowl.econ ?? "—"}</div></div>
          <div class="stat-tile" style="--accent:#4F8CFF"><div class="label">SR</div><div class="value">${bowl.sr ?? "—"}</div></div>
          <div class="stat-tile" style="--accent:#B8FF00"><div class="label">Best</div><div class="value">${bowl.best ?? "—"}</div></div>
          <div class="stat-tile" style="--accent:#8B8B9E"><div class="label">5W / 4W</div><div class="value">${bowl.five_w ?? 0} / ${bowl.four_w ?? 0}</div></div>
        </div>
        <div class="table-scroll mt-4">
          <table class="data-table">
            <thead><tr><th>Format</th><th>Mat</th><th>Inn</th><th>Wkts</th><th>Avg</th><th>Econ</th><th>SR</th><th>Best</th></tr></thead>
            <tbody>${fmtRows(bowl, ["matches", "innings", "wickets", "avg", "econ", "sr", "best"])}</tbody>
          </table>
        </div>
      </div>`
          : `<div class="card"><div class="card-head"><h2>Bowling</h2></div><p class="empty-card">No bowling innings in archive</p></div>`
      }
    </div>

    ${
      fld
        ? `<div class="card mt-6">
      <div class="card-head"><h2>Fielding</h2></div>
      <div class="mini-stats" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:0.5rem">
        <div class="mini-row"><span class="k">Matches</span><span class="v">${fld.matches}</span></div>
        <div class="mini-row"><span class="k">Catches</span><span class="v">${fld.catches}</span></div>
        <div class="mini-row"><span class="k">Stumpings</span><span class="v">${fld.stumpings}</span></div>
        <div class="mini-row"><span class="k">Run-outs</span><span class="v">${fld.runouts}</span></div>
        <div class="mini-row"><span class="k">Dismissals</span><span class="v" style="color:var(--lime)">${fld.dismissals}</span></div>
      </div>
    </div>`
        : ""
    }

    <div class="card mt-6">
      <div class="card-head"><h2>Matches in archive</h2><span class="chip">Up to 40 · XI or PoM</span></div>
      <div class="table-scroll">
        <table class="data-table">
          <thead><tr><th>Date</th><th>Fmt</th><th>Opponent</th><th>Result</th><th>Venue</th><th>PoM</th></tr></thead>
          <tbody>
            ${
              matches.length
                ? matches
                    .map(
                      (m) => `<tr class="clickable-row" data-match="${escapeAttr(m.id)}">
              <td class="mono match-link">${m.date}</td>
              <td><span class="badge badge-fmt">${m.format}</span></td>
              <td class="player match-link">${escapeHtml(m.opponent)}</td>
              <td><span class="badge ${RESULT_BADGE[m.result] || ""}">${resultLabel(m.result)}</span></td>
              <td style="white-space:normal">${escapeHtml(m.venue || "—")}</td>
              <td>${(m.pom || []).some((p) => namesMatch(p, matchName) || namesMatch(p, name)) ? "★" : "—"}</td>
            </tr>`
                    )
                    .join("")
                : `<tr><td colspan="6" class="text-muted">No XI/PoM matches found (name mapping may differ)</td></tr>`
            }
          </tbody>
        </table>
      </div>
    </div>
  `;
}

/* ── Global search ── */
function renderSearch(qInit) {
  const input = $("#globalSearch");
  if (input && qInit != null && input.value !== qInit) input.value = qInit;
  const q = (input?.value || qInit || "").trim();
  const root = $("#searchResults");
  if (!root) return;

  if (!q || q.length < 2) {
    root.innerHTML = `<div class="search-empty">Type at least 2 characters to search players, matches and series.</div>`;
    return;
  }

  const ql = q.toLowerCase();
  const players = [];
  const seen = new Set();
  const pushPlayer = (name, meta) => {
    const key = normalizePlayerName(name);
    if (seen.has(key)) return;
    if (!name.toLowerCase().includes(ql) && nameScore(q, name) < 55) return;
    seen.add(key);
    players.push({ name, meta });
  };

  (DATA.batting || []).forEach((p) => {
    if (p.name.toLowerCase().includes(ql) || nameScore(q, p.name) >= 70) {
      pushPlayer(p.name, `${fmtNum(p.runs)} runs · ${p.matches} mat`);
    }
  });
  (DATA.bowling || []).forEach((p) => {
    if (p.name.toLowerCase().includes(ql) || nameScore(q, p.name) >= 70) {
      pushPlayer(p.name, `${fmtNum(p.wickets)} wkts · ${p.matches} mat`);
    }
  });

  const matches = (DATA.matches || [])
    .filter((m) => {
      const hay = `${m.opponent} ${m.venue} ${m.city} ${m.event} ${m.date}`.toLowerCase();
      return hay.includes(ql);
    })
    .slice(0, 25);

  const series = (DATA.events || [])
    .filter((e) => e.name.toLowerCase().includes(ql))
    .slice(0, 15);

  root.innerHTML = `
    <div class="search-section">
      <h2>Players <span class="chip">${Math.min(players.length, 20)}</span></h2>
      <div class="search-list">
        ${
          players.length
            ? players
                .slice(0, 20)
                .map(
                  (p) => `
          <button type="button" class="search-item player-link" data-player="${escapeAttr(p.name)}">
            ${playerAvatar(p.name, "sm")}
            <div><strong>${escapeHtml(p.name)}</strong><div class="meta">${escapeHtml(p.meta)}</div></div>
          </button>`
                )
                .join("")
            : `<div class="search-empty">No players</div>`
        }
      </div>
    </div>
    <div class="search-section">
      <h2>Series <span class="chip">${series.length}</span></h2>
      <div class="search-list">
        ${
          series.length
            ? series
                .map(
                  (e) => `
          <button type="button" class="search-item" data-series="${escapeAttr(e.name)}">
            <div><strong>${escapeHtml(e.name)}</strong><div class="meta">${e.played} matches · ${e.win_pct}% · ${e.first} → ${e.last}</div></div>
          </button>`
                )
                .join("")
            : `<div class="search-empty">No series</div>`
        }
      </div>
    </div>
    <div class="search-section">
      <h2>Matches <span class="chip">${matches.length}</span></h2>
      <div class="search-list">
        ${
          matches.length
            ? matches
                .map(
                  (m) => `
          <button type="button" class="search-item" data-match="${escapeAttr(m.id)}">
            <div>
              <strong>${escapeHtml(m.date)} · vs ${escapeHtml(m.opponent)}</strong>
              <div class="meta">${escapeHtml(m.format)} · ${resultLabel(m.result)} · ${escapeHtml(m.venue || "")} · ${escapeHtml(m.event || "")}</div>
            </div>
            ${qualityBadge(m.quality)}
          </button>`
                )
                .join("")
            : `<div class="search-empty">No matches</div>`
        }
      </div>
    </div>
  `;
}

/* ── About ── */
function renderAbout() {
  const root = $("#aboutContent");
  if (!root) return;
  const gen = DATA?.meta?.generated || "—";
  const matches = DATA?.meta?.matches ?? "—";
  const range = DATA?.meta?.date_range || ["—", "—"];
  const asOf = OFFICIAL?.meta?.as_of || "—";
  const sources = (OFFICIAL?.meta?.sources || [])
    .map((s) => `<li><a href="${escapeAttr(s.url)}" target="_blank" rel="noopener">${escapeHtml(s.name)}</a></li>`)
    .join("");

  root.innerHTML = `
    <div class="card">
      <div class="card-head"><h2>What is this?</h2></div>
      <p class="about-p">A full-fledged <strong>Team India men’s international cricket records</strong> site hosted at <a href="https://cricket.rkjat.in" target="_blank" rel="noopener">cricket.rkjat.in</a>. It combines verified public career totals with a local Cricsheet-based archive for deep match and player analytics.</p>
    </div>
    <div class="card">
      <div class="card-head"><h2>Official vs archive</h2></div>
      <ul class="about-list">
        <li><strong>Official Records</strong> — career team/player landmarks compiled from Wikipedia / ESPNcricinfo / ICC public figures (as of ${escapeHtml(asOf)}). Use this for “all-time” truth.</li>
        <li><strong>Archive analytics</strong> — computed from ${fmtNum(matches)} match files in this dataset (${escapeHtml(range[0])} → ${escapeHtml(range[1])}). Player tables, match centre, series and coverage all use this source and can under-count pre-coverage careers.</li>
      </ul>
    </div>
    <div class="card">
      <div class="card-head"><h2>Methodology</h2></div>
      <ul class="about-list">
        <li>Match results, XI, bat/bowl cards and quality flags are derived from Cricsheet JSON and recovered India internationals.</li>
        <li><span class="quality-badge quality-full">Full</span> matches have ball-by-ball data; <span class="quality-badge quality-partial">Partial</span> have limited detail; <span class="quality-badge quality-empty">Empty</span> are shells without innings cards.</li>
        <li>Afghanistan-related withholdings follow Cricsheet policy and are documented under Coverage.</li>
      </ul>
    </div>
    <div class="card">
      <div class="card-head"><h2>Sources</h2></div>
      <ul class="source-list">${sources || "<li>Cricsheet · Wikipedia · ESPNcricinfo</li>"}</ul>
      <p class="footnote mt-3">${escapeHtml(OFFICIAL?.meta?.note || "")}</p>
    </div>
    <div class="card">
      <div class="card-head"><h2>Site &amp; updates</h2></div>
      <div class="mini-stats">
        <div class="mini-row"><span class="k">Last generated</span><span class="v mono">${escapeHtml(gen)}</span></div>
        <div class="mini-row"><span class="k">Archive matches</span><span class="v mono">${fmtNum(matches)}</span></div>
        <div class="mini-row"><span class="k">Domain</span><span class="v"><a href="https://cricket.rkjat.in">cricket.rkjat.in</a></span></div>
        <div class="mini-row"><span class="k">Design</span><span class="v"><a href="https://crickrida.rkjat.in" target="_blank" rel="noopener">Crickrida-inspired</a></span></div>
      </div>
      <p class="about-p mt-3">Built as a static SPA for GitHub Pages. Feedback and corrections welcome via the site owner.</p>
    </div>
  `;
}

/* ── Overview ── */
function renderOverview() {
  if (!DATA) return;
  if (overviewRendered) {
    // still refresh recent table links if needed — full re-render is fine & cheap for tiles
  }
  overviewRendered = true;

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

  const ha = DATA.by_home_away;
  $("#homeAwayCards").innerHTML = ["home", "away"]
    .map((k) => {
      const s = ha[k] || { played: 0, won: 0, win_pct: 0 };
      return `<div class="mini-row"><span class="k">${k === "home" ? "Home" : "Away"}</span>
        <span class="v">${s.won}/${s.played} · ${s.win_pct}%</span></div>`;
    })
    .join("");

  const t = DATA.toss;
  const tossWinRate = t.won_toss ? Math.round((t.toss_and_win / t.won_toss) * 1000) / 10 : 0;
  $("#tossCards").innerHTML = `
    <div class="mini-row"><span class="k">Toss won</span><span class="v">${t.won_toss}</span></div>
    <div class="mini-row"><span class="k">Toss lost</span><span class="v">${t.lost_toss}</span></div>
    <div class="mini-row"><span class="k">Win after winning toss</span><span class="v">${t.toss_and_win} (${tossWinRate}%)</span></div>
  `;

  const bfWin = t.bat_first_matches ? Math.round((t.won_bat_first / t.bat_first_matches) * 1000) / 10 : 0;
  const chWin = t.chase_matches ? Math.round((t.won_chase / t.chase_matches) * 1000) / 10 : 0;
  $("#chaseCards").innerHTML = `
    <div class="mini-row"><span class="k">Bat first</span><span class="v">${t.won_bat_first}/${t.bat_first_matches} · ${bfWin}%</span></div>
    <div class="mini-row"><span class="k">Chasing</span><span class="v">${t.won_chase}/${t.chase_matches} · ${chWin}%</span></div>
  `;

  $("#topBatters").innerHTML = DATA.batting
    .slice(0, 8)
    .map(
      (p, i) => `
    <button type="button" class="rank-item player-link" data-player="${escapeAttr(p.name)}">
      <span class="pos">${i + 1}</span>
      ${playerAvatar(p.name, "sm")}
      <div><div class="name">${escapeHtml(p.name)}</div><div class="meta">${p.matches} mat · avg ${p.avg ?? "—"} · SR ${p.sr}</div></div>
      <span class="num">${fmtNum(p.runs)}</span>
    </button>`
    )
    .join("");

  $("#topBowlers").innerHTML = DATA.bowling
    .slice(0, 8)
    .map(
      (p, i) => `
    <button type="button" class="rank-item player-link" data-player="${escapeAttr(p.name)}">
      <span class="pos">${i + 1}</span>
      ${playerAvatar(p.name, "sm")}
      <div><div class="name">${escapeHtml(p.name)}</div><div class="meta">${p.matches} mat · avg ${p.avg ?? "—"} · ${p.best}</div></div>
      <span class="num magenta">${fmtNum(p.wickets)}</span>
    </button>`
    )
    .join("");

  $("#recentTable tbody").innerHTML = DATA.matches
    .slice(0, 12)
    .map(
      (m) => `
    <tr class="clickable-row" data-match="${escapeAttr(m.id)}">
      <td class="mono match-link">${m.date}</td>
      <td><span class="badge badge-fmt">${m.format}</span></td>
      <td class="player match-link">${escapeHtml(m.opponent)}</td>
      <td><span class="badge ${RESULT_BADGE[m.result] || ""}">${resultLabel(m.result)}</span></td>
      <td class="mono">${escapeHtml(m.margin || "—")}</td>
      <td>${escapeHtml(m.venue || "—")}</td>
      <td>${(m.pom || []).map((p) => escapeHtml(p)).join(", ") || "—"}</td>
    </tr>`
    )
    .join("");

  renderOverviewCharts();
}

function renderOverviewCharts() {
  if (typeof Chart === "undefined" || !DATA) return;
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
        {
          label: "Draw / Tie / NR",
          data: [
            f.Test.draw + f.Test.tied + f.Test.nr,
            f.ODI.draw + f.ODI.tied + f.ODI.nr,
            f.T20.draw + f.T20.tied + f.T20.nr,
          ],
          backgroundColor: "#5C5C70",
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
function renderFormats() {
  if (formatsRendered || !DATA) return;
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
    ducks: p.ducks,
  };
}

function renderBatting() {
  if (!DATA) return;
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
    if (sort === "avg" || sort === "sr") {
      if (av == null) return 1;
      if (bv == null) return -1;
    }
    return bv - av;
  });

  if (sort === "avg" || sort === "sr") {
    rows = rows.filter((p) => p.innings >= 10 && p.runs >= 200);
  }

  $("#battingTable tbody").innerHTML = rows
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
  if (!DATA) return;
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
  if (!DATA) return;
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
    <button type="button" class="rank-item player-link" data-player="${escapeAttr(p.player)}">
      <span class="pos">${i + 1}</span>
      ${playerAvatar(p.player, "sm")}
      <div><div class="name">${escapeHtml(p.player)}</div></div>
      <span class="num amber">${p.awards}</span>
    </button>`
    )
    .join("");
}

/* ── H2H ── */
function renderH2H() {
  if (!DATA) return;
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
        <td class="player">${escapeHtml(o.opponent)}</td>
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
  if (!DATA) return;
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
        <td class="player" style="white-space:normal;min-width:180px">${escapeHtml(v.venue)}</td>
        <td>${escapeHtml(v.city || "—")}</td>
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
  if (!DATA) return;
  const r = DATA.records;

  $("#highTotals tbody").innerHTML = r.highest_totals
    .slice(0, 25)
    .map(
      (t) => `<tr>
      <td class="mono" style="color:var(--cyan);font-weight:600">${t.runs}/${t.wickets} <span style="color:var(--text-dim)">(${t.overs})</span></td>
      <td><span class="badge badge-fmt">${t.format}</span></td>
      <td>${escapeHtml(t.opponent)}</td>
      <td class="mono">${t.date}</td>
      <td style="white-space:normal">${escapeHtml(t.venue)}</td>
    </tr>`
    )
    .join("");

  $("#lowTotals tbody").innerHTML = r.lowest_totals
    .slice(0, 20)
    .map(
      (t) => `<tr>
      <td class="mono" style="color:var(--magenta);font-weight:600">${t.runs}/${t.wickets}</td>
      <td><span class="badge badge-fmt">${t.format}</span></td>
      <td>${escapeHtml(t.opponent)}</td>
      <td class="mono">${t.date}</td>
      <td style="white-space:normal">${escapeHtml(t.venue)}</td>
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
        <td>${escapeHtml(t.opponent)}</td>
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
      <td>${escapeHtml(t.opponent)}</td>
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
      <td>${escapeHtml(t.opponent)}</td>
      <td class="mono">${t.date}</td>
      <td style="white-space:normal">${escapeHtml(t.venue)}</td>
    </tr>`
    )
    .join("");

  $("#bigWinsW tbody").innerHTML = r.biggest_wins_wickets
    .slice(0, 20)
    .map(
      (t) => `<tr>
      <td class="mono" style="color:#4ade80;font-weight:600">${t.margin} wkts</td>
      <td><span class="badge badge-fmt">${t.format}</span></td>
      <td>${escapeHtml(t.opponent)}</td>
      <td class="mono">${t.date}</td>
      <td style="white-space:normal">${escapeHtml(t.venue)}</td>
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
  if (!DATA) return;
  const rows = filteredMatches();
  const totalPages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  if (matchPage >= totalPages) matchPage = totalPages - 1;
  if (matchPage < 0) matchPage = 0;

  const slice = rows.slice(matchPage * PAGE_SIZE, (matchPage + 1) * PAGE_SIZE);
  $("#matchCount").textContent = `${fmtNum(rows.length)} matches · page ${matchPage + 1} of ${totalPages} · click row for scorecard`;

  $("#matchesTable tbody").innerHTML = slice
    .map(
      (m) => `<tr class="clickable-row" data-match="${escapeAttr(m.id)}">
      <td class="mono match-link">${m.date}</td>
      <td><span class="badge badge-fmt">${m.format}</span></td>
      <td class="player match-link">${escapeHtml(m.opponent)}</td>
      <td><span class="badge ${RESULT_BADGE[m.result] || ""}">${resultLabel(m.result)}</span></td>
      <td class="mono">${escapeHtml(m.margin || "—")}</td>
      <td style="white-space:normal;min-width:140px">${escapeHtml(m.venue || "—")}</td>
      <td style="white-space:normal;min-width:120px;color:var(--text-muted)">${escapeHtml(m.event || "—")}${m.stage ? " · " + escapeHtml(m.stage) : ""}</td>
      <td>${(m.pom || []).map((p) => escapeHtml(p)).join(", ") || "—"}</td>
      <td>${qualityBadge(m.quality)}</td>
    </tr>`
    )
    .join("");

  const pager = $("#matchPager");
  let html = `<button type="button" ${matchPage === 0 ? "disabled" : ""} data-p="${matchPage - 1}">← Prev</button>`;
  html += `<span>${matchPage + 1} / ${totalPages}</span>`;
  html += `<button type="button" ${matchPage >= totalPages - 1 ? "disabled" : ""} data-p="${matchPage + 1}">Next →</button>`;
  pager.innerHTML = html;
  pager.querySelectorAll("button[data-p]").forEach((btn) => {
    btn.addEventListener("click", () => {
      matchPage = Number(btn.dataset.p);
      renderMatches();
    });
  });
}

/* ── Coverage ── */
function renderMissing() {
  if (!DATA) return;
  const m = DATA.missing;
  const cov = m.by_format_vs_official;
  const q = m.quality || {};
  const sum = m.summary || {};

  $("#missingCoverage").innerHTML =
    ["Test", "ODI", "T20"]
      .map((fmt) => {
        const c = cov[fmt];
        const accent = FMT_COLORS[fmt];
        return `
      <div class="stat-tile" style="--accent:${accent}">
        <div class="label">${fmt} coverage</div>
        <div class="value">${c.coverage_pct}%</div>
        <div class="sub">${fmtNum(c.in_dataset)} of ~${fmtNum(c.official_approx)} · full-ball ${c.full_ball_pct ?? "—"}%</div>
      </div>`;
      })
      .join("") +
    `
    <div class="stat-tile" style="--accent:#22C55E">
      <div class="label">Full ball-by-ball</div>
      <div class="value">${fmtNum(q.full ?? sum.full_ball_matches)}</div>
      <div class="sub">of ${fmtNum(sum.dataset_matches)} matches</div>
    </div>
    <div class="stat-tile" style="--accent:#FFB800">
      <div class="label">Partial</div>
      <div class="value">${fmtNum(q.partial ?? sum.partial_matches)}</div>
      <div class="sub">limited innings data</div>
    </div>
    <div class="stat-tile" style="--accent:#F43F5E">
      <div class="label">Empty shells</div>
      <div class="value">${fmtNum(q.empty ?? sum.empty_shells)}</div>
      <div class="sub">no ball-by-ball cards</div>
    </div>
    <div class="stat-tile" style="--accent:#8B8B9E">
      <div class="label">Withheld (AFG)</div>
      <div class="value">${m.withheld?.count ?? sum.withheld_afghanistan_policy ?? "—"}</div>
      <div class="sub">Cricsheet policy</div>
    </div>
    <div class="stat-tile" style="--accent:#00E5FF">
      <div class="label">Est. career missing</div>
      <div class="value">${fmtNum(
        cov.Test.estimated_missing + cov.ODI.estimated_missing + cov.T20.estimated_missing
      )}</div>
      <div class="sub">vs official totals</div>
    </div>`;

  $("#missingBlocks").innerHTML = `
    <div class="missing-block">
      <h3>1. Historical pre-archive gap</h3>
      <p><strong>Tests:</strong> ${escapeHtml(m.historical_gap.tests_before_dataset)}<br/>
      <strong>ODIs:</strong> ${escapeHtml(m.historical_gap.odis_before_dataset)}<br/>
      <strong>T20Is:</strong> ${escapeHtml(m.historical_gap.t20_coverage)}</p>
    </div>
    <div class="missing-block">
      <h3>2. Data quality tiers</h3>
      <p><strong>Full:</strong> ${fmtNum(q.full)} with bat/bowl cards · <strong>Partial:</strong> ${fmtNum(q.partial)} · <strong>Empty:</strong> ${fmtNum(q.empty)} shells without ball-by-ball. Player aggregates use deliveries from full (and partial where available) matches only.</p>
    </div>
    <div class="missing-block">
      <h3>3. Afghanistan policy withholdings</h3>
      <p>${escapeHtml(m.withheld?.reason || "")} Count: <strong>${m.withheld?.count ?? "—"}</strong>. See <a href="${escapeAttr(m.withheld?.url || "https://cricsheet.org/withheld-matches")}" target="_blank" rel="noopener">cricsheet.org/withheld-matches</a>. ${escapeHtml(m.withheld?.impact || "")}</p>
    </div>
    <div class="missing-block">
      <h3>4. What this means for stats</h3>
      <p>Player and team numbers on archive pages reflect only the ${fmtNum(sum.dataset_matches)} matches present (from ${sum.date_range?.[0]} to ${sum.date_range?.[1]}). Career greats who peaked earlier may be under-counted. Prefer <button type="button" class="inline-link" onclick="showView('official')">Official Records</button> for all-time totals.</p>
    </div>
  `;

  $("#missingWindow").innerHTML = `
    <div class="mw-item"><label>Earliest match</label><strong>${sum.date_range?.[0] || "—"}</strong></div>
    <div class="mw-item"><label>Latest match</label><strong>${sum.date_range?.[1] || "—"}</strong></div>
    <div class="mw-item"><label>Archive note</label><strong style="font-size:0.85rem;line-height:1.4;color:var(--text-muted)">${escapeHtml(sum.note || "")}</strong></div>
  `;

  const notes = {
    Test: "Most missing Tests are 1932–2001 (pre ball-by-ball). Many folder entries are empty shells.",
    ODI: "Large 1974–2002 gap; plus AFG ODIs withheld under policy.",
    T20: "Near-complete; remaining gap is largely India vs Afghanistan and edge cases.",
  };

  $("#missingTable tbody").innerHTML = ["Test", "ODI", "T20"]
    .map((fmt) => {
      const c = cov[fmt];
      return `<tr>
        <td><span class="badge badge-fmt">${fmt}</span></td>
        <td class="mono">${fmtNum(c.in_dataset)}</td>
        <td class="mono" style="color:var(--lime)">${fmtNum(c.full_ball)}</td>
        <td class="mono">~${fmtNum(c.official_approx)}</td>
        <td class="mono" style="color:var(--amber);font-weight:600">~${fmtNum(c.estimated_missing)}</td>
        <td class="mono" style="color:var(--cyan)">${c.coverage_pct}%</td>
        <td class="mono">${c.full_ball_pct ?? "—"}%</td>
        <td style="white-space:normal;min-width:200px;color:var(--text-muted)">${notes[fmt]}</td>
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
            label: "Full ball-by-ball",
            data: [cov.Test.full_ball, cov.ODI.full_ball, cov.T20.full_ball],
            backgroundColor: "#22C55E",
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
          x: { stacked: false, grid: { display: false } },
          y: { stacked: false, grid: { color: "rgba(30,30,42,0.9)" } },
        },
      },
    });
  }
}

/* ── Events / delegation ── */
function bindEvents() {
  $$(".nav-item").forEach((btn) => {
    btn.addEventListener("click", () => showView(btn.dataset.view));
  });

  $$("[data-nav]").forEach((a) => {
    a.addEventListener("click", (e) => {
      e.preventDefault();
      showView(a.dataset.nav);
    });
  });

  $("#menuToggle")?.addEventListener("click", openSidebar);
  $("#sidebarClose")?.addEventListener("click", closeSidebar);
  $("#sidebarBackdrop")?.addEventListener("click", closeSidebar);
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeSidebar();
  });

  window.addEventListener("hashchange", () => {
    if (applyingHash) return;
    applyRouteFromHash();
  });

  // Global click delegation
  document.addEventListener("click", (e) => {
    const playerBtn = e.target.closest("[data-player]");
    if (playerBtn) {
      e.preventDefault();
      e.stopPropagation();
      const pname = playerBtn.getAttribute("data-player");
      if (pname) showView("player", { name: pname });
      return;
    }
    const matchBtn = e.target.closest("[data-match]");
    if (matchBtn) {
      e.preventDefault();
      const mid = matchBtn.getAttribute("data-match");
      if (mid) showView("match", { id: mid });
      return;
    }
    const seriesBtn = e.target.closest("[data-series]");
    if (seriesBtn) {
      e.preventDefault();
      const sname = seriesBtn.getAttribute("data-series");
      if (sname) showView("series-detail", { name: sname });
    }
  });

  $$("#batFormatSeg .seg-btn").forEach((b) =>
    b.addEventListener("click", () => {
      $$("#batFormatSeg .seg-btn").forEach((x) => x.classList.remove("active"));
      b.classList.add("active");
      renderBatting();
    })
  );
  $("#batSearch")?.addEventListener("input", () => renderBatting());
  $("#batSort")?.addEventListener("change", () => renderBatting());

  $$("#bowlFormatSeg .seg-btn").forEach((b) =>
    b.addEventListener("click", () => {
      $$("#bowlFormatSeg .seg-btn").forEach((x) => x.classList.remove("active"));
      b.classList.add("active");
      renderBowling();
    })
  );
  $("#bowlSearch")?.addEventListener("input", () => renderBowling());
  $("#bowlSort")?.addEventListener("change", () => renderBowling());

  $("#h2hSearch")?.addEventListener("input", () => renderH2H());
  $("#h2hSort")?.addEventListener("change", () => renderH2H());

  $("#venueSearch")?.addEventListener("input", () => renderVenues());
  $("#venueFilter")?.addEventListener("change", () => renderVenues());

  ["matchSearch", "matchFormat", "matchResult", "matchHome"].forEach((id) => {
    const el = $("#" + id);
    if (!el) return;
    el.addEventListener(id === "matchSearch" ? "input" : "change", () => {
      matchPage = 0;
      renderMatches();
    });
  });

  $("#seriesSearch")?.addEventListener("input", () => renderSeriesList());
  $("#seriesSort")?.addEventListener("change", () => renderSeriesList());

  let searchTimer = null;
  $("#globalSearch")?.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      const q = $("#globalSearch").value || "";
      setHash("search", q ? { q } : {});
      renderSearch(q);
    }, 180);
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
    buildMatchIndex();
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
    $("#footerMeta").textContent = `Generated ${DATA.meta.generated} · ${DATA.meta.matches} matches · Official as of ${OFFICIAL?.meta?.as_of || "—"}`;

    bindEvents();

    // Prefetch overview charts data path without showing (lazy on first visit)
    // Default route from hash or official
    if (location.hash && location.hash.length > 1) {
      applyRouteFromHash();
    } else {
      showView("official");
    }
  } catch (err) {
    $("#loading").innerHTML = `
      <p style="color:var(--magenta)">Failed to load data.</p>
      <p style="color:var(--text-muted);max-width:420px;text-align:center;margin-top:0.5rem">
        ${escapeHtml(err.message)}<br/><br/>
        Serve this folder over HTTP (browsers block local fetch). Example:<br/>
        <code style="font-family:var(--font-mono);color:var(--cyan)">cd dashboard && python3 -m http.server 8765</code>
      </p>`;
    console.error(err);
  }
}

// Expose for inline onclick handlers in HTML
window.showView = showView;

init();
