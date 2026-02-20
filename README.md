# narou-py

Standalone Python downloader for Narou-family and other major JP webnovel sites with automatic EPUB export.

## Scope

- Supported sites:
  - `https://ncode.syosetu.com/<ncode>/` and `https://novel18.syosetu.com/<ncode>/` (Narou family, unified handling; also accepts noc/mnlt/mid/nl domains)
  - `https://syosetu.org/novel/<id>/` (Hameln)
  - `https://kakuyomu.jp/works/<id>` (Kakuyomu)
  - `https://www.akatsuki-novels.com/stories/index/novel_id~<id>` (Akatsuki)
  - `https://www.mai-net.net/bbs/sst/sst.php?act=dump&cate=<cate>&all=<id>` (Arcadia)
- Implemented:
  - Target/site detection
  - TOC fetch + metadata extraction
  - Subtitle list parsing
  - Section download (introduction/body/postscript)
  - Local archive output

## Install

```bash
pip install -e .
```

## Run

```bash
narou-py "https://ncode.syosetu.com/n1234ab/"
```

or

```bash
narou-py "https://syosetu.org/novel/123456/"
```

or

```bash
narou-py "https://kakuyomu.jp/works/1177354054880000000"
```

Default behavior:
- Check existing downloaded chapters under `本文/*.json`
- Skip chapters already downloaded
- Download only missing chapters
- Auto export EPUB after download
- If `cover.jpg` / `cover.png` / `cover.jpeg` exists in novel directory, embed it as EPUB cover

Add `dc:subject` metadata or force re-download all chapters:

```bash
narou-py "https://ncode.syosetu.com/n1234ab/" --subject fantasy --subject isekai
narou-py "https://ncode.syosetu.com/n1234ab/" --no-skip-existing
narou-py "https://syosetu.org/novel/307058/" --title "生意気な義妹が引きこもりになったので優しくしたら激甘ブラコン化した話"
```

Output layout is now aligned to AozoraEpub3-style package paths:
- `META-INF/container.xml` -> `item/standard.opf`
- `item/nav.xhtml`
- `item/toc.ncx`
- `item/xhtml/*.xhtml`
- `item/style/book-style.css`

## Test

```bash
python3 -m unittest discover -s tests -v
```

## Acknowledgements

- [Rumia-Channel/narou](https://github.com/Rumia-Channel/narou)
- [kyukyunyorituryo/AozoraEpub3](https://github.com/kyukyunyorituryo/AozoraEpub3)
