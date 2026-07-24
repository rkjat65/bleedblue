/* Team India Records — landing page interactions */

(function () {
  "use strict";

  // Mobile nav
  const navToggle = document.getElementById("navToggle");
  const siteNav = document.getElementById("siteNav");
  const navBackdrop = document.getElementById("navBackdrop");

  function closeNav() {
    siteNav?.classList.remove("open");
    navBackdrop?.classList.remove("visible");
    document.body.classList.remove("nav-open");
  }

  navToggle?.addEventListener("click", () => {
    const open = siteNav?.classList.toggle("open");
    navBackdrop?.classList.toggle("visible", open);
    document.body.classList.toggle("nav-open", open);
  });

  navBackdrop?.addEventListener("click", closeNav);
  siteNav?.querySelectorAll("a").forEach((a) => a.addEventListener("click", closeNav));

  // Format tabs
  const fmtTabs = document.querySelectorAll(".fmt-tab");
  const fmtPanels = document.querySelectorAll(".fmt-panel");

  fmtTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.format;
      fmtTabs.forEach((t) => t.classList.toggle("active", t === tab));
      fmtPanels.forEach((p) => p.classList.toggle("active", p.dataset.format === target));
    });
  });

  // Category filter (interactive — tabs, not cards)
  const catTabs = document.querySelectorAll(".cat-tab");
  const catGroups = document.querySelectorAll(".cat-group");

  catTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.category;
      catTabs.forEach((t) => t.classList.toggle("active", t === tab));
      catGroups.forEach((g) => {
        g.classList.toggle("active", g.dataset.category === target);
      });
    });
  });

  // Scroll reveal
  const revealEls = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );
    revealEls.forEach((el) => observer.observe(el));
  } else {
    revealEls.forEach((el) => el.classList.add("visible"));
  }

  // Archive coverage blurb (Official vs Archive section)
  const archiveLead = document.getElementById("archiveCoverageLead");
  if (archiveLead) {
    Promise.all([
      fetch("/stats.json").then((r) => (r.ok ? r.json() : null)),
      fetch("/official_records.json").then((r) => (r.ok ? r.json() : null)),
    ])
      .then(([stats, official]) => {
        if (!stats) {
          archiveLead.textContent =
            "Cricsheet ball-by-ball where available. Empty meta shells are excluded from team and player aggregates.";
          return;
        }
        const sum = stats.missing?.summary || {};
        const full = sum.full_ball_matches ?? stats.meta?.analytics_matches ?? "—";
        const catalog = sum.dataset_matches ?? stats.meta?.matches ?? "—";
        const shells = sum.empty_shells ?? "—";
        const offTests = official?.overall?.tests?.played ?? 599;
        const analytics = sum.analytics_matches ?? stats.overall?.played ?? full;
        archiveLead.textContent = `${full} full-ball matches power archive analytics (${analytics} in W/L tables). Catalog lists ${catalog} files including ${shells} meta-only shells. Official Tests played: ${offTests}.`;
      })
      .catch(() => {
        archiveLead.textContent =
          "Cricsheet ball-by-ball where available. Meta-only shells excluded from aggregates.";
      });
  }
})();
