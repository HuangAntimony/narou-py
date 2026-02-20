from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SiteConfig:
    key: str
    name: str
    top_url: str
    url_patterns: tuple[str, ...]
    toc_url_template: str
    subtitles_pattern: str
    body_pattern: str
    introduction_pattern: str | None
    postscript_pattern: str | None
    title_pattern: str
    author_pattern: str
    story_pattern: str
    novel_info_url_template: str | None = None
    href_template: str | None = None
    encoding: str = 'utf-8'
    cookie: str | None = None
    default_headers: dict[str, str] | None = None


@dataclass(frozen=True)
class Subtitle:
    index: str
    href: str
    subtitle: str
    chapter: str = ''
    subdate: str = ''
    subupdate: str = ''


@dataclass(frozen=True)
class Section:
    introduction: str
    body: str
    postscript: str
    downloaded_at: datetime


@dataclass(frozen=True)
class Novel:
    ncode: str
    toc_url: str
    title: str
    author: str
    story: str
    site: str
    subtitles: tuple[Subtitle, ...]
