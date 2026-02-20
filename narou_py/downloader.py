from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from .models import Novel, Section, SiteConfig, Subtitle
from .parser import pick_first, strip_html
from .sites import detect_site


class UnsupportedTarget(ValueError):
    pass


class PyNarouDownloader:
    section_dir_name = '本文'

    def __init__(
        self,
        target: str,
        *,
        output_root: str | Path = 'archive',
        custom_title: str | None = None,
        stream=None,
    ) -> None:
        detected = detect_site(target)
        if not detected:
            raise UnsupportedTarget(f'unsupported target: {target}')
        self.site, self.ncode = detected
        self.toc_url = self.site.toc_url_template.format(ncode=self.ncode)
        if self.site.key == 'narou':
            match = re.match(r'^(?P<scheme>https?)://(?P<host>[^/]+)/(?P<ncode>n\d+[a-z]+)/?$', target.strip(), re.IGNORECASE)
            if match:
                self.toc_url = f"{match.group('scheme').lower()}://{match.group('host').lower()}/{self.ncode}/"
        if self.site.key == 'arcadia' and 'www.mai-net.net/bbs/sst/sst.php' in target:
            self.toc_url = target.strip()
        self.output_root = Path(output_root)
        self.custom_title = custom_title.strip() if custom_title else None
        self.stream = stream or sys.stdout
        self._kakuyomu_work: dict | None = None

    def fetch_novel(self) -> Novel:
        toc_pages = self._fetch_toc_pages()
        toc_html = toc_pages[0] if toc_pages else ''
        if self.site.key == 'kakuyomu':
            self._kakuyomu_work = self._parse_kakuyomu_work(toc_html)
            title = strip_html(str(self._kakuyomu_work.get('title', '')))
            author = strip_html(str(self._kakuyomu_work.get('author', '')))
            story = str(self._kakuyomu_work.get('introduction', '')).replace('\n', '<br>')
        else:
            title = strip_html(pick_first(self.site.title_pattern, toc_html, 'title'))
            author = strip_html(pick_first(self.site.author_pattern, toc_html, 'author'))
            story = strip_html(pick_first(self.site.story_pattern, toc_html, 'story'))
            if not author and self.site.key == 'arcadia':
                author = strip_html(pick_first(self.site.author_pattern, toc_html, 'author2'))
        if (not title or not author or not story) and self.site.novel_info_url_template:
            info_url = self.site.novel_info_url_template.format(ncode=self.ncode)
            info_html = self._fetch_text(info_url, self.site)
            title = title or strip_html(pick_first(self.site.title_pattern, info_html, 'title'))
            author = author or strip_html(pick_first(self.site.author_pattern, info_html, 'author'))
            if not author and self.site.key == 'arcadia':
                author = strip_html(pick_first(self.site.author_pattern, info_html, 'author2'))
            story = story or strip_html(pick_first(self.site.story_pattern, info_html, 'story'))
            title = title or self._fallback_title(info_html)
        title = title or self._fallback_title(toc_html)
        if self.custom_title:
            title = self.custom_title
        subtitles = tuple(self._parse_subtitles_pages(toc_pages or [toc_html]))
        return Novel(
            ncode=self.ncode,
            toc_url=self.toc_url,
            title=title,
            author=author,
            story=story,
            site=self.site.name,
            subtitles=subtitles,
        )

    def download(self, *, skip_existing: bool = True) -> Path:
        novel = self.fetch_novel()
        novel_dir = self._novel_dir(novel)
        section_dir = novel_dir / self.section_dir_name
        section_dir.mkdir(parents=True, exist_ok=True)
        existing_indexes = self._load_existing_indexes(section_dir) if skip_existing else set()
        self._log(f'[{self.site.key}] {self.ncode} {novel.title}')
        self._log(f'toc: {novel.toc_url}')
        toc = {
            'title': novel.title,
            'author': novel.author,
            'toc_url': novel.toc_url,
            'story': novel.story,
            'subtitles': [subtitle.__dict__ for subtitle in novel.subtitles],
        }
        (novel_dir / 'toc.json').write_text(
            json.dumps(toc, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
        downloaded = 0
        skipped = 0
        for subtitle in novel.subtitles:
            if subtitle.index in existing_indexes:
                skipped += 1
                self._log(f'[skip] {subtitle.index} {subtitle.subtitle}')
                continue
            self._log(f'[download] {subtitle.index} {subtitle.subtitle}')
            section = self._download_section(subtitle)
            payload = {
                'index': subtitle.index,
                'subtitle': subtitle.subtitle,
                'chapter': subtitle.chapter,
                'subdate': subtitle.subdate,
                'subupdate': subtitle.subupdate,
                'element': {
                    'data_type': 'html',
                    'introduction': section.introduction,
                    'body': section.body,
                    'postscript': section.postscript,
                    'downloaded_at': section.downloaded_at.isoformat(),
                },
            }
            filename = f'{subtitle.index} {self._safe_filename(subtitle.subtitle)}.json'
            (section_dir / filename).write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding='utf-8',
            )
            downloaded += 1
            self._log(f'[saved] {subtitle.index} {subtitle.subtitle}')
        self._log(f'done: downloaded={downloaded}, skipped={skipped}, total={len(novel.subtitles)}')
        return novel_dir

    def _download_section(self, subtitle: Subtitle) -> Section:
        url = urljoin(self.toc_url, subtitle.href)
        html = self._fetch_text(url, self.site)
        body = pick_first(self.site.body_pattern, html, 'body')
        introduction = pick_first(self.site.introduction_pattern, html, 'introduction')
        postscript = pick_first(self.site.postscript_pattern, html, 'postscript')
        if not postscript:
            postscript = pick_first(self.site.body_pattern, html, 'postscript')
        if self.site.key == 'hameln':
            introduction = introduction or self._extract_by_patterns(
                html,
                (
                    r'<div id="maegaki">(?P<v>.+?)</div>',
                    r'<div class="maegaki">(?P<v>.+?)</div>',
                ),
            )
            body = body or self._extract_by_patterns(
                html,
                (
                    r'<div id="honbun">(?P<v>.+?)</div>',
                    r'<div id="novel_honbun">(?P<v>.+?)</div>',
                    r'<div class="honbun">(?P<v>.+?)</div>',
                    r'<div class="ss">(?P<v>.+?)</div>',
                ),
            )
            postscript = postscript or self._extract_by_patterns(
                html,
                (
                    r'<div id="atogaki">(?P<v>.+?)</div>',
                    r'<div class="atogaki">(?P<v>.+?)</div>',
                ),
            )
            if not body or len(strip_html(body)) <= 2:
                body = self._extract_hameln_body_fallback(html, introduction, postscript)
            body = self._trim_hameln_navigation_tail(body)
        if not body:
            self._log(f'[warn] empty body: {url}')
        return Section(
            introduction=introduction.strip(),
            body=body.strip(),
            postscript=postscript.strip(),
            downloaded_at=datetime.now(timezone.utc),
        )

    def _parse_subtitles(self, toc_html: str) -> list[Subtitle]:
        if self.site.key == 'kakuyomu':
            work = self._kakuyomu_work or self._parse_kakuyomu_work(toc_html)
            subtitles: list[Subtitle] = []
            chapter_title = ''
            for item in work.get('toc', []):
                kind = item.get('__typename', '')
                if kind == 'Chapter':
                    chapter_title = item.get('title', '')
                    continue
                if kind != 'Episode':
                    continue
                index = str(item.get('id', '')).strip()
                subtitle = strip_html(str(item.get('title', '')).strip())
                if not index or not subtitle:
                    continue
                subtitles.append(
                    Subtitle(
                        index=index,
                        href=f'/works/{self.ncode}/episodes/{index}',
                        subtitle=subtitle,
                        chapter=strip_html(chapter_title),
                        subdate='',
                        subupdate=str(item.get('publishedAt', '')).strip(),
                    )
                )
            return subtitles
        matches = re.finditer(self.site.subtitles_pattern, toc_html, re.DOTALL)
        subtitles: list[Subtitle] = []
        for match in matches:
            groups = match.groupdict()
            index = (groups.get('index') or '').strip()
            subtitle = strip_html((groups.get('subtitle') or '').replace('\t', ''))
            chapter = strip_html(groups.get('chapter') or '')
            href = groups.get('href')
            if not href:
                template = self.site.href_template or '{index}.html'
                href = template.format(index=index)
            subtitles.append(
                Subtitle(
                    index=index,
                    href=href,
                    subtitle=subtitle,
                    chapter=chapter,
                    subdate=(groups.get('subdate') or '').strip(),
                    subupdate=(groups.get('subupdate') or '').strip(),
                )
            )
        return subtitles

    def _parse_subtitles_pages(self, toc_pages: list[str]) -> list[Subtitle]:
        subtitles: list[Subtitle] = []
        seen_indexes: set[str] = set()
        carry_chapter = ''
        for toc_html in toc_pages:
            for item in self._parse_subtitles(toc_html):
                chapter = item.chapter or carry_chapter
                if item.chapter:
                    carry_chapter = item.chapter
                if chapter != item.chapter:
                    item = Subtitle(
                        index=item.index,
                        href=item.href,
                        subtitle=item.subtitle,
                        chapter=chapter,
                        subdate=item.subdate,
                        subupdate=item.subupdate,
                    )
                if item.index and item.index in seen_indexes:
                    continue
                if item.index:
                    seen_indexes.add(item.index)
                subtitles.append(item)
        return subtitles

    def _fetch_toc_pages(self) -> list[str]:
        first_page = self._fetch_text(self.toc_url, self.site)
        pages = [first_page]
        if self.site.key != 'narou':
            return pages
        page_max = self._extract_toc_page_max(first_page)
        for page_no in range(2, page_max + 1):
            page_url = self._with_page_query(self.toc_url, page_no)
            pages.append(self._fetch_text(page_url, self.site))
        return pages

    @staticmethod
    def _extract_toc_page_max(toc_html: str) -> int:
        match = re.search(
            r'<a href="/[^"]+?p=(?P<toc_page_max>\d+)" class="c-pager__item c-pager__item--last">',
            toc_html,
            flags=re.IGNORECASE,
        )
        if not match:
            return 1
        try:
            page_max = int(match.group('toc_page_max'))
        except ValueError:
            return 1
        return max(1, min(page_max, 200))

    @staticmethod
    def _with_page_query(url: str, page_no: int) -> str:
        parsed = urlparse(url)
        params = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k != 'p']
        params.append(('p', str(page_no)))
        query = urlencode(params)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, query, parsed.fragment))

    def _fetch_text(self, url: str, site: SiteConfig) -> str:
        headers = {
            'User-Agent': 'narou.py/0.1',
            'Accept-Language': 'ja,en-US;q=0.8,en;q=0.5',
        }
        if site.default_headers:
            headers.update(site.default_headers)
        if site.cookie:
            headers['Cookie'] = site.cookie
        req = urllib.request.Request(url=url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as res:
            return res.read().decode(site.encoding, errors='replace')

    def _novel_dir(self, novel: Novel) -> Path:
        folder = f'{novel.ncode} {self._safe_filename(novel.title)}'.strip()
        return self.output_root / novel.site / folder

    def _load_existing_indexes(self, section_dir: Path) -> set[str]:
        indexes: set[str] = set()
        for path in section_dir.glob('*.json'):
            parsed_index = ''
            try:
                with path.open('r', encoding='utf-8') as fp:
                    data = json.load(fp)
                index = str(data.get('index', '')).strip()
                parsed_index = index
                body = str(data.get('element', {}).get('body', '')).strip()
                introduction = str(data.get('element', {}).get('introduction', '')).strip()
                postscript = str(data.get('element', {}).get('postscript', '')).strip()
                # Empty previously-downloaded sections should be retried.
                if index and self._has_meaningful_content(body, introduction, postscript):
                    indexes.add(index)
                    continue
            except Exception:
                pass
            if parsed_index:
                # Parsed a valid index but content was empty: force re-download.
                continue
            match = re.match(r'^(\d+)\s', path.stem)
            if match:
                indexes.add(match.group(1))
        return indexes

    @staticmethod
    def _safe_filename(text: str) -> str:
        stripped = strip_html(text)
        cleaned = re.sub(r'[\\/:*?"<>|]', '_', stripped)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned[:120] or 'untitled'

    def _log(self, message: str) -> None:
        self.stream.write(message + '\n')
        self.stream.flush()

    def _fallback_title(self, html_text: str) -> str:
        match = re.search(r'<title[^>]*>(?P<title>.+?)</title>', html_text, re.IGNORECASE | re.DOTALL)
        if not match:
            return ''
        title = strip_html(match.group('title'))
        title = re.sub(r'\s*[-|｜]\s*(小説家になろう|ハーメルン|Hameln).*$','', title).strip()
        return title

    def _extract_by_patterns(self, text: str, patterns: tuple[str, ...]) -> str:
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                value = match.groupdict().get('v', '')
                if value and value.strip():
                    return value
        return ''

    def _extract_hameln_body_fallback(self, raw_html: str, introduction: str, postscript: str) -> str:
        body = raw_html
        for part in (introduction, postscript):
            if part:
                body = body.replace(part, '')
        body = re.sub(r'<script\b.*?</script>', '', body, flags=re.IGNORECASE | re.DOTALL)
        body = re.sub(r'<style\b.*?</style>', '', body, flags=re.IGNORECASE | re.DOTALL)
        markers = (
            r'<span style="font-size:\s*120%">.*?</span><br><br>',
            r'<div id="maegaki">.*?</div>',
        )
        for marker in markers:
            m = re.search(marker, body, flags=re.IGNORECASE | re.DOTALL)
            if m:
                body = body[m.end():]
                break
        tail_markers = (
            r'<div id="atogaki">',
            r'<div class="atogaki">',
            r'</body>',
        )
        end = len(body)
        for marker in tail_markers:
            m = re.search(marker, body, flags=re.IGNORECASE | re.DOTALL)
            if m:
                end = min(end, m.start())
        body = body[:end]
        return body.strip()

    def _trim_hameln_navigation_tail(self, body_html: str) -> str:
        if not body_html:
            return body_html
        hard_markers = (
            r'<div[^>]+id=(?:\\?["\'])nextpage(?:\\?["\'])[^>]*class=(?:\\?["\'])[^"\']*novelnavi',
            r'<span[^>]+id=(?:\\?["\'])analytics_end(?:\\?["\'])',
            r'<span[^>]+id=(?:\\?["\'])n_vid(?:\\?["\'])',
        )
        cut_pos = None
        for marker in hard_markers:
            match = re.search(marker, body_html, flags=re.IGNORECASE)
            if match:
                pos = match.start()
                cut_pos = pos if cut_pos is None else min(cut_pos, pos)
        if cut_pos is not None:
            return body_html[:cut_pos].rstrip()

        tail_plain = strip_html(body_html)[-600:]
        tokens = [
            '目 次',
            '次の話',
            '目次',
            '小説情報',
            '縦書き',
            'しおりを挟む',
            'お気に入り登録',
            '評価',
            '感想',
        ]
        hit_count = sum(1 for token in tokens if token in tail_plain)
        if hit_count < 3:
            return body_html
        marker = re.search(
            r'(目\s*次|次の話|目次|小説情報|縦書き|しおりを挟む|お気に入り登録|評価|感想)',
            body_html,
            flags=re.IGNORECASE,
        )
        if not marker:
            return body_html
        return body_html[:marker.start()].rstrip()

    def _parse_kakuyomu_work(self, html_text: str) -> dict:
        script_match = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(?P<json>.+?)</script>',
            html_text,
            flags=re.DOTALL,
        )
        if not script_match:
            return {}
        try:
            data = json.loads(script_match.group('json'))
            apollo_state = data['props']['pageProps']['__APOLLO_STATE__']
            work_id = data['query']['workId']
            work = dict(apollo_state.get(f'Work:{work_id}') or {})
            author_ref = (work.get('author') or {}).get('__ref', '')
            author = ''
            if author_ref:
                author_data = apollo_state.get(author_ref) or {}
                author = author_data.get('activityName', '')
            alt_name = work.get('alternateAuthorName')
            if alt_name:
                author = f'{alt_name}／{author}' if author else str(alt_name)
            toc_items: list[dict] = []
            for toc_ref in work.get('tableOfContents') or []:
                toc_entry = apollo_state.get((toc_ref or {}).get('__ref', '')) or {}
                chapter = toc_entry.get('chapter')
                if isinstance(chapter, dict) and chapter.get('__ref'):
                    chapter_data = apollo_state.get(chapter['__ref']) or {}
                    toc_items.append(
                        {
                            '__typename': 'Chapter',
                            'title': chapter_data.get('title', ''),
                        }
                    )
                for ep_ref in toc_entry.get('episodeUnions') or []:
                    ep = apollo_state.get((ep_ref or {}).get('__ref', '')) or {}
                    toc_items.append(
                        {
                            '__typename': ep.get('__typename', 'Episode'),
                            'id': ep.get('id', ''),
                            'title': ep.get('title', ''),
                            'publishedAt': ep.get('publishedAt', ''),
                        }
                    )
            return {
                'title': work.get('title', ''),
                'author': author,
                'introduction': work.get('introduction', ''),
                'toc': toc_items,
            }
        except Exception:
            return {}

    def _has_meaningful_content(self, body: str, introduction: str, postscript: str) -> bool:
        for content in (body, introduction, postscript):
            plain = strip_html(content or '')
            plain = re.sub(r'\s+', '', plain)
            if not plain:
                continue
            # Require at least one alnum/cjk char, not just broken symbols like "<".
            if re.search(r'[0-9A-Za-z\u3040-\u30ff\u3400-\u9fff]', plain):
                return True
        return False
