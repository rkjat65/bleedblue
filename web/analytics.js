/* Cricket Wicket audience measurement with a quiet, persistent opt-out. */
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

  function ready() {
    if (choice !== 'declined') loadAnalytics();
    const footer = document.querySelector('footer .muted');
    if (footer) {
      const settings = document.createElement('button');
      settings.id = 'analytics-settings';
      settings.type = 'button';
      settings.textContent = choice === 'declined' ? 'Enable analytics' : 'Disable analytics';
      settings.addEventListener('click', function () {
        if (choice === 'declined') {
          choice = 'accepted';
          try { localStorage.setItem(key, choice); } catch (_) { /* session-only choice */ }
          loadAnalytics();
          settings.textContent = 'Disable analytics';
          return;
        }
        choice = 'declined';
        try { localStorage.setItem(key, choice); } catch (_) { /* session-only choice */ }
        if (loaded && window.gtag) window.gtag('consent', 'update', { analytics_storage: 'denied' });
        eraseAnalyticsCookies();
        window.location.reload();
      });
      footer.appendChild(settings);
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ready);
  else ready();
}());
