from __future__ import annotations

import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape

from .aozora.text_converter_mixin import AozoraTextConverterMixin
from .epub_exporter import EpubExportError, EpubExporter
from .parser import strip_html


class AozoraExportError(EpubExportError):
    pass


class AozoraEpubExporter(AozoraTextConverterMixin, EpubExporter):
    def __init__(self, novel_dir: str | Path, *, aozora_jar: str | Path | None = None) -> None:
        super().__init__(novel_dir)
        self.aozora_jar = Path(aozora_jar).expanduser() if aozora_jar else None

    def export(self, output_path: str | Path | None = None, *, subjects: list[str] | None = None) -> Path:
        toc = self._load_toc()
        sections = self._load_sections()
        if not sections:
            raise AozoraExportError(f'no sections found: {self.section_dir}')
        target_path = Path(output_path) if output_path else self.novel_dir / f'{self._safe_filename(toc["title"])}.epub'
        target_path.parent.mkdir(parents=True, exist_ok=True)

        aozora_jar = self._resolve_aozora_jar()
        java_bin = shutil.which('java')
        if not java_bin:
            raise AozoraExportError('java not found in PATH')

        txt_path = self._write_aozora_input_text(toc, sections, target_path.parent)
        before = {path.resolve(): path.stat().st_mtime_ns for path in target_path.parent.glob('*.epub')}
        command = [
            java_bin,
            '-Dfile.encoding=UTF-8',
            '-Dstdout.encoding=UTF-8',
            '-Dstderr.encoding=UTF-8',
            '-Dsun.stdout.encoding=UTF-8',
            '-Dsun.stderr.encoding=UTF-8',
            '-cp',
            aozora_jar.name,
            'AozoraEpub3',
            '-enc',
            'UTF-8',
            '-of',
            '-dst',
            str(target_path.parent.resolve()),
            str(txt_path.resolve()),
        ]
        try:
            result = subprocess.run(
                command,
                cwd=str(aozora_jar.parent.resolve()),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                check=False,
            )
        finally:
            txt_path.unlink(missing_ok=True)
        if result.returncode != 0:
            raise AozoraExportError(
                f'AozoraEpub3 failed (exit={result.returncode}): {result.stdout.strip()} {result.stderr.strip()}'.strip()
            )
        produced = self._detect_generated_epub(target_path.parent, before)
        if produced.resolve() != target_path.resolve():
            produced.replace(target_path)
        if subjects:
            self._add_dc_subject_to_epub(target_path, subjects)
        return target_path

    def _resolve_aozora_jar(self) -> Path:
        candidates: list[Path] = []
        if self.aozora_jar:
            candidates.append(self.aozora_jar)
        env_jar = os.environ.get('NAROU_PY_AOZORAEPUB3_JAR') or os.environ.get('AOZORAEPUB3_JAR')
        if env_jar:
            candidates.append(Path(env_jar).expanduser())
        repo_root = Path(__file__).resolve().parents[1]
        projects_root = Path(__file__).resolve().parents[2]
        candidates.extend(
            [
                repo_root / 'AozoraEpub3.jar',
                projects_root / 'AozoraEpub3' / 'out' / 'AozoraEpub3.jar',
                projects_root / 'AozoraEpub3' / 'AozoraEpub3.jar',
            ]
        )
        candidates.extend((projects_root / 'AozoraEpub3' / 'out').glob('AozoraEpub3*.jar'))
        for candidate in candidates:
            path = candidate.expanduser().resolve()
            if path.exists() and path.is_file():
                return path
        raise AozoraExportError(
            'AozoraEpub3.jar not found; use --aozora-jar or set NAROU_PY_AOZORAEPUB3_JAR'
        )

    def _write_aozora_input_text(self, toc: dict, sections: list[dict], output_dir: Path) -> Path:
        lines: list[str] = []
        title = self._to_plain_text(str(toc.get('title', '')))
        author = self._to_plain_text(str(toc.get('author', '')))
        story = self._convert_html_fragment_to_aozora(str(toc.get('story', '')), text_type='story')
        toc_url = self._normalize_toc_url(self._to_plain_text(str(toc.get('toc_url', ''))))

        lines.append(title)
        lines.append(author)
        cover_chuki = self._create_cover_chuki()
        lines.append(cover_chuki)
        lines.append('［＃区切り線］')
        if story:
            lines.append('あらすじ：')
            lines.append(story)
            lines.append('')
        if toc_url:
            lines.append('掲載ページ:')
            lines.append(f'<a href="{toc_url}">{toc_url}</a>')
        lines.append('［＃区切り線］')
        lines.append('')
        previous_chapter = ''
        for section in sections:
            chapter = self._convert_html_fragment_to_aozora(section.get('chapter', ''), text_type='chapter').strip()
            subtitle = self._convert_html_fragment_to_aozora(section.get('subtitle', ''), text_type='subtitle').strip()
            intro = self._convert_html_fragment_to_aozora(section.get('introduction', ''), text_type='introduction')
            body = self._convert_html_fragment_to_aozora(section.get('body', ''), text_type='body')
            postscript = self._convert_html_fragment_to_aozora(section.get('postscript', ''), text_type='postscript')
            lines.append('［＃改ページ］')
            chapter_changed = bool(chapter) and chapter != previous_chapter
            if not chapter_changed:
                lines.append('')
            if chapter_changed:
                lines.append('［＃ページの左右中央］')
                lines.append(f'［＃ここから柱］{title}［＃ここで柱終わり］')
                lines.append(f'［＃３字下げ］［＃大見出し］{chapter}［＃大見出し終わり］')
                lines.append('［＃改ページ］')
                lines.append('')
            if chapter:
                previous_chapter = chapter
            if subtitle:
                lines.append(f'［＃３字下げ］［＃中見出し］{subtitle}［＃中見出し終わり］')
                if not intro:
                    lines.append('')
                    lines.append('')
            if intro:
                lines.append('［＃ここから前書き］')
                lines.append(intro)
                lines.append('［＃ここで前書き終わり］')
                lines.append('')
                lines.append('')
            if body:
                lines.append(body)
            if postscript:
                lines.append('［＃ここから後書き］')
                lines.append(postscript)
                lines.append('［＃ここで後書き終わり］')
        lines.append('')
        lines.append('［＃ここから地付き］［＃小書き］（本を読み終わりました）［＃小書き終わり］［＃ここで地付き終わり］')
        filename = f'{self._safe_filename(title or "book")}.aozora.txt'
        path = output_dir / filename
        path.write_text('\n'.join(lines).strip() + '\n', encoding='utf-8')
        return path

    def _to_plain_text(self, value: str) -> str:
        return strip_html(str(value or '')).strip()

    @staticmethod
    def _normalize_toc_url(url: str) -> str:
        if not url:
            return ''
        parsed = urlparse(url)
        if parsed.netloc == 'ncode.syosetu.com':
            return f'https://novel18.syosetu.com{parsed.path}'
        return url

    def _create_cover_chuki(self) -> str:
        # Keep parity with narou.rb default output text (cover chuki is usually not emitted).
        return ''

    @staticmethod
    def _detect_generated_epub(output_dir: Path, before: dict[Path, int]) -> Path:
        candidates: list[Path] = []
        for path in output_dir.glob('*.epub'):
            resolved = path.resolve()
            mtime = path.stat().st_mtime_ns
            if resolved not in before or mtime > before[resolved]:
                candidates.append(path)
        if not candidates:
            raise AozoraExportError(f'no generated epub found in {output_dir}')
        return max(candidates, key=lambda path: path.stat().st_mtime_ns)

    @staticmethod
    def _add_dc_subject_to_epub(epub_path: Path, subjects: list[str]) -> None:
        normalized = [s.strip() for s in subjects if s and s.strip()]
        if not normalized:
            return
        with zipfile.ZipFile(epub_path, 'r') as zf:
            entries = {name: zf.read(name) for name in zf.namelist()}
        opf_name = next((name for name in entries if name.endswith('standard.opf')), None)
        if not opf_name:
            raise AozoraExportError('standard.opf not found in generated epub')
        opf = entries[opf_name].decode('utf-8')
        opf = re.sub(r'\s*<dc:subject>.*?</dc:subject>', '', opf, flags=re.DOTALL)
        subject_xml = ''.join(f'\n    <dc:subject>{escape(subject)}</dc:subject>' for subject in normalized)
        opf = re.sub(r'</metadata>', f'{subject_xml}\n  </metadata>', opf, count=1)
        entries[opf_name] = opf.encode('utf-8')

        with zipfile.ZipFile(epub_path, 'w') as zf:
            zf.writestr('mimetype', entries['mimetype'], compress_type=zipfile.ZIP_STORED)
            for name, payload in entries.items():
                if name == 'mimetype':
                    continue
                zf.writestr(name, payload)
