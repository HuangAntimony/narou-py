import json
import tempfile
import unittest
from pathlib import Path

from narou_py.downloader import PyNarouDownloader
from narou_py.sites import detect_site


NAROU_TOC = '''
<h1 class="p-infotop-title"><a href="/foo">テストタイトル</a></h1>
<dt class="p-infotop-data__title">作者名</dt><dd class="p-infotop-data__value">作者A</dd>
<dt class="p-infotop-data__title">あらすじ</dt><dd class="p-infotop-data__value">これは<br>あらすじ</dd>
<div class="p-eplist__sublist">
<a href="/n1234ab/1/" class="p-eplist__subtitle">第一話</a>
</div>
'''

NAROU_BODY = '''
<div class="js-novel-text p-novel__text p-novel__text--preface">前書き</div>
<div class="js-novel-text p-novel__text">本文です</div>
<div class="js-novel-text p-novel__text p-novel__text--afterword">後書き</div>
'''

NAROU_TOC_P1 = '''
<h1 class="p-infotop-title"><a href="/foo">テストタイトル</a></h1>
<dt class="p-infotop-data__title">作者名</dt><dd class="p-infotop-data__value">作者A</dd>
<dt class="p-infotop-data__title">あらすじ</dt><dd class="p-infotop-data__value">これは<br>あらすじ</dd>
<div class="p-eplist__chapter-title">第一章</div>
<div class="p-eplist__sublist"><a href="/n1234ab/1/" class="p-eplist__subtitle">第一話</a></div>
<a href="/n1234ab/?p=2" class="c-pager__item c-pager__item--last">2</a>
'''

NAROU_TOC_P2 = '''
<div class="p-eplist__sublist"><a href="/n1234ab/2/" class="p-eplist__subtitle">第二話</a></div>
'''

HAMELN_TOC = '''
タイトル</td><td><a href="/novel/123456/">ハーメルン作品</a>
作者</td><td>作者B</td>
あらすじ</td><td>説明文</td>
<tr bgcolor="#fff" class="bgcolor1"><td width=60%><span id="1">　</span>
 <a href=./1.html style="text-decoration:none;">一話</a></td><td><NOBR>2024/01/01</NOBR></td></tr>
'''

HAMELN_BODY = '''
<div id="maegaki">前書き<br><hr><br></div><
<span style="font-size:120%">題</span><BR><BR>本文です<div id="atogaki"><br><hr><br>後書き</div>
'''

HAMELN_BODY_FALLBACK = '''
<html><body>
<div id="maegaki">前書き</div>
<div id="honbun">これは<ruby>本文<rt>ほんぶん</rt></ruby>です。</div>
<div id="atogaki">後書き</div>
</body></html>
'''

HAMELN_BODY_WITH_NAV_TAIL = '''
<span style="font-size:120%">題</span><BR><BR>
これは本文です。<br>
×<br>
目 次<br>
次の話 &gt;&gt;<br>
目次<br>
小説情報<br>
縦書き<br>
しおりを挟む<br>
お気に入り登録<br>
評価<br>
感想<br>
'''

HAMELN_BODY_WITH_NEXTPAGE_NAV = '''
<span style="font-size:120%">題</span><BR><BR>
これは第一章の本文です。</p><p id="184">　</p><p id="185">　</p></div>


</div>
<span id="analytics_end"></span>
<span id="n_vid" data-vid="2955150"></span>

<div class="ss">

<div id="nextpage" class="novelnavi" style="margin-top:15px;">
<ul class="nl">
<li class="novelnb"><a href="#">×</a></li>
<li class="novelmokuzi"><a href="./">目次</a></li>
</ul>
</div>
'''

NAROU_INFO = '''
<h1 class="p-infotop-title"><a href="/foo">情報ページタイトル</a></h1>
<dt class="p-infotop-data__title">作者名</dt><dd class="p-infotop-data__value">作者A</dd>
<dt class="p-infotop-data__title">あらすじ</dt><dd class="p-infotop-data__value">情報あらすじ</dd>
'''

NAROU_R18_TOC = '''
<h1 class="p-infotop-title"><a href="/foo">R18タイトル</a></h1>
<dt class="p-infotop-data__title">作者名</dt><dd class="p-infotop-data__value">作者R</dd>
<dt class="p-infotop-data__title">あらすじ</dt><dd class="p-infotop-data__value">R18あらすじ</dd>
<div class="p-eplist__sublist">
<a href="/n7777aa/1/" class="p-eplist__subtitle">第一夜</a>
</div>
'''

