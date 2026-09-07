"""Verified portrait metadata and server-rendered attribution for player profiles."""
from __future__ import annotations

import html
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent


def load_portraits(path=None):
    path = Path(path) if path else ROOT / 'data' / 'portraits.json'
    if not path.exists():
        return {}
    records = json.loads(path.read_text(encoding='utf-8'))['players']
    for pid, p in records.items():
        if not p.get('author') or not p.get('license'):
            raise ValueError('Portrait needs individual attribution: ' + pid)
        if urlparse(p['source_url']).hostname != 'commons.wikimedia.org':
            raise ValueError('Portrait source must be a Commons file page: ' + pid)
        if not p['path'].startswith('/assets/portraits/') or '..' in p['path']:
            raise ValueError('Invalid local portrait path: ' + pid)
        if not (ROOT / 'web' / p['path'].removeprefix('/assets/')).is_file():
            raise ValueError('Missing portrait asset: ' + pid)
    return records


def initials(name):
    words = str(name).replace('-', ' ').split()
    return ''.join(w[0] for w in (words[:1] + words[-1:] if len(words) > 1 else words)).upper()


def portrait_figure(player_id, name, portraits, *, compact=False):
    """A figure including credit, or a deterministic initials fallback.

    Keep the complete returned figure next to the player's profile heading;
    credit must remain visible wherever a licensed portrait is rendered.
    """
    e = lambda value: html.escape(str(value), quote=True)
    p = portraits.get(player_id)
    css = 'player-portrait' + (' player-portrait--compact' if compact else '')
    if not p:
        return ('<figure class="' + css + ' player-portrait--fallback">'
                '<div class="portrait-initials" role="img" aria-label="' + e(name) + ' initials">'
                + e(initials(name)) + '</div><figcaption>Player portrait unavailable</figcaption></figure>')
    return ('<figure class="' + css + '"><img src="' + e(p['path']) + '" width="'
            + str(p['width']) + '" height="' + str(p['height']) + '" alt="' + e(name)
            + '" decoding="async" fetchpriority="high">'
            '<figcaption><span>Photo: ' + e(p['author']) + '</span> '
            '<a href="' + e(p['source_url']) + '" rel="license noopener">Wikimedia Commons</a>'
            ' · <a href="' + e(p['license_url']) + '" rel="license noopener">' + e(p['license'])
            + '</a><span class="portrait-changes">' + e(p['changes']) + '</span></figcaption></figure>')


def portrait_schema(player_id, portraits, base='https://cricket.rkjat.in'):
    """ImageObject usable as a Person's image; None for a fallback."""
    p = portraits.get(player_id)
    if not p:
        return None
    return {'@type': 'ImageObject', 'contentUrl': base.rstrip('/') + p['path'],
            'url': p['source_url'], 'license': p['license_url'],
            'creditText': p['author'] + ' / Wikimedia Commons / ' + p['license'],
            'creator': {'@type': 'Person', 'name': p['author']},
            'caption': p['name'], 'width': p['width'], 'height': p['height']}
