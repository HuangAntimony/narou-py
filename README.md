# narou-py

Python downloader for major JP webnovel platforms with automatic EPUB export.

## Supported Sites

- `https://ncode.syosetu.com/<ncode>/`
- `https://novel18.syosetu.com/<ncode>/` (also `noc/mnlt/mid/nl.syosetu.com`)
- `https://syosetu.org/novel/<id>/` (Hameln)
- `https://kakuyomu.jp/works/<id>` (Kakuyomu)
- `https://www.akatsuki-novels.com/stories/index/novel_id~<id>` (Akatsuki)
- `https://www.mai-net.net/bbs/sst/sst.php?act=dump&cate=<cate>&all=<id>` (Arcadia)

## Run Directly

No install is required in this repository workflow. Run directly:

```bash
python3 -m narou_py "<novel-url>"
```

Optional (if you want command entry points in your environment):

```bash
python3 -m pip install -e .
```

## Basic Usage

```bash
python3 -m narou_py "https://ncode.syosetu.com/n1234ab/"
python3 -m narou_py "https://syosetu.org/novel/123456/"
python3 -m narou_py "https://kakuyomu.jp/works/1177354054880000000"
```

## Useful Flags

- `--no-skip-existing`: re-download all chapters
- `--subject <tag>`: add EPUB `dc:subject` (repeatable)
- `--title "<custom title>"`: fully override original title for archive name, `toc.json`, EPUB metadata, and cover title
- `--output <dir>`: archive root (default: `archive`)
- `--epub-output <file>`: output EPUB path

Examples:

```bash
python3 -m narou_py "https://ncode.syosetu.com/n1234ab/" --subject fantasy --subject isekai
python3 -m narou_py "https://ncode.syosetu.com/n1234ab/" --no-skip-existing
python3 -m narou_py "https://syosetu.org/novel/307058/" --title "生意気な義妹が引きこもりになったので優しくしたら激甘ブラコン化した話"
```

## Output Notes

- Chapters are stored under `本文/*.json`
- Existing non-empty chapters are skipped by default
- EPUB is exported automatically after download
- If `cover.jpg/png/jpeg` exists in novel directory, it is used as cover
- If no cover file exists, `cover.png` is auto-generated

EPUB package paths:

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