NAROU_R18_TOC_P1 = '''
<h1 class="p-infotop-title"><a href="/foo">R18連載</a></h1>
<dt class="p-infotop-data__title">作者名</dt><dd class="p-infotop-data__value">作者R</dd>
<dt class="p-infotop-data__title">あらすじ</dt><dd class="p-infotop-data__value">R18連載あらすじ</dd>
<div class="p-eplist__chapter-title">第一章</div>
<div class="p-eplist__sublist"><a href="/n7777aa/1/" class="p-eplist__subtitle">第一夜</a></div>
<a href="/n7777aa/?p=2" class="c-pager__item c-pager__item--last">2</a>
'''

NAROU_R18_TOC_P2 = '''
<div class="p-eplist__sublist"><a href="/n7777aa/2/" class="p-eplist__subtitle">第二夜</a></div>
'''

KAKUYOMU_TOC = '''
<script id="__NEXT_DATA__" type="application/json">{"props":{"pageProps":{"__APOLLO_STATE__":{"Work:1177354054880000000":{"title":"カクヨム作品","introduction":"概要1\\n概要2","author":{"__ref":"User:1"},"tableOfContents":[{"__ref":"TableOfContentsChapter:1"}]},"User:1":{"activityName":"作者K"},"TableOfContentsChapter:1":{"chapter":{"__ref":"Chapter:1"},"episodeUnions":[{"__ref":"Episode:1001"}]},"Chapter:1":{"title":"第一章"},"Episode:1001":{"__typename":"Episode","id":"1001","title":"一話","publishedAt":"2024-01-01T00:00:00Z"}}}},"query":{"workId":"1177354054880000000"}}</script>
'''

KAKUYOMU_BODY = '''
<div class="widget-episodeBody js-episode-body">これはカクヨム本文です。</div>
'''

AKATSUKI_TOC = '''
id="LookNovel">暁作品</a>
作者：<a href="/users/view/1">作者A</a>
<div class=" body-x1 body-normal body-w123">x<div>説明文</div>
<tr><td style="border: 0; padding: 0;word-break:break-all;" colspan="2"><b>第一章</b></td></tr>
<tr><td><a href="/stories/view/555/novel_id~999">第一話</a> </td><td class="font-s">2024年01月01日 </td></tr>
'''

AKATSUKI_BODY = '''
</h2><div class="body-novel">暁の本文です。&nbsp;</div>
'''

ARCADIA_TOC = '''
<font size=4 color=4444aa>Arcadia作品</font>
<tt>Name: 作者M </tt>
<td width="0%" style="font-size:60%">[1]</td><td width="0%" style="font-size:60%"><b>
<a href="/bbs/sst/sst.php?act=dump&cate=all&all=123&n=1#kiji">第一話</a></b></td><td width="0%" style="font-size:60%">[x]</td><td width="0%" style="font-size:60%">(2024/01/01)</td>
'''

ARCADIA_BODY = '''
<blockquote><div style="line-height:1.5">Arcadia本文です。</div></blockquote>
'''


class FakeDownloader(PyNarouDownloader):
    def __init__(
        self,
        target: str,
        html_map: dict[str, str],
        output_root: str | Path,
        *,
        custom_title: str | None = None,
    ) -> None:
        super().__init__(target, output_root=output_root, custom_title=custom_title)
        self._html_map = html_map

    def _fetch_text(self, url, site):  # noqa: ARG002
        return self._html_map[url]


