from __future__ import annotations

import argparse

from .aozora_exporter import AozoraEpubExporter, AozoraExportError
from .downloader import PyNarouDownloader, UnsupportedTarget
from .epub_exporter import EpubExportError, EpubExporter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='narou-py',
        description='Download novel and auto-export EPUB (narou/hameln).',
    )
    parser.add_argument('target', help='Novel URL from ncode.syosetu.com or syosetu.org')
    parser.add_argument(
        '--output',
        default='archive',
        help='Archive output root directory (default: archive)',
    )
    parser.add_argument(
        '--epub-output',
        help='Output epub file path (default: <novel_dir>/<title>.epub)',
    )
    parser.add_argument(
        '--no-aozora',
        action='store_true',
        help='Use built-in epub packer instead of AozoraEpub3-rs',
    )
    parser.add_argument(
        '--aozora',
        nargs='?',
        const='auto',
        metavar='PATH',
        help='Use AozoraEpub3-rs exporter; optional PATH to project root or executable',
    )
    parser.add_argument(
        '--subject',
        action='append',
        default=[],
        help='Add dc:subject metadata (repeatable)',
    )
    parser.add_argument(
        '--no-skip-existing',
        action='store_true',
        help='Do not skip existing downloaded chapters',
    )
    parser.add_argument(
        '--title',
        help='Override novel title completely (archive name/toc/EPUB metadata/cover title)',
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        downloader = PyNarouDownloader(args.target, output_root=args.output, custom_title=args.title)
        novel_dir = downloader.download(skip_existing=not args.no_skip_existing)
        use_aozora = bool(args.aozora) and not args.no_aozora
        if use_aozora:
            aozora_path = None if args.aozora == 'auto' else args.aozora
            exporter = AozoraEpubExporter(novel_dir, aozora=aozora_path)
        else:
            exporter = EpubExporter(novel_dir)
        epub_path = exporter.export(args.epub_output, subjects=args.subject)
    except (UnsupportedTarget, EpubExportError, AozoraExportError) as exc:
        print(str(exc))
        return 2
    print(epub_path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
