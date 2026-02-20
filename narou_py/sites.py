from __future__ import annotations

import re

from .models import SiteConfig


NAROU = SiteConfig(
    key='narou',
    name='小説家になろう',
    top_url='https://ncode.syosetu.com',
    url_patterns=(
        r'https?://ncode\.syosetu\.com/(?P<ncode>n\d+[a-z]+)/?$',
        r'https?://novel18\.syosetu\.com/(?P<ncode>n\d+[a-z]+)/?$',
        r'https?://noc\.syosetu\.com/(?P<ncode>n\d+[a-z]+)/?$',
        r'https?://mnlt\.syosetu\.com/(?P<ncode>n\d+[a-z]+)/?$',
        r'https?://mid\.syosetu\.com/(?P<ncode>n\d+[a-z]+)/?$',
        r'https?://nl\.syosetu\.com/(?P<ncode>n\d+[a-z]+)/?$',
    ),
    toc_url_template='https://ncode.syosetu.com/{ncode}/',
    subtitles_pattern=(
        r'(?:<div class="p-eplist__chapter-title">(?P<chapter>.+?)</div>\s*)?'
        r'<div class="p-eplist__sublist">\s*'
        r'<a href="(?P<href>/.+?/(?P<index>\d+?)/)" class="p-eplist__subtitle">\s*'
        r'(?P<subtitle>.+?)\s*</a>'
    ),
    body_pattern=r'<div class="js-novel-text p-novel__text">\s*(?P<body>.+?)\s*</div>',
    introduction_pattern=(
        r'<div class="js-novel-text p-novel__text p-novel__text--preface">\s*'
        r'(?P<introduction>.+?)\s*</div>'
    ),
    postscript_pattern=(
        r'<div class="js-novel-text p-novel__text p-novel__text--afterword">\s*'
        r'(?P<postscript>.+?)\s*</div>'
    ),
    title_pattern=r'<h1 class="p-infotop-title">\s*<a href=".+?">(?P<title>.+?)</a>\s*</h1>',
    author_pattern=r'<dt class="p-infotop-data__title">作者名</dt>\s*<dd class="p-infotop-data__value">(?:<a href=".+?">)?(?P<author>.+?)(?:</a>)?.?</dd>',
    story_pattern=r'<dt class="p-infotop-data__title">あらすじ</dt>\s*<dd class="p-infotop-data__value">(?P<story>.+?)</dd>',
    novel_info_url_template='https://ncode.syosetu.com/novelview/infotop/ncode/{ncode}/',
    encoding='utf-8',
    cookie='over18=yes',
)


HAMELN = SiteConfig(
    key='hameln',
    name='ハーメルン',
    top_url='https://syosetu.org',
    url_patterns=(
        r'https?://syosetu\.org/novel/(?P<ncode>\d+)/?$',
        r'https?://novel\.syosetu\.org/(?P<ncode>\d+)/?$',
    ),
    toc_url_template='https://syosetu.org/novel/{ncode}/',
    subtitles_pattern=(
        r'(?:<tr><td colspan=2><strong>(?P<chapter>.+?)</strong></td></tr>)?'
        r'<tr bgcolor="#.+?" class="bgcolor\d"><td width=60%><span id="(?P<index>\d+?)">　</span>'
        r'\s*<a href=(?P<href>.+?) style="text-decoration:none;">(?P<subtitle>.+?)</a></td><td><NOBR>'
        r'(?:<time itemprop=".+?" datetime=".+?">)?(?P<subdate>.+?)(?:</time>)?'
        r'(?:<span title="(?P<subupdate>.+?)改稿">\(<u>改</u>\)</span>)?</NOBR></td></tr>'
    ),
    href_template='{index}.html',
    body_pattern=(
        r'<span style="font-size:120%">.+?</span><BR><BR>\s*'
        r'(?P<body>.+?)(?:<div id="atogaki"><br><hr><br>(?P<postscript>.+?)</div>)?'
    ),
    introduction_pattern=r'<div id="maegaki">(?P<introduction>.+?)<br><hr><br></div><',
    postscript_pattern=None,
    title_pattern=r'タイトル</td><td.*?><a href=.+?>(?P<title>.+?)</a>',
    author_pattern=r'作者</td><td.*?>(?:<a href=.+?>)?(?P<author>.+?)(?:</a>)?</td>',
    story_pattern=r'あらすじ</td><td.*?>(?P<story>.+?)</td>',
    novel_info_url_template='https://syosetu.org/?mode=ss_detail&nid={ncode}',
    encoding='utf-8',
    cookie='over18=off',
)

