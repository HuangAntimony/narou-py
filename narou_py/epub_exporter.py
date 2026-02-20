from __future__ import annotations

import hashlib
import html
import io
import json
import re
import struct
import zipfile
import zlib
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

from .parser import strip_html


class EpubExportError(ValueError):
    pass


class EpubExporter:
    section_dir_name = '本文'

    def __init__(self, novel_dir: str | Path) -> None:
        self.novel_dir = Path(novel_dir)
        self.toc_path = self.novel_dir / 'toc.json'
        self.section_dir = self.novel_dir / self.section_dir_name

    def export(self, output_path: str | Path | None = None, *, subjects: list[str] | None = None) -> Path:
        toc = self._load_toc()
        sections = self._load_sections()
        cover = self._find_cover_image()
        if not cover:
            cover = self._generate_cover_image(toc)
            # Keep generated cover in archive for visibility and manual replacement.
            (self.novel_dir / cover['name']).write_bytes(cover['data'])
        if not sections:
            raise EpubExportError(f'no sections found: {self.section_dir}')
        if output_path is None:
            output_path = self.novel_dir / f'{self._safe_filename(toc["title"])}.epub'
        epub_path = Path(output_path)
        epub_path.parent.mkdir(parents=True, exist_ok=True)
        book_id = self._book_id(toc.get('toc_url', ''))
        with zipfile.ZipFile(epub_path, 'w') as zf:
            zf.writestr(
                'mimetype',
                'application/epub+zip',
                compress_type=zipfile.ZIP_STORED,
            )
            zf.writestr('META-INF/container.xml', self._container_xml())
            zf.writestr('item/style/book-style.css', self._style_css())
            chapter_files = []
            if cover:
                zf.writestr(f'item/image/{cover["name"]}', cover['data'])
                zf.writestr(
                    'item/xhtml/cover.xhtml',
                    self._cover_xhtml(cover['name']),
                )
                chapter_files.append(('cover-page', 'xhtml/cover.xhtml', '表紙'))
            zf.writestr('item/xhtml/title.xhtml', self._title_xhtml(toc))
            chapter_files.append(('title-page', 'xhtml/title.xhtml', '表題'))
            for idx, section in enumerate(sections, start=1):
                filename = f'{idx:04d}.xhtml'
                chapter_files.append((f'sec{idx:04d}', f'xhtml/{filename}', section['subtitle']))
                zf.writestr(f'item/xhtml/{filename}', self._chapter_xhtml(section, idx))
            zf.writestr('item/nav.xhtml', self._nav_xhtml(sections, chapter_files))
            zf.writestr(
                'item/standard.opf',
                self._content_opf(toc, chapter_files, book_id, subjects or [], cover),
            )
            zf.writestr('item/toc.ncx', self._toc_ncx(toc, sections, chapter_files, book_id))
        return epub_path

    def _load_toc(self) -> dict:
        if not self.toc_path.exists():
            raise EpubExportError(f'toc file not found: {self.toc_path}')
        with self.toc_path.open('r', encoding='utf-8') as fp:
            return json.load(fp)

    def _load_sections(self) -> list[dict]:
        if not self.section_dir.exists():
            raise EpubExportError(f'section dir not found: {self.section_dir}')
        section_files = sorted(
            self.section_dir.glob('*.json'),
            key=lambda path: self._section_sort_key(path),
        )
        sections: list[dict] = []
        for path in section_files:
            with path.open('r', encoding='utf-8') as fp:
                raw = json.load(fp)
            sections.append(
                {
                    'index': str(raw.get('index', '')),
                    'subtitle': str(raw.get('subtitle', '')),
                    'chapter': str(raw.get('chapter', '')),
                    'introduction': str(raw.get('element', {}).get('introduction', '')),
                    'body': str(raw.get('element', {}).get('body', '')),
                    'postscript': str(raw.get('element', {}).get('postscript', '')),
                }
            )
        return sections

    def _chapter_xhtml(self, section: dict, order: int) -> str:
        title = section['subtitle'] or f'第{order}話'
        chapter = section['chapter']
        intro = self._html_fragment_to_paragraphs(section['introduction'])
        body = self._html_fragment_to_paragraphs(section['body'])
        post = self._html_fragment_to_paragraphs(section['postscript'])
        chapter_header = ''
        if chapter:
            chapter_header = f'<h2 class="chapter">{escape(chapter)}</h2>'
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE html>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" '
            'xml:lang="ja" lang="ja" class="vrtl">\n'
            '<head>\n'
            f'  <title>{escape(title)}</title>\n'
            '  <meta charset="UTF-8"/>\n'
            '  <link rel="stylesheet" type="text/css" href="../style/book-style.css"/>\n'
            '</head>\n'
            '<body>\n'
            '  <div class="main">\n'
            f'    {chapter_header}\n'
            f'    <h1>{escape(title)}</h1>\n'
            f'    {self._block("前書き", intro)}\n'
            f'    {self._body_block(body)}\n'
            f'    {self._block("後書き", post)}\n'
            '  </div>\n'
            '</body>\n'
            '</html>\n'
        )

    def _title_xhtml(self, toc: dict) -> str:
        title = escape(str(toc.get('title', '')))
        author = escape(str(toc.get('author', '')))
        story = self._html_fragment_to_paragraphs(str(toc.get('story', '')))
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE html>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" '
            'xml:lang="ja" lang="ja" class="vrtl p-titlepage">\n'
            '<head>\n'
            f'  <title>{title}</title>\n'
            '  <meta charset="UTF-8"/>\n'
            '  <link rel="stylesheet" type="text/css" href="../style/book-style.css"/>\n'
            '</head>\n'
            '<body>\n'
            '  <div class="main">\n'
            f'    <h1 class="book-title">{title}</h1>\n'
            f'    <div class="author"><p>{author}</p></div>\n'
            f'    {self._block("あらすじ", story)}\n'
            '  </div>\n'
            '</body>\n'
            '</html>\n'
        )

    def _content_opf(
        self,
        toc: dict,
        chapter_files: list[tuple[str, str, str]],
        book_id: str,
        subjects: list[str],
        cover: dict | None = None,
    ) -> str:
        manifest_items = [
            '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
            '<item id="book-style" href="style/book-style.css" media-type="text/css"/>',
            '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
        ]
        if cover:
            manifest_items.append(
                f'<item id="cover-image" href="image/{escape(cover["name"])}" '
                f'media-type="{escape(cover["media_type"])}" properties="cover-image"/>'
            )
        spine_items = []
        for item_id, filename, _title in chapter_files:
            manifest_items.append(
                f'<item id="{item_id}" href="{filename}" media-type="application/xhtml+xml"/>'
            )
            spine_items.append(f'<itemref idref="{item_id}"/>')
        subjects_xml = ''
        for subject in subjects:
            sub = subject.strip()
            if sub:
                subjects_xml += f'\n    <dc:subject>{escape(sub)}</dc:subject>'
        title = escape(str(toc.get('title', '')))
        author = escape(str(toc.get('author', '')))
        modified = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        cover_meta = '\n    <meta name="cover" content="cover-image"/>' if cover else ''
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" xml:lang="ja" unique-identifier="BookId">\n'
            '  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" '
            'xmlns:opf="http://www.idpf.org/2007/opf">\n'
            f'    <dc:title>{title}</dc:title>\n'
            f'    <dc:creator id="creator01">{author}</dc:creator>\n'
            '    <dc:language>ja</dc:language>\n'
            f'    <dc:identifier id="BookId">{escape(book_id)}</dc:identifier>\n'
            f'    <meta property="dcterms:modified">{modified}</meta>{cover_meta}{subjects_xml}\n'
            '  </metadata>\n'
            '  <manifest>\n'
            f'    {"".join(manifest_items)}\n'
            '  </manifest>\n'
            '  <spine page-progression-direction="rtl" toc="ncx">\n'
            f'    {"".join(spine_items)}\n'
            '  </spine>\n'
            '</package>\n'
        )

    def _toc_ncx(self, toc: dict, sections: list[dict], chapter_files: list[tuple[str, str, str]], book_id: str) -> str:
        nav_points = []
        play_order = 1
        current_chapter = None
        has_chapter_nesting = False
        section_pos = 0
        for item_id, filename, title in chapter_files:
            chapter_name = ''
            if item_id.startswith('sec') and section_pos < len(sections):
                chapter_name = sections[section_pos].get('chapter', '').strip()
                section_pos += 1
            if chapter_name and chapter_name != current_chapter:
                has_chapter_nesting = True
                nav_points.append(
                    '<navPoint id="navPoint-{0}" playOrder="{0}">'
                    '<navLabel><text>{1}</text></navLabel>'
                    '<content src="{2}"/></navPoint>'.format(
                        play_order,
                        escape(chapter_name),
                        escape(filename),
                    )
                )
                play_order += 1
                current_chapter = chapter_name
            nav_points.append(
                '<navPoint id="navPoint-{0}" playOrder="{0}">'
                '<navLabel><text>{1}</text></navLabel>'
                '<content src="{2}"/></navPoint>'.format(
                    play_order,
                    escape(title),
                    escape(filename),
                )
            )
            play_order += 1
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">\n'
            '  <head>\n'
            f'    <meta name="dtb:uid" content="{escape(book_id)}"/>\n'
            f'    <meta name="dtb:depth" content="{"2" if has_chapter_nesting else "1"}"/>\n'
            '    <meta name="dtb:totalPageCount" content="0"/>\n'
            '    <meta name="dtb:maxPageNumber" content="0"/>\n'
            '  </head>\n'
            f'  <docTitle><text>{escape(str(toc.get("title", "")))}</text></docTitle>\n'
            f'  <navMap>{"".join(nav_points)}</navMap>\n'
            '</ncx>\n'
        )

    @staticmethod
    def _container_xml() -> str:
        return (
            '<?xml version="1.0"?>\n'
            '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
            '<rootfiles>\n'
            '<rootfile full-path="item/standard.opf" media-type="application/oebps-package+xml"/>\n'
            '</rootfiles>\n'
            '</container>\n'
        )

    @staticmethod
    def _style_css() -> str:
        return (
            '@charset "utf-8";\n'
            '@namespace "http://www.w3.org/1999/xhtml";\n'
            'html.vrtl{writing-mode:vertical-rl;-webkit-writing-mode:vertical-rl;}\n'
            'body{font-family:serif;line-height:1.8;margin:0;}\n'
            '.main{margin:0 auto;padding:1em;max-width:34em;}\n'
            'h1{font-size:1.2em;margin:1.2em 0 .8em;}\n'
            'h2.chapter{font-size:1em;color:#555;margin-top:2em;}\n'
            'h3{font-size:1em;margin-top:1.6em;border-bottom:1px solid #ddd;}\n'
            'p{text-indent:1em;margin:.2em 0;text-align:justify;}\n'
            '.p-titlepage .book-title{text-align:center;}\n'
            '.p-titlepage .author p{text-indent:0;text-align:center;}\n'
            '.p-cover{margin:0;padding:0;}\n'
            '.p-cover .cover-image{display:block;width:100%;height:auto;}\n'
        )

    def _nav_xhtml(self, sections: list[dict], chapter_files: list[tuple[str, str, str]]) -> str:
        items = []
        current_chapter = None
        section_pos = 0
        for item_id, path, title in chapter_files:
            if item_id.startswith('sec') and section_pos < len(sections):
                chapter_name = sections[section_pos].get('chapter', '').strip()
                section_pos += 1
                if chapter_name and chapter_name != current_chapter:
                    items.append(f'<li class="chapter">{escape(chapter_name)}</li>')
                    current_chapter = chapter_name
            items.append(f'<li><a href="{escape(path)}">{escape(title)}</a></li>')
        body_href = 'xhtml/0001.xhtml'
        for _id, path, _title in chapter_files:
            if path == 'xhtml/cover.xhtml':
                continue
            if path == 'xhtml/title.xhtml':
                continue
            body_href = path
            break
        has_cover = any(path == 'xhtml/cover.xhtml' for _id, path, _title in chapter_files)
        cover_landmark = '<li><a epub:type="cover" href="xhtml/cover.xhtml">表紙</a></li>' if has_cover else ''
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE html>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" '
            'lang="ja" xml:lang="ja">\n'
            '<head>\n'
            '<meta charset="UTF-8"/>\n'
            '<title>目次</title>\n'
            '</head>\n'
            '<body>\n'
            '<nav epub:type="landmarks" id="landmarks" hidden="">\n'
            '<h2>Guide</h2><ol>'
            '<li><a epub:type="toc" href="nav.xhtml">目次</a></li>'
            f'{cover_landmark}'
            '<li><a epub:type="titlepage" href="xhtml/title.xhtml">扉</a></li>'
            f'<li><a epub:type="bodymatter" href="{escape(body_href)}">本文</a></li>'
            '</ol></nav>\n'
            '<nav epub:type="toc" id="toc">\n'
            '<h1>目次</h1>\n'
            f'<ol>{"".join(items)}</ol>\n'
            '</nav>\n'
            '</body>\n'
            '</html>\n'
        )

    @staticmethod
    def _cover_xhtml(image_name: str) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE html>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" '
            'xml:lang="ja" lang="ja">\n'
            '<head>\n'
            '  <meta charset="UTF-8"/>\n'
            '  <title>表紙</title>\n'
            '  <link rel="stylesheet" type="text/css" href="../style/book-style.css"/>\n'
            '</head>\n'
            '<body epub:type="cover" class="p-cover">\n'
            f'  <img class="cover-image" src="../image/{escape(image_name)}" alt="表紙"/>\n'
            '</body>\n'
            '</html>\n'
        )

    def _find_cover_image(self) -> dict | None:
        for ext, media_type in (('.jpg', 'image/jpeg'), ('.png', 'image/png'), ('.jpeg', 'image/jpeg')):
            path = self.novel_dir / f'cover{ext}'
            if path.exists() and path.is_file():
                return {
                    'name': path.name,
                    'data': path.read_bytes(),
                    'media_type': media_type,
                }
        return None

    def _generate_cover_image(self, toc: dict) -> dict:
        title = strip_html(str(toc.get('title', ''))).strip() or 'Untitled'
        author = strip_html(str(toc.get('author', ''))).strip() or 'Unknown Author'
        seed = int(hashlib.sha1(title.encode('utf-8')).hexdigest()[:8], 16)
        png = self._build_cover_png_with_text(1200, 1600, seed, title, author)
        return {
            'name': 'cover.png',
            'data': png,
            'media_type': 'image/png',
        }

    @staticmethod
    def _wrap_text(text: str, width: int) -> list[str]:
        if not text:
            return ['']
        chunks: list[str] = []
        current = ''
        for ch in text:
            current += ch
            if len(current) >= width:
                chunks.append(current)
                current = ''
        if current:
            chunks.append(current)
        return chunks

    @staticmethod
    def _build_cover_png(width: int, height: int, seed: int) -> bytes:
        # Minimal modern palette: clean gradient only.
        top_r = 64 + (seed % 10)
        top_g = 104 + ((seed >> 6) % 12)
        top_b = 176 + ((seed >> 12) % 14)
        bottom_r = 24 + ((seed >> 18) % 8)
        bottom_g = 42 + ((seed >> 22) % 10)
        bottom_b = 104 + ((seed >> 26) % 12)

        raw = bytearray()
        for y in range(height):
            t = y / max(1, height - 1)
            r = int(top_r * (1.0 - t) + bottom_r * t)
            g = int(top_g * (1.0 - t) + bottom_g * t)
            b = int(top_b * (1.0 - t) + bottom_b * t)
            raw.append(0)  # PNG filter type 0
            for x in range(width):
                rr, gg, bb = r, g, b
                raw.extend((rr, gg, bb))

        compressed = zlib.compress(bytes(raw), level=9)

        def chunk(tag: bytes, data: bytes) -> bytes:
            return (
                struct.pack('!I', len(data))
                + tag
                + data
                + struct.pack('!I', zlib.crc32(tag + data) & 0xffffffff)
            )

        signature = b'\x89PNG\r\n\x1a\n'
        ihdr = struct.pack('!IIBBBBB', width, height, 8, 2, 0, 0, 0)
        return signature + chunk(b'IHDR', ihdr) + chunk(b'IDAT', compressed) + chunk(b'IEND', b'')

    def _build_cover_png_with_text(self, width: int, height: int, seed: int, title: str, author: str) -> bytes:
        base_png = self._build_cover_png(width, height, seed)
        try:
            from PIL import Image, ImageDraw, ImageFont
        except Exception:
            return base_png

        image = Image.open(io.BytesIO(base_png)).convert('RGB')
        draw = ImageDraw.Draw(image)
        title_font = self._load_cover_font(ImageFont, 84)
        author_font = self._load_cover_font(ImageFont, 48)

        max_text_width = int(width * 0.82)
        title_lines = self._wrap_text_pixels(draw, title, title_font, max_text_width, max_lines=4)
        author_lines = self._wrap_text_pixels(draw, author, author_font, max_text_width, max_lines=2)

        total_h = len(title_lines) * 104 + 64 + len(author_lines) * 62
        y = max(120, (height - total_h) // 2)

        for line in title_lines:
            bbox = draw.textbbox((0, 0), line, font=title_font)
            line_w = bbox[2] - bbox[0]
            x = (width - line_w) // 2
            self._draw_text_with_shadow(draw, (x, y), line, title_font, fill=(244, 234, 210))
            y += 104
        y += 28
        for line in author_lines:
            bbox = draw.textbbox((0, 0), line, font=author_font)
            line_w = bbox[2] - bbox[0]
            x = (width - line_w) // 2
            self._draw_text_with_shadow(draw, (x, y), line, author_font, fill=(228, 216, 182))
            y += 62

        out = io.BytesIO()
        image.save(out, format='PNG', optimize=True)
        return out.getvalue()

    @staticmethod
    def _draw_text_with_shadow(draw, xy: tuple[int, int], text: str, font, fill: tuple[int, int, int]) -> None:
        x, y = xy
        draw.text((x + 1, y + 1), text, font=font, fill=(0, 0, 0, 110))
        draw.text((x, y), text, font=font, fill=fill)

    @staticmethod
    def _load_cover_font(image_font, size: int):
        candidates = [
            '/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc',
            '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc',
            '/System/Library/Fonts/Hiragino Sans GB.ttc',
            '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
            '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf',
        ]
        for path in candidates:
            try:
                return image_font.truetype(path, size=size)
            except Exception:
                continue
        return image_font.load_default()

    @staticmethod
    def _wrap_text_pixels(draw, text: str, font, max_width: int, max_lines: int) -> list[str]:
        text = (text or '').strip()
        if not text:
            return ['']
        lines: list[str] = []
        current = ''
        for ch in text:
            trial = current + ch
            bbox = draw.textbbox((0, 0), trial, font=font)
            if (bbox[2] - bbox[0]) <= max_width or not current:
                current = trial
            else:
                lines.append(current)
                current = ch
                if len(lines) >= max_lines:
                    break
        if current and len(lines) < max_lines:
            lines.append(current)
        if len(lines) > max_lines:
            lines = lines[:max_lines]
        if len(lines) == max_lines and len(''.join(lines)) < len(text):
            lines[-1] = lines[-1][:-1] + '…'
        return lines

    @staticmethod
    def _section_sort_key(path: Path) -> tuple[int, str]:
        stem = path.stem
        index = stem.split(' ', 1)[0].strip()
        try:
            return int(index), stem
        except ValueError:
            return 10**9, stem

    def _html_fragment_to_paragraphs(self, value: str) -> str:
        if not value:
            return ''
        text = value
        text = re.sub(r'<\s*br\s*/?\s*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</\s*p\s*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<\s*p[^>]*>', '', text, flags=re.IGNORECASE)
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]
        return ''.join(f'<p>{self._render_line_with_ruby(line)}</p>' for line in lines)

    def _render_line_with_ruby(self, line: str) -> str:
        ruby_blocks: list[str] = []

        def stash_ruby(match: re.Match[str]) -> str:
            ruby_blocks.append(self._normalize_ruby_block(match.group('inner')))
            return f'__RUBY_BLOCK_{len(ruby_blocks) - 1}__'

        placeholder_text = re.sub(
            r'<\s*ruby[^>]*>(?P<inner>.*?)</\s*ruby\s*>',
            stash_ruby,
            line,
            flags=re.IGNORECASE | re.DOTALL,
        )
        plain = escape(html.unescape(strip_html(placeholder_text)))
        for idx, ruby in enumerate(ruby_blocks):
            plain = plain.replace(f'__RUBY_BLOCK_{idx}__', ruby)
        return plain

    def _normalize_ruby_block(self, inner: str) -> str:
        rb = re.findall(r'<\s*rb[^>]*>(.*?)</\s*rb\s*>', inner, flags=re.IGNORECASE | re.DOTALL)
        rt = re.findall(r'<\s*rt[^>]*>(.*?)</\s*rt\s*>', inner, flags=re.IGNORECASE | re.DOTALL)
        if rb:
            base = ''.join(strip_html(part) for part in rb).strip()
        else:
            without_rt = re.sub(r'<\s*rt[^>]*>.*?</\s*rt\s*>', '', inner, flags=re.IGNORECASE | re.DOTALL)
            without_rp = re.sub(r'<\s*rp[^>]*>.*?</\s*rp\s*>', '', without_rt, flags=re.IGNORECASE | re.DOTALL)
            base = strip_html(without_rp).strip()
        reading = ''.join(strip_html(part) for part in rt).strip()
        if base and reading:
            return (
                f'<ruby><rb>{escape(base)}</rb>'
                f'<rp>(</rp><rt>{escape(reading)}</rt><rp>)</rp></ruby>'
            )
        if base:
            return escape(base)
        return escape(reading)

    @staticmethod
    def _block(title: str, body: str) -> str:
        if not body:
            return ''
        return f'<section><h3>{escape(title)}</h3>{body}</section>'

    @staticmethod
    def _body_block(body: str) -> str:
        if not body:
            return ''
        return f'<section>{body}</section>'

    @staticmethod
    def _book_id(seed: str) -> str:
        digest = hashlib.sha1(seed.encode('utf-8')).hexdigest()
        return f'urn:narou-py:{digest}'

    @staticmethod
    def _safe_filename(text: str) -> str:
        cleaned = re.sub(r'[\\/:*?"<>|]', '_', text or '')
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned or 'book'
