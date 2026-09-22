/* Cricket Wicket analytics: no Google request until the reader opts in. */
(function () {
  'use strict';
  const measurementId = 'G-DXRDX6R7YY';
  const key = 'cw-analytics-consent';
  let choice = null;
  let loaded = false;

  try { choice = localStorage.getItem(key); } catch (_) { /* storage may be blocked */ }

  function loadAnalytics() {
    if (loaded) return;
    loaded = true;
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag('consent', 'default', {
      analytics_storage: 'granted',
      ad_storage: 'denied',
      ad_user_data: 'denied',
      ad_personalization: 'denied'
    });
    window.gtag('js', new Date());
    window.gtag('config', measurementId);
    const script = document.createElement('script');
    script.async = true;
    script.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(measurementId);
    document.head.appendChild(script);
  }

  function eraseAnalyticsCookies() {
    const domains = ['', 'cricket.rkjat.in', 'rkjat.in'];
    document.cookie.split(';').forEach(function (part) {
      const name = part.trim().split('=')[0];
      if (!/^_ga(?:_|$)/.test(name)) return;
      domains.forEach(function (domain) {
        document.cookie = name + '=; Max-Age=0; path=/; SameSite=Lax' + (domain ? '; domain=' + domain : '');
      });
    });
  }

  function setChoice(value) {
    choice = value;
    try { localStorage.setItem(key, value); } catch (_) { /* session-only choice */ }
    if (value === 'accepted') loadAnalytics();
    else {
      if (loaded && window.gtag) window.gtag('consent', 'update', { analytics_storage: 'denied' });
      eraseAnalyticsCookies();
      if (loaded) { window.location.reload(); return; }
    }
    const panel = document.getElementById('analytics-choice');
    if (panel) panel.hidden = true;
  }

  function showChoice() {
    const panel = document.getElementById('analytics-choice');
    if (panel) panel.hidden = false;
  }

  function ready() {
    const panel = document.createElement('aside');
    panel.id = 'analytics-choice';
    panel.className = 'analytics-choice';
    panel.setAttribute('aria-label', 'Analytics choice');
    panel.innerHTML = '<div><strong>Help us understand how readers use Cricket Wicket</strong><p>With your permission, Google Analytics measures visits and page use. No analytics is sent before you choose. <a href="/privacy/">Privacy details</a></p></div><div class="analytics-choice-actions"><button type="button" data-analytics="declined">Decline</button><button type="button" class="primary" data-analytics="accepted">Allow analytics</button></div>';
    panel.addEventListener('click', function (event) {
      const button = event.target.closest('[data-analytics]');
      if (button) setChoice(button.dataset.analytics);
    });
    document.body.appendChild(panel);
    const footer = document.querySelector('footer .muted');
    if (footer) {
      const settings = document.createElement('button');
      settings.id = 'analytics-settings';
      settings.type = 'button';
      settings.textContent = 'Analytics settings';
      settings.addEventListener('click', showChoice);
      footer.appendChild(settings);
    }
    if (choice === 'accepted') loadAnalytics();
    panel.hidden = choice === 'accepted' || choice === 'declined';
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ready);
  else ready();
}());
