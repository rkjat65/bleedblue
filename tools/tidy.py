"""Publication copy filter: data pages lead with numbers, not explanations.

Explanatory sentences under headings and charts (notes, muted ledes and profile
intros) are dropped from data pages. Short data lines such as
"India v Australia · 2023-11-19 · ODI · Men" stay. Prose pages keep every word.
"""
import html
import re

# Sections whose text is the content itself.
PROSE_SECTIONS = {
    'about', 'advertise', 'blog', 'brand', 'contact', 'corrections', 'data-coverage', 'datasets',
    'editorial-policy', 'embed', 'insights', 'methodology', 'privacy', 'questions', 'research',
    'saved', 'search', 'studio',
}

_COPY = re.compile(r'<p class="(?:note|muted|player-intro)"[^>]*>(.*?)</p>', re.S)
_TAG = re.compile(r'<[^>]+>')


def is_explanation(fragment):
    """A sentence of explanation rather than a label: long, and written as prose."""
    text = html.unescape(_TAG.sub('', fragment)).strip()
    return len(text) > 40 and ('. ' in text or text.endswith(('.', '→')))


def tidy_copy(path, body):
    if path.strip('/').split('/')[0] in PROSE_SECTIONS:
        return body
    return _COPY.sub(lambda m: '' if is_explanation(m.group(1)) else m.group(0), body)