KAKUYOMU = SiteConfig(
    key='kakuyomu',
    name='カクヨム',
    top_url='https://kakuyomu.jp',
    url_patterns=(r'https?://kakuyomu\.jp/works/(?P<ncode>\d+)/?$',),
    toc_url_template='https://kakuyomu.jp/works/{ncode}',
    subtitles_pattern=(
        r'^Episode;(?P<index>\d+);(?P<subupdate>.+?);(?P<subtitle>.+?)$'
    ),
    body_pattern=r'<div class="widget-episodeBody js-episode-body"[^>]*>\s*(?P<body>.+?)\s*</div>',
    introduction_pattern=None,
    postscript_pattern=None,
    title_pattern=r'<title[^>]*>(?P<title>.+?)</title>',
    author_pattern=r'<meta name="author" content="(?P<author>.+?)"',
    story_pattern=r'<meta property="og:description" content="(?P<story>.+?)"',
    novel_info_url_template='https://kakuyomu.jp/works/{ncode}',
    encoding='utf-8',
)

AKATSUKI = SiteConfig(
    key='akatsuki',
    name='暁',
    top_url='https://www.akatsuki-novels.com',
    url_patterns=(r'https?://www\.akatsuki-novels\.com/stories/index/novel_id~(?P<ncode>\d+)/?$',),
    toc_url_template='https://www.akatsuki-novels.com/stories/index/novel_id~{ncode}',
    subtitles_pattern=(
        r'(?:<tr><td style="border: 0; padding: 0;word-break:break-all;" colspan="2"><b>(?P<chapter>.+?)</b></td></tr>)*'
        r'<tr><td>(?:  )?<a href="(?P<href>/stories/view/(?P<index>\d+)/novel_id\~\d+)">(?P<subtitle>.+?)</a> </td>'
        r'<td class="font-s">(?P<subupdate>.+?) </td></tr>'
    ),
    body_pattern=(
        r'</h2>(?:<div>&nbsp;</div><div><b>前書き</b></div><div class="body-novel">(?P<introduction>.+?)&nbsp;</div>'
        r'<hr width="100%"><div>&nbsp;</div>)?<div class="body-novel">(?P<body>.+?)&nbsp;</div>'
        r'(?:<div>&nbsp;</div><hr width="100%"><div>&nbsp;</div><div><b>後書き</b></div>'
        r'<div class="body-novel">(?P<postscript>.+?)&nbsp;</div>)?'
    ),
    introduction_pattern=None,
    postscript_pattern=None,
    title_pattern=r'id="LookNovel">(?P<title>.+?)</a>',
    author_pattern=r'作者：<a href="/users/view/\d+">(?P<author>.+?)</a>',
    story_pattern=r'<div class=" body-x1 body-normal body-w\d+">.+?<div>(?P<story>.+?)</div>',
    encoding='utf-8',
    cookie='CakeCookie[ALLOWED_ADULT_NOVEL]=on',
)

ARCADIA = SiteConfig(
    key='arcadia',
    name='Arcadia',
    top_url='http://www.mai-net.net',
    url_patterns=(
        r'https?://www\.mai-net\.net/bbs/sst/sst\.php\?act=dump&cate=(?P<category>[^&]*)&all=(?P<ncode>\d+).*$',
        r'https?://www\.mai-net\.net/bbs/sst/sst\.php\?act=dump&cate=&all=(?P<ncode>\d+).*$',
    ),
    toc_url_template='http://www.mai-net.net/bbs/sst/sst.php?act=dump&cate=&all={ncode}&n=0&count=1',
    subtitles_pattern=(
        r'<td width="0%" style="font-size:60%">\[(?P<index>\d+?)\]</td>'
        r'<td width="0%" style="font-size:60%"><b>\s*'
        r'<a href="(?P<href>.+?)#kiji">(?P<subtitle>.+?)</a></b></td>'
        r'<td width="0%" style="font-size:60%">\[(.+?)\]</td>'
        r'<td width="0%" style="font-size:60%">\((?P<subupdate>.+?)\)</td>'
    ),
    body_pattern=r'<blockquote><div style="line-height:1.5">(?P<body>.+?)</div></blockquote>',
    introduction_pattern=None,
    postscript_pattern=None,
    title_pattern=r'<font size=4 color=4444aa>(?P<title>.+?)</font>',
    author_pattern=r'<tt>Name: (?:(?P<author>.+?)◆.+</tt>|(?P<author2>.+?) </tt>)',
    story_pattern=r'(?P<story>)',
    encoding='utf-8',
)

SUPPORTED_SITES: tuple[SiteConfig, ...] = (
    NAROU,
    HAMELN,
    KAKUYOMU,
    AKATSUKI,
    ARCADIA,
)


def detect_site(target: str) -> tuple[SiteConfig, str] | None:
    raw = target.strip()
    # ncode shorthand input (e.g. n7820gz) defaults to narou.
    if re.match(r'^n\d+[a-z]+$', raw, re.IGNORECASE):
        return NAROU, raw.lower()
    for site in SUPPORTED_SITES:
        for pattern in site.url_patterns:
            match = re.match(pattern, raw, re.IGNORECASE)
            if match:
                ncode = match.group('ncode').lower()
                return site, ncode
    return None
