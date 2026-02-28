import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from narou_py.aozora_exporter import AozoraEpubExporter
from narou_py.epub_exporter import EpubExporter


class AozoraExporterTest(unittest.TestCase):
    def _make_archive(self, root: Path) -> None:
        section_dir = root / '本文'
        section_dir.mkdir(parents=True, exist_ok=True)
        (root / 'toc.json').write_text(
            json.dumps(
                {
                    'title': 'テスト作品',
                    'author': '作者A',
                    'toc_url': 'https://ncode.syosetu.com/n0001aa/',
                    'story': 'これは<br>あらすじ',
                    'subtitles': [{'index': '1', 'subtitle': '第一話'}],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding='utf-8',
        )
        (section_dir / '1 第一話.json').write_text(
            json.dumps(
                {
                    'index': '1',
                    'subtitle': '第一話',
                    'chapter': '第一章',
                    'element': {'introduction': '前書き', 'body': '本文', 'postscript': '後書き'},
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding='utf-8',
        )

    def test_export_invokes_aozora_rs_binary_without_rebuild(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'novel'
            root.mkdir(parents=True, exist_ok=True)
            self._make_archive(root)
            rs_root = Path(tmp) / 'AozoraEpub3-rs'
            rs_bin = rs_root / 'target' / 'release' / 'aozoraepub3-rs'
            rs_bin.parent.mkdir(parents=True, exist_ok=True)
            rs_bin.write_bytes(b'fake-binary')
            output_path = root / 'custom.epub'

            def fake_run(command, **kwargs):
                self.assertEqual(Path(command[0]).resolve(), rs_bin.resolve())
                self.assertIn('--enc', command)
                self.assertIn('-d', command)
                dst_index = command.index('-d')
                out_dir = Path(command[dst_index + 1])
                with zipfile.ZipFile(out_dir / 'generated.epub', 'w') as zf:
                    zf.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
                    zf.writestr('item/standard.opf', '<package><metadata></metadata></package>')
                return subprocess.CompletedProcess(command, 0, stdout='変換完了', stderr='')

            with (
                patch('narou_py.aozora_exporter.subprocess.run', side_effect=fake_run) as mocked,
                patch.object(AozoraEpubExporter, '_resolve_aozora_rs_root', return_value=rs_root),
            ):
                exporter = AozoraEpubExporter(root)
                result = exporter.export(output_path)

            self.assertEqual(result, output_path)
            self.assertTrue(output_path.exists())
            self.assertEqual(mocked.call_count, 1)

    def test_export_builds_aozora_rs_when_release_binary_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'novel'
            root.mkdir(parents=True, exist_ok=True)
            self._make_archive(root)
            rs_root = Path(tmp) / 'AozoraEpub3-rs'
            rs_root.mkdir(parents=True, exist_ok=True)
            rs_bin = rs_root / 'target' / 'release' / 'aozoraepub3-rs'
            output_path = root / 'custom.epub'

            def fake_run(command, **kwargs):
                if Path(command[0]).name == 'cargo':
                    self.assertEqual(command[1:], ['build', '--release'])
                    self.assertEqual(Path(kwargs['cwd']).resolve(), rs_root.resolve())
                    rs_bin.parent.mkdir(parents=True, exist_ok=True)
                    rs_bin.write_bytes(b'fake-binary')
                    return subprocess.CompletedProcess(command, 0, stdout='build ok', stderr='')

                self.assertEqual(Path(command[0]).resolve(), rs_bin.resolve())
                self.assertIn('--enc', command)
                self.assertIn('-d', command)
                dst_index = command.index('-d')
                out_dir = Path(command[dst_index + 1])
                with zipfile.ZipFile(out_dir / 'generated.epub', 'w') as zf:
                    zf.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
                    zf.writestr('item/standard.opf', '<package><metadata></metadata></package>')
                return subprocess.CompletedProcess(command, 0, stdout='変換完了', stderr='')

            with (
                patch('narou_py.aozora_exporter.subprocess.run', side_effect=fake_run) as mocked,
                patch.object(AozoraEpubExporter, '_resolve_aozora_rs_root', return_value=rs_root),
            ):
                exporter = AozoraEpubExporter(root)
                result = exporter.export(output_path)

            self.assertEqual(result, output_path)
            self.assertTrue(output_path.exists())
            self.assertEqual(mocked.call_count, 2)

    def test_add_dc_subject_to_generated_epub(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'novel'
            root.mkdir(parents=True, exist_ok=True)
            self._make_archive(root)
            epub_path = EpubExporter(root).export()

            AozoraEpubExporter._add_dc_subject_to_epub(epub_path, ['fantasy', 'test'])
            with zipfile.ZipFile(epub_path, 'r') as zf:
                opf = zf.read('item/standard.opf').decode('utf-8')
            self.assertIn('<dc:subject>fantasy</dc:subject>', opf)
            self.assertIn('<dc:subject>test</dc:subject>', opf)

    def test_write_aozora_input_text_appends_end_of_book_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'novel'
            root.mkdir(parents=True, exist_ok=True)
            self._make_archive(root)

            exporter = AozoraEpubExporter(root)
            toc = exporter._load_toc()
            sections = exporter._load_sections()
            txt_path = exporter._write_aozora_input_text(toc, sections, root)
            text = txt_path.read_text(encoding='utf-8')

            marker = '［＃ここから地付き］［＃小書き］（本を読み終わりました）［＃小書き終わり］［＃ここで地付き終わり］'
            self.assertEqual(text.rstrip('\n').split('\n')[-1], marker)
            self.assertIn('\n\n' + marker + '\n', text)

    def test_digits_to_kanji_converts_hankaku_and_zenkaku(self):
        converted = AozoraEpubExporter._digits_to_kanji('123４５６abc７８９0')
        self.assertEqual(converted, '一二三四五六abc七八九〇')

    def test_pack_blank_lines_keeps_only_long_blank_runs(self):
        text = '一行目\n\n二行目\n\n\n三行目\n　\n\n四行目\n*****\n\n\n五行目\n'
        packed = AozoraEpubExporter._pack_blank_lines(text)
        expected = '一行目\n二行目\n\n三行目\n\n四行目\n\n　　　　＊＊＊＊＊\n\n\n五行目'
        self.assertEqual(packed, expected)


if __name__ == '__main__':
    unittest.main()
