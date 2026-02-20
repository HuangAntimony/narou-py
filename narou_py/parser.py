from __future__ import annotations

import html
import re


TAG_RE = re.compile(r'<[^>]+>')
SCRIPT_STYLE_RE = re.compile(r'<(script|style)\b.*?>.*?</\1>', re.IGNORECASE | re.DOTALL)
COMMENT_RE = re.compile(r'<!--.*?-->', re.DOTALL)


def pick_first(pattern: str | None, text: str, key: str) -> str:
    if not pattern:
        return ''
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return ''
    return match.groupdict().get(key, '') or ''


def strip_html(value: str) -> str:
    if not value:
        return ''
    out = COMMENT_RE.sub('', value)
    out = SCRIPT_STYLE_RE.sub('', out)
    out = TAG_RE.sub('', out)
    out = html.unescape(out)
    out = out.replace('\u00a0', ' ')
    out = re.sub(r'[ \t]+', ' ', out)
    out = re.sub(r'\r\n?', '\n', out)
    out = re.sub(r'\n{3,}', '\n\n', out)
    return out.strip()

