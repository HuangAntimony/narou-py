import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from narou_py.epub_exporter import EpubExporter


class EpubExporterTest(unittest.TestCase):
    def test_export_epub_from_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / '小説家になろう' / 'n0001aa テスト'
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
                        'element': {
                            'introduction': '前書き',
                            'body': '本文<br>です',
                            'postscript': '後書き',
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding='utf-8',
            )
            (section_dir / '10 第十話.json').write_text(
                json.dumps(
                    {
                        'index': '10',
                        'subtitle': '第十話',
                        'chapter': '第二章',
                        'element': {
                            'introduction': '',
                            'body': '十話本文',
                            'postscript': '',
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding='utf-8',
            )
            exporter = EpubExporter(root)
            epub_path = exporter.export(subjects=['fantasy', 'test'])
            self.assertTrue(epub_path.exists())

            with zipfile.ZipFile(epub_path, 'r') as zf:
                names = zf.namelist()
                self.assertEqual(names[0], 'mimetype')
                self.assertIn('META-INF/container.xml', names)
                self.assertIn('item/standard.opf', names)
                self.assertIn('item/toc.ncx', names)
                self.assertIn('item/nav.xhtml', names)
                self.assertIn('item/xhtml/title.xhtml', names)
                self.assertIn('item/xhtml/0001.xhtml', names)
                self.assertIn('item/xhtml/0002.xhtml', names)

                opf = zf.read('item/standard.opf').decode('utf-8')
                self.assertIn('<dc:title>テスト作品</dc:title>', opf)
                self.assertIn('<dc:creator id="creator01">作者A</dc:creator>', opf)
                self.assertIn('<dc:subject>fantasy</dc:subject>', opf)
                self.assertIn('<dc:subject>test</dc:subject>', opf)

                nav = zf.read('item/nav.xhtml').decode('utf-8')
                self.assertIn('第一章', nav)
                self.assertIn('第二章', nav)
                self.assertIn('<li class="chapter"><a href="xhtml/0001.xhtml">第一章</a><ol>', nav)
                self.assertIn('<li class="chapter"><a href="xhtml/0002.xhtml">第二章</a><ol>', nav)
                self.assertNotIn('<li class="chapter">第一章</li>', nav)
                self.assertNotIn('epub:type="toc" href="nav.xhtml"', nav)
                ET.fromstring(nav)

                ncx = zf.read('item/toc.ncx').decode('utf-8')
                self.assertIn('<content src="xhtml/0001.xhtml#sec-title-0001"/><navPoint', ncx)
                self.assertIn('<content src="xhtml/0002.xhtml"/></navPoint>', ncx)
                ET.fromstring(ncx)

                chapter = zf.read('item/xhtml/0001.xhtml').decode('utf-8')
                self.assertIn('<div class="block block-body">', chapter)
                self.assertNotIn('<section>', chapter)
                self.assertIn('<h1 id="sec-title-0001">第一話</h1>', chapter)

                title = zf.read('item/xhtml/title.xhtml').decode('utf-8')
                self.assertIn('<body class="p-titlepage">', title)

                css = zf.read('item/style/book-style.css').decode('utf-8')
                self.assertIn('.main{margin:0;padding:0;}', css)
                self.assertIn('p{text-indent:1em;margin:0;text-align:justify;}', css)

    def test_export_epub_with_cover_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / '小説家になろう' / 'n0002aa テスト'
            section_dir = root / '本文'
            section_dir.mkdir(parents=True, exist_ok=True)
            (root / 'toc.json').write_text(
                json.dumps(
                    {
                        'title': '表紙付き作品',
                        'author': '作者B',
                        'toc_url': 'https://ncode.syosetu.com/n0002aa/',
                        'story': 'あらすじ',
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
                        'chapter': '',
                        'element': {
                            'introduction': '',
                            'body': '本文',
                            'postscript': '',
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding='utf-8',
            )
            # 1x1 PNG
            (root / 'cover.png').write_bytes(
                b'\x89PNG\r\n\x1a\n'
                b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
                b'\x00\x00\x00\x0bIDATx\x9cc``\x00\x00\x00\x03\x00\x01h&Y\r'
                b'\x00\x00\x00\x00IEND\xaeB`\x82'
            )
            exporter = EpubExporter(root)
            epub_path = exporter.export()
            with zipfile.ZipFile(epub_path, 'r') as zf:
                names = zf.namelist()
                self.assertIn('item/image/cover.png', names)
                self.assertIn('item/xhtml/cover.xhtml', names)
                opf = zf.read('item/standard.opf').decode('utf-8')
                self.assertIn('id="cover-image"', opf)
                self.assertIn('<meta name="cover" content="cover-image"/>', opf)
                self.assertIn('idref="cover-page"', opf)
                nav = zf.read('item/nav.xhtml').decode('utf-8')
                self.assertIn('epub:type="cover"', nav)

    def test_ruby_text_keeps_base_and_reading(self):
        exporter = EpubExporter('/tmp/not-used')
        html_fragment = (
            '妹である'
            '<ruby><rb>皆賀美瑠</rb><rp>(</rp><rt>みながみる</rt><rp>)</rp></ruby>'
            'の笑み。'
            '<ruby>皆賀望<rp>(</rp><rt>みながのぞむ</rt><rp>)</rp></ruby>'
        )
        out = exporter._html_fragment_to_paragraphs(html_fragment)
        self.assertIn('<ruby><rb>皆賀美瑠</rb><rp>(</rp><rt>みながみる</rt><rp>)</rp></ruby>', out)
        self.assertIn('<ruby><rb>皆賀望</rb><rp>(</rp><rt>みながのぞむ</rt><rp>)</rp></ruby>', out)

    def test_export_epub_auto_generates_cover_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / '小説家になろう' / 'n0003aa テスト'
            section_dir = root / '本文'
            section_dir.mkdir(parents=True, exist_ok=True)
            (root / 'toc.json').write_text(
                json.dumps(
                    {
                        'title': '自動生成表紙作品',
                        'author': '作者C',
                        'toc_url': 'https://ncode.syosetu.com/n0003aa/',
                        'story': 'あらすじ',
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
                        'chapter': '',
                        'element': {'introduction': '', 'body': '本文', 'postscript': ''},
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding='utf-8',
            )
            exporter = EpubExporter(root)
            epub_path = exporter.export()
            with zipfile.ZipFile(epub_path, 'r') as zf:
                names = zf.namelist()
                self.assertIn('item/image/cover.png', names)
                self.assertIn('item/xhtml/cover.xhtml', names)
                opf = zf.read('item/standard.opf').decode('utf-8')
                self.assertIn('media-type="image/png"', opf)
                cover_xhtml = zf.read('item/xhtml/cover.xhtml').decode('utf-8')
                self.assertIn('../image/cover.png', cover_xhtml)


if __name__ == '__main__':
    unittest.main()