class CoreTest(unittest.TestCase):
    def test_detect_site(self):
        detected = detect_site('https://ncode.syosetu.com/n1234ab/')
        self.assertIsNotNone(detected)
        detected = detect_site('https://syosetu.org/novel/123456/')
        self.assertIsNotNone(detected)
        detected = detect_site('n7820gz')
        self.assertIsNotNone(detected)
        self.assertEqual(detected[0].key, 'narou')
        self.assertEqual(detected[1], 'n7820gz')
        detected = detect_site('N7820GZ')
        self.assertIsNotNone(detected)
        self.assertEqual(detected[1], 'n7820gz')
        detected = detect_site('https://kakuyomu.jp/works/1177354054880000000')
        self.assertIsNotNone(detected)
        self.assertEqual(detected[0].key, 'kakuyomu')
        detected = detect_site('https://novel18.syosetu.com/n7777aa/')
        self.assertIsNotNone(detected)
        self.assertEqual(detected[0].key, 'narou')
        detected = detect_site('https://www.akatsuki-novels.com/stories/index/novel_id~999')
        self.assertIsNotNone(detected)
        self.assertEqual(detected[0].key, 'akatsuki')
        detected = detect_site('https://www.mai-net.net/bbs/sst/sst.php?act=dump&cate=all&all=123&n=0&count=1')
        self.assertIsNotNone(detected)
        self.assertEqual(detected[0].key, 'arcadia')

    def test_narou_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            html_map = {
                'https://ncode.syosetu.com/n1234ab/': NAROU_TOC,
                'https://ncode.syosetu.com/n1234ab/1/': NAROU_BODY,
            }
            downloader = FakeDownloader(
                'https://ncode.syosetu.com/n1234ab/',
                html_map,
                output_root=tmp,
            )
            output = downloader.download()
            self.assertTrue((output / 'toc.json').exists())
            section_dir = output / '本文'
            self.assertEqual(len(list(section_dir.glob('*.json'))), 1)

    def test_narou_toc_pagination(self):
        with tempfile.TemporaryDirectory() as tmp:
            html_map = {
                'https://ncode.syosetu.com/n1234ab/': NAROU_TOC_P1,
                'https://ncode.syosetu.com/n1234ab/?p=2': NAROU_TOC_P2,
                'https://ncode.syosetu.com/n1234ab/1/': NAROU_BODY,
                'https://ncode.syosetu.com/n1234ab/2/': NAROU_BODY,
            }
            downloader = FakeDownloader(
                'https://ncode.syosetu.com/n1234ab/',
                html_map,
                output_root=tmp,
            )
            output = downloader.download()
            sections = sorted((output / '本文').glob('*.json'))
            self.assertEqual(len(sections), 2)
            second = json.loads(sections[1].read_text(encoding='utf-8'))
            self.assertEqual(second['chapter'], '第一章')

    def test_hameln_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            html_map = {
                'https://syosetu.org/novel/123456/': HAMELN_TOC,
                'https://syosetu.org/novel/123456/1.html': HAMELN_BODY,
            }
            downloader = FakeDownloader(
                'https://syosetu.org/novel/123456/',
                html_map,
                output_root=tmp,
            )
            output = downloader.download()
            self.assertTrue((output / 'toc.json').exists())
            section_dir = output / '本文'
            self.assertEqual(len(list(section_dir.glob('*.json'))), 1)
            saved = next(section_dir.glob('*.json')).read_text(encoding='utf-8')
            self.assertIn('本文です', saved)

    def test_hameln_fallback_body_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            html_map = {
                'https://syosetu.org/novel/123456/': HAMELN_TOC,
                'https://syosetu.org/novel/123456/1.html': HAMELN_BODY_FALLBACK,
                'https://syosetu.org/?mode=ss_detail&nid=123456': HAMELN_TOC,
            }
            downloader = FakeDownloader(
                'https://syosetu.org/novel/123456/',
                html_map,
                output_root=tmp,
            )
            output = downloader.download()
            section = next((output / '本文').glob('*.json')).read_text(encoding='utf-8')
            self.assertIn('これは<ruby>本文<rt>ほんぶん</rt></ruby>です。', section)

    def test_hameln_navigation_tail_trim(self):
        with tempfile.TemporaryDirectory() as tmp:
            html_map = {
                'https://syosetu.org/novel/123456/': HAMELN_TOC,
                'https://syosetu.org/novel/123456/1.html': HAMELN_BODY_WITH_NAV_TAIL,
                'https://syosetu.org/?mode=ss_detail&nid=123456': HAMELN_TOC,
            }
            downloader = FakeDownloader(
                'https://syosetu.org/novel/123456/',
                html_map,
                output_root=tmp,
            )
            output = downloader.download()
            section = next((output / '本文').glob('*.json')).read_text(encoding='utf-8')
            self.assertIn('これは本文です。', section)
            self.assertNotIn('小説情報', section)
            self.assertNotIn('しおりを挟む', section)

    def test_hameln_nextpage_nav_hard_trim(self):
        with tempfile.TemporaryDirectory() as tmp:
            html_map = {
                'https://syosetu.org/novel/123456/': HAMELN_TOC,
                'https://syosetu.org/novel/123456/1.html': HAMELN_BODY_WITH_NEXTPAGE_NAV,
                'https://syosetu.org/?mode=ss_detail&nid=123456': HAMELN_TOC,
            }
            downloader = FakeDownloader(
                'https://syosetu.org/novel/123456/',
                html_map,
                output_root=tmp,
            )
            output = downloader.download()
            section = next((output / '本文').glob('*.json')).read_text(encoding='utf-8')
            self.assertIn('これは第一章の本文です。', section)
            self.assertNotIn('novelnavi', section)
            self.assertNotIn('analytics_end', section)
            self.assertNotIn('>×<', section)

    def test_skip_existing_sections(self):
        toc = '''
<h1 class="p-infotop-title"><a href="/foo">テストタイトル</a></h1>
<dt class="p-infotop-data__title">作者名</dt><dd class="p-infotop-data__value">作者A</dd>
<dt class="p-infotop-data__title">あらすじ</dt><dd class="p-infotop-data__value">説明</dd>
<div class="p-eplist__sublist"><a href="/n1234ab/1/" class="p-eplist__subtitle">第一話</a></div>
<div class="p-eplist__sublist"><a href="/n1234ab/2/" class="p-eplist__subtitle">第二話</a></div>
'''
        with tempfile.TemporaryDirectory() as tmp:
            html_map = {
                'https://ncode.syosetu.com/n1234ab/': toc,
                'https://ncode.syosetu.com/n1234ab/2/': NAROU_BODY,
            }
            downloader = FakeDownloader(
                'https://ncode.syosetu.com/n1234ab/',
                html_map,
                output_root=tmp,
            )
            output = downloader._novel_dir(downloader.fetch_novel())
            section_dir = output / '本文'
            section_dir.mkdir(parents=True, exist_ok=True)
            (section_dir / '1 第一話.json').write_text(
                json.dumps(
                    {
                        'index': '1',
                        'subtitle': '第一話',
                        'element': {'body': 'cached'},
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding='utf-8',
            )
            saved = downloader.download()
            self.assertEqual(saved, output)
            files = sorted(section_dir.glob('*.json'))
            self.assertEqual(len(files), 2)
            self.assertTrue((section_dir / '1 第一話.json').exists())

    def test_empty_existing_section_is_not_skipped(self):
        toc = '''
<h1 class="p-infotop-title"><a href="/foo">テストタイトル</a></h1>
<dt class="p-infotop-data__title">作者名</dt><dd class="p-infotop-data__value">作者A</dd>
<dt class="p-infotop-data__title">あらすじ</dt><dd class="p-infotop-data__value">説明</dd>
<div class="p-eplist__sublist"><a href="/n1234ab/1/" class="p-eplist__subtitle">第一話</a></div>
'''
        with tempfile.TemporaryDirectory() as tmp:
            html_map = {
                'https://ncode.syosetu.com/n1234ab/': toc,
                'https://ncode.syosetu.com/novelview/infotop/ncode/n1234ab/': NAROU_INFO,
                'https://ncode.syosetu.com/n1234ab/1/': NAROU_BODY,
            }
            downloader = FakeDownloader('n1234ab', html_map, output_root=tmp)
            output = downloader._novel_dir(downloader.fetch_novel())
            section_dir = output / '本文'
            section_dir.mkdir(parents=True, exist_ok=True)
            (section_dir / '1 第一話.json').write_text(
                json.dumps(
                    {'index': '1', 'subtitle': '第一話', 'element': {'body': '<'}},
                    ensure_ascii=False,
                ),
                encoding='utf-8',
            )
            downloader.download()
            saved = (section_dir / '1 第一話.json').read_text(encoding='utf-8')
            self.assertIn('本文です', saved)

    def test_title_fallback_from_info_page(self):
        toc = '''
<html><head><title>dummy - 小説家になろう</title></head>
<body><div class="p-eplist__sublist"><a href="/n7820gz/1/" class="p-eplist__subtitle">第一話</a></div></body>
</html>
'''
        with tempfile.TemporaryDirectory() as tmp:
            html_map = {
                'https://ncode.syosetu.com/n7820gz/': toc,
                'https://ncode.syosetu.com/novelview/infotop/ncode/n7820gz/': NAROU_INFO,
                'https://ncode.syosetu.com/n7820gz/1/': NAROU_BODY,
            }
            downloader = FakeDownloader('n7820gz', html_map, output_root=tmp)
            output = downloader.download()
            self.assertIn('情報ページタイトル', output.name)

    def test_narou_r18_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            html_map = {
                'https://novel18.syosetu.com/n7777aa/': NAROU_R18_TOC,
                'https://novel18.syosetu.com/n7777aa/1/': NAROU_BODY,
            }
            downloader = FakeDownloader(
                'https://novel18.syosetu.com/n7777aa/',
                html_map,
                output_root=tmp,
            )
            output = downloader.download()
            section_dir = output / '本文'
            self.assertEqual(len(list(section_dir.glob('*.json'))), 1)

    def test_narou_r18_toc_pagination(self):
        with tempfile.TemporaryDirectory() as tmp:
            html_map = {
                'https://novel18.syosetu.com/n7777aa/': NAROU_R18_TOC_P1,
                'https://novel18.syosetu.com/n7777aa/?p=2': NAROU_R18_TOC_P2,
                'https://novel18.syosetu.com/n7777aa/1/': NAROU_BODY,
                'https://novel18.syosetu.com/n7777aa/2/': NAROU_BODY,
            }
            downloader = FakeDownloader(
                'https://novel18.syosetu.com/n7777aa/',
                html_map,
                output_root=tmp,
            )
            output = downloader.download()
            sections = sorted((output / '本文').glob('*.json'))
            self.assertEqual(len(sections), 2)
            second = json.loads(sections[1].read_text(encoding='utf-8'))
            self.assertEqual(second['chapter'], '第一章')

    def test_kakuyomu_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            html_map = {
                'https://kakuyomu.jp/works/1177354054880000000': KAKUYOMU_TOC,
                'https://kakuyomu.jp/works/1177354054880000000/episodes/1001': KAKUYOMU_BODY,
            }
            downloader = FakeDownloader(
                'https://kakuyomu.jp/works/1177354054880000000',
                html_map,
                output_root=tmp,
            )
            output = downloader.download()
            section = next((output / '本文').glob('*.json')).read_text(encoding='utf-8')
            self.assertIn('これはカクヨム本文です。', section)
            toc = json.loads((output / 'toc.json').read_text(encoding='utf-8'))
            self.assertEqual(toc['author'], '作者K')
            self.assertEqual(toc['story'], '概要1<br>概要2')

    def test_akatsuki_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            html_map = {
                'https://www.akatsuki-novels.com/stories/index/novel_id~999': AKATSUKI_TOC,
                'https://www.akatsuki-novels.com/stories/view/555/novel_id~999': AKATSUKI_BODY,
            }
            downloader = FakeDownloader(
                'https://www.akatsuki-novels.com/stories/index/novel_id~999',
                html_map,
                output_root=tmp,
            )
            output = downloader.download()
            section = next((output / '本文').glob('*.json')).read_text(encoding='utf-8')
            self.assertIn('暁の本文です。', section)

    def test_arcadia_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            toc_url = 'https://www.mai-net.net/bbs/sst/sst.php?act=dump&cate=all&all=123&n=0&count=1'
            html_map = {
                toc_url: ARCADIA_TOC,
                'https://www.mai-net.net/bbs/sst/sst.php?act=dump&cate=all&all=123&n=1': ARCADIA_BODY,
            }
            downloader = FakeDownloader(
                toc_url,
                html_map,
                output_root=tmp,
            )
            output = downloader.download()
            section = next((output / '本文').glob('*.json')).read_text(encoding='utf-8')
            self.assertIn('Arcadia本文です。', section)

    def test_custom_title_override_replaces_original_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            html_map = {
                'https://ncode.syosetu.com/n1234ab/': NAROU_TOC,
                'https://ncode.syosetu.com/n1234ab/1/': NAROU_BODY,
            }
            downloader = FakeDownloader(
                'https://ncode.syosetu.com/n1234ab/',
                html_map,
                output_root=tmp,
                custom_title='純净标题',
            )
            output = downloader.download()
            self.assertTrue(output.name.endswith('純净标题'))
            toc = json.loads((output / 'toc.json').read_text(encoding='utf-8'))
            self.assertEqual(toc['title'], '純净标题')


if __name__ == '__main__':
    unittest.main()
