import unittest
from pathlib import Path
from unittest.mock import patch

from narou_py import cli


class CliTest(unittest.TestCase):
    @patch('narou_py.cli.PyNarouDownloader')
    @patch('narou_py.cli.EpubExporter')
    @patch('narou_py.cli.AozoraEpubExporter')
    @patch('builtins.print')
    def test_default_uses_builtin_exporter(self, mocked_print, mocked_aozora, mocked_builtin, mocked_downloader):
        mocked_downloader.return_value.download.return_value = Path('/tmp/novel')
        mocked_builtin.return_value.export.return_value = Path('/tmp/novel/book.epub')

        with patch('sys.argv', ['narou-py', 'https://ncode.syosetu.com/n1234ab/']):
            exit_code = cli.main()

        self.assertEqual(exit_code, 0)
        mocked_builtin.assert_called_once()
        mocked_aozora.assert_not_called()
        mocked_print.assert_called_once()

    @patch('narou_py.cli.PyNarouDownloader')
    @patch('narou_py.cli.EpubExporter')
    @patch('narou_py.cli.AozoraEpubExporter')
    @patch('builtins.print')
    def test_aozora_used_when_path_is_given(self, mocked_print, mocked_aozora, mocked_builtin, mocked_downloader):
        mocked_downloader.return_value.download.return_value = Path('/tmp/novel')
        mocked_aozora.return_value.export.return_value = Path('/tmp/novel/book.epub')

        with patch(
            'sys.argv',
            ['narou-py', 'https://ncode.syosetu.com/n1234ab/', '--aozora', '/opt/AozoraEpub3-rs'],
        ):
            exit_code = cli.main()

        self.assertEqual(exit_code, 0)
        mocked_aozora.assert_called_once()
        mocked_builtin.assert_not_called()
        mocked_print.assert_called_once()


if __name__ == '__main__':
    unittest.main()
