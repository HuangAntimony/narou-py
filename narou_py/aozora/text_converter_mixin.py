from __future__ import annotations

import html
import re


class AozoraTextConverterMixin:
    @staticmethod
    def _delete_tag(text: str) -> str:
        previous = None
        while text != previous:
            previous = text
            text = re.sub(r'<.+?>', '', text, flags=re.DOTALL)
        return text

    def _html_to_aozora(self, value: str, *, pre_html: bool = False) -> str:
        if not value:
            return ''
        text = value
        if not pre_html:
            text = re.sub(r'[\r\n]+', '', text)
            text = re.sub(r'<br.*?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'\n?</p>', '\n', text, flags=re.IGNORECASE)

        def ruby_repl(match: re.Match[str]) -> str:
            ruby_inner = match.group(1)
            splited_ruby = re.split(r'<rt>', ruby_inner, flags=re.IGNORECASE)
            if len(splited_ruby) < 2:
                return self._delete_tag(splited_ruby[0])
            ruby_base = self._delete_tag(re.split(r'<rp>', splited_ruby[0], maxsplit=1, flags=re.IGNORECASE)[0])
            ruby_text = self._delete_tag(re.split(r'<rp>', splited_ruby[1], maxsplit=1, flags=re.IGNORECASE)[0])
            if re.fullmatch(r'[・、]+', ruby_text):
                return f'［＃傍点］{ruby_base}［＃傍点終わり］'
            return f'｜{ruby_base}《{ruby_text}》'

        text = re.sub(r'<ruby>(.+?)</ruby>', ruby_repl, text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<b>', '［＃太字］', text, flags=re.IGNORECASE)
        text = re.sub(r'</b>', '［＃太字終わり］', text, flags=re.IGNORECASE)
        text = re.sub(r'<i>', '［＃斜体］', text, flags=re.IGNORECASE)
        text = re.sub(r'</i>', '［＃斜体終わり］', text, flags=re.IGNORECASE)
        text = re.sub(r'<s>', '［＃取消線］', text, flags=re.IGNORECASE)
        text = re.sub(r'</s>', '［＃取消線終わり］', text, flags=re.IGNORECASE)

        def img_repl(match: re.Match[str]) -> str:
            src = match.group('src')
            return f'［＃挿絵（{src}）入る］'

        text = re.sub(r'<img.+?src=\"(?P<src>.+?)\".*?>', img_repl, text, flags=re.IGNORECASE)
        text = re.sub(r'<em class="emphasisDots">(.+?)</em>', r'［＃傍点］\1［＃傍点終わり］', text, flags=re.DOTALL)
        text = self._delete_tag(text)
        text = html.unescape(text)
        return text

    @staticmethod
    def _symbols_to_zenkaku(text: str) -> str:
        text = re.sub(r"[‘’']([^\"\n]+?)[‘’']", r'〝\1〟', text)
        text = re.sub(r'[“”〝〟"]([^"\n]+?)[“”〝〟"]', r'〝\1〟', text)
        text = text.translate(
            str.maketrans(
                "-=+/*《》'\"%$#&!?<>＜＞()|‐,._;:[]{}",
                "－＝＋／＊≪≫’〝％＄＃＆！？〈〉〈〉（）｜－，．＿；：［］｛｝",
            )
        )
        return text.replace('\\', '￥')

    @staticmethod
    def _hankakukana_to_zenkakukana(text: str) -> str:
        # Keep parity with narou.rb NKF conversion relevant for punctuation.
        return text.replace('－', '−').replace('—', '―')

    _KANJI_NUM = '〇一二三四五六七八九'
    _ZENKAKU_NUM = '０１２３４５６７８９'
    _ALPHABET_TABLE = str.maketrans(
        'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ',
        'ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ',
    )
    _KANJI_TO_ZENKAKU_DIGIT = str.maketrans(_KANJI_NUM, _ZENKAKU_NUM)
    _URL_SENTINEL_OPEN = '\uE000'
    _URL_SENTINEL_CLOSE = '\uE001'
    _URL_SENTINEL_BASE = 0xE100
    _ENGLISH_SENTINEL_OPEN = '\uE002'
    _ENGLISH_SENTINEL_CLOSE = '\uE003'
    _ENGLISH_SENTINEL_BASE = 0xE200
    _NUM_SENTINEL_OPEN = '\uE005'
    _NUM_SENTINEL_CLOSE = '\uE006'
    _NUM_SENTINEL_BASE = 0xE300
    _KOME_SENTINEL = '\uE004'

    @staticmethod
    def _alphabet_to_zenkaku(text: str) -> str:
        return text.translate(AozoraTextConverterMixin._ALPHABET_TABLE)

    @classmethod
    def _stash_urls(cls, text: str) -> tuple[str, list[str]]:
        urls: list[str] = []
        pattern = re.compile(r'https?://[A-Za-z0-9\-._~:/?#\[\]@!$&\'()*+,;=%]+')

        def repl(match: re.Match[str]) -> str:
            idx = len(urls)
            urls.append(match.group(0))
            return f'{cls._URL_SENTINEL_OPEN}{chr(cls._URL_SENTINEL_BASE + idx)}{cls._URL_SENTINEL_CLOSE}'

        return pattern.sub(repl, text), urls

    @classmethod
    def _rebuild_urls(cls, text: str, urls: list[str]) -> str:
        for idx, url in enumerate(urls):
            text = text.replace(
                f'{cls._URL_SENTINEL_OPEN}{chr(cls._URL_SENTINEL_BASE + idx)}{cls._URL_SENTINEL_CLOSE}',
                f'<a href="{url}">{url}</a>',
            )
        return text

    @classmethod
    def _stash_english_sentences(cls, text: str) -> tuple[str, list[str]]:
        english_sentences: list[str] = []
        pattern = re.compile(r"[A-Za-z0-9_.,!?\"' &:;-]+")

        def sentence_like(token: str) -> bool:
            return len([chunk for chunk in token.split(' ') if chunk]) >= 2

        def long_ascii_word(token: str) -> bool:
            return len(token) >= 8 and re.search(r'[A-Za-z]', token) is not None

        def repl(match: re.Match[str]) -> str:
            token = match.group(0)
            if sentence_like(token) or long_ascii_word(token):
                idx = len(english_sentences)
                english_sentences.append(token)
                return (
                    f'{cls._ENGLISH_SENTINEL_OPEN}'
                    f'{chr(cls._ENGLISH_SENTINEL_BASE + idx)}'
                    f'{cls._ENGLISH_SENTINEL_CLOSE}'
                )
            return cls._alphabet_to_zenkaku(token)

        return pattern.sub(repl, text), english_sentences

    @classmethod
    def _rebuild_english_sentences(cls, text: str, english_sentences: list[str]) -> str:
        for idx, sentence in enumerate(english_sentences):
            text = text.replace(
                f'{cls._ENGLISH_SENTINEL_OPEN}{chr(cls._ENGLISH_SENTINEL_BASE + idx)}{cls._ENGLISH_SENTINEL_CLOSE}',
                sentence,
            )
        return text

    @classmethod
    def _rebuild_hankaku_num_and_comma(cls, text: str, nums: list[str]) -> str:
        for idx, num in enumerate(nums):
            text = text.replace(
                f'{cls._NUM_SENTINEL_OPEN}{chr(cls._NUM_SENTINEL_BASE + idx)}{cls._NUM_SENTINEL_CLOSE}',
                num,
            )
        return text

    @classmethod
    def _stash_kome(cls, text: str) -> str:
        return text.replace('※', cls._KOME_SENTINEL)

    @classmethod
    def _rebuild_kome_to_gaiji(cls, text: str) -> str:
        return text.replace(cls._KOME_SENTINEL, '※［＃米印、1-2-8］')

    @classmethod
    def _hankaku_num_to_zenkaku_num(cls, text: str, *, text_type: str) -> str:
        def tcy(value: str) -> str:
            return f'［＃縦中横］{value}［＃縦中横終わり］'

        def repl(match: re.Match[str]) -> str:
            token = match.group(0)
            if len(token) == 2:
                return tcy(token)
            if len(token) == 3 and text_type == 'subtitle' and match.start() == 0:
                return tcy(token)
            return token.translate(str.maketrans('0123456789', cls._ZENKAKU_NUM))

        return re.sub(r'\d+', repl, text)

    @classmethod
    def _convert_numbers(cls, text: str, *, text_type: str) -> tuple[str, list[str]]:
        digit_class = f'\\d０-９{cls._KANJI_NUM}'
        num_and_comma: list[str] = []
        text = re.sub(
            rf'([{digit_class}]+?)[\.．]([{digit_class}]+?)',
            r'\1・\2',
            text,
        )
        if text_type in ('subtitle', 'chapter', 'story'):
            return cls._hankaku_num_to_zenkaku_num(text, text_type=text_type), num_and_comma

        def repl(match: re.Match[str]) -> str:
            token = match.group(0)
            if ',' in token or '，' in token:
                if re.search(r'\d', token):
                    idx = len(num_and_comma)
                    num_and_comma.append(token.replace('，', ','))
                    return f'{cls._NUM_SENTINEL_OPEN}{chr(cls._NUM_SENTINEL_BASE + idx)}{cls._NUM_SENTINEL_CLOSE}'
                return token
            return cls._digits_to_kanji(token)

        text = re.sub(r'[\d０-９,，]+', repl, text)
        return text, num_and_comma

    @classmethod
    def _exception_reconvert_kanji_to_num(cls, text: str) -> str:
        unit_chars = '％㎜㎝㎞㎎㎏㏄㎡㎥'

        def to_zenkaku_digits(token: str) -> str:
            return token.translate(cls._KANJI_TO_ZENKAKU_DIGIT)

        text = re.sub(
            rf'([Ａ-Ｚａ-ｚ])([{cls._KANJI_NUM}・～]+)',
            lambda m: m.group(1) + to_zenkaku_digits(m.group(2)),
            text,
        )
        text = re.sub(
            rf'([{cls._KANJI_NUM}・～]+)([Ａ-Ｚａ-ｚ{unit_chars}])',
            lambda m: to_zenkaku_digits(m.group(1)) + m.group(2),
            text,
        )
        return text

    @staticmethod
    def _insert_separate_space(text: str) -> str:
        close_chars = '」］｝] }』】〉》〕＞>≫)）"”’〟　☆★♪［―'

        def repl(match: re.Match[str]) -> str:
            m1, m2 = match.group(1), match.group(2)
            if m2 in (' ', '　', '、', '。'):
                m2 = '　'
            if m2 not in close_chars:
                return f'{m1}　{m2}'
            return f'{m1}{m2}'

        return re.sub(r'([!?！？]+)([^!?！？])', repl, text)

    @staticmethod
    def _convert_tatechuyoko(text: str) -> str:
        def tcy(value: str) -> str:
            return f'［＃縦中横］{value}［＃縦中横終わり］'

        def bang_repl(match: re.Match[str]) -> str:
            token = match.group(0)
            left = match.string[match.start() - 1] if match.start() > 0 else ''
            right = match.string[match.end()] if match.end() < len(match.string) else ''
            if left == '？' or right == '？':
                return token
            length = len(token)
            if length == 3:
                return tcy('!!!')
            if length >= 4:
                if length % 2 == 1:
                    length += 1
                return tcy('!!') * (length // 2)
            return token

        text = re.sub(r'！+', bang_repl, text)

        def mixed_repl(match: re.Match[str]) -> str:
            token = match.group(0)
            if len(token) == 2:
                return tcy(token.translate(str.maketrans('！？', '!?')))
            if len(token) == 3 and token in ('！！？', '？！！'):
                return tcy(token.translate(str.maketrans('！？', '!?')))
            return token

        return re.sub(r'[！？]+', mixed_repl, text)

    @staticmethod
    def _half_indent_bracket(text: str) -> str:
        pattern = re.compile(r'^[ 　\t]*((?:[〔「『(（【〈《≪〝])|(?:※［＃始め二重山括弧］))', re.MULTILINE)
        return pattern.sub(lambda m: f'［＃二分アキ］{m.group(1)}', text)

    @staticmethod
    def _normalize_border_line(line: str) -> str | None:
        stripped = line.strip(' 　\t')
        if not stripped:
            return None
        if re.fullmatch(r'[＊*]{5,}', stripped):
            return stripped.replace('*', '＊')
        if re.fullmatch(r'[◆◇■□●○★☆]+', stripped):
            return stripped
        return None

    @staticmethod
    def _pack_blank_lines(text: str) -> str:
        lines = text.split('\n')
        packed: list[str] = []
        blank_run = 0
        prev_border = False

        def append_blanks(count: int) -> None:
            for _ in range(count):
                if not packed or packed[-1] != '':
                    packed.append('')
                else:
                    packed.append('')

        for line in lines:
            if not line.strip(' 　\t'):
                blank_run += 1
                continue
            border = AozoraTextConverterMixin._normalize_border_line(line)
            if border is not None:
                if blank_run > 0:
                    append_blanks(1 if blank_run in (1, 3) else 2)
                elif packed and packed[-1] != '':
                    packed.append('')
                blank_run = 0
                packed.append('　' * 4 + border)
                prev_border = True
                continue
            if not packed and blank_run >= 1:
                packed.append('')
            elif prev_border and blank_run >= 1:
                append_blanks(1 if blank_run in (1, 3) else 2)
            elif blank_run >= 2 and packed[-1] != '':
                packed.append('')
                if blank_run >= 4:
                    packed.append('')
                if blank_run >= 8:
                    packed.append('')
                if blank_run >= 10:
                    packed.append('')
            blank_run = 0
            prev_border = False
            packed.append(line.rstrip(' 　\t'))
        while packed and packed[-1] == '':
            packed.pop()
        result = '\n'.join(packed)
        result = result.replace('\n！」', '！」')
        result = result.replace('\n？」', '？」')
        return result

    @staticmethod
    def _convert_horizontal_ellipsis(text: str) -> str:
        for char in ('・', '。', '、', '．'):
            pattern = re.compile(f'{re.escape(char)}' + r'{3,}')

            def repl(match: re.Match[str]) -> str:
                pre_char = match.string[match.start() - 1] if match.start() > 0 else ''
                post_char = match.string[match.end()] if match.end() < len(match.string) else ''
                if pre_char == '―' or post_char == '―':
                    return match.group(0)
                count = len(match.group(0))
                return '…' * (((count + 5) // 6) * 2)

            text = pattern.sub(repl, text)
        text = text.replace('。。', '。')
        text = text.replace('、、', '、')
        return text

    @staticmethod
    def _digits_to_kanji(text: str) -> str:
        return text.translate(str.maketrans('0123456789０１２３４５６７８９', '〇一二三四五六七八九〇一二三四五六七八九'))

    @staticmethod
    def _convert_novel_rule(text: str) -> str:
        text = re.sub(r'。([」』）])', r'\1', text)
        text = re.sub(r'[…]+', lambda m: m.group(0) if len(m.group(0)) % 2 == 0 else m.group(0) + '…', text)
        text = re.sub(r'[‥]+', lambda m: m.group(0) if len(m.group(0)) % 2 == 0 else m.group(0) + '‥', text)
        text = re.sub(r'。　', '。', text)
        return text

    @staticmethod
    def _convert_double_angle_quotation_to_gaiji(text: str) -> str:
        text = text.replace('≪', '※［＃始め二重山括弧］')
        text = text.replace('≫', '※［＃終わり二重山括弧］')
        return text

    @staticmethod
    def _restore_explicit_ruby(text: str) -> str:
        def repl(match: re.Match[str]) -> str:
            base = match.group(1)
            ruby = match.group(2)
            if re.fullmatch(r'[…‥。．、,\-]+', ruby):
                return match.group(0)
            return f'｜{base}《{ruby}》'

        return re.sub(r'｜([^｜≪≫\n]+)≪([^≪≫\n]+)≫', repl, text)

    @staticmethod
    def _replace_tatesen(text: str) -> str:
        text = re.sub(r'｜([^｜《》\n]+)《([^《》\n]+)》', r'［＃ルビ用縦線］\1《\2》', text)
        text = text.replace('｜', '※［＃縦線］')
        return text.replace('［＃ルビ用縦線］', '｜')

    @staticmethod
    def _auto_join_line(text: str) -> str:
        return re.sub(
            r'([^、])、\n(?:[ 　\t]*\n)*　([^「『(（【<＜〈《≪・■…‥―　１-９一-九])',
            r'\1、\2',
            text,
        )

    @staticmethod
    def _ensure_story_linebreaks(text: str) -> str:
        # toc.story is often already plain text with explicit newlines.
        if '<' not in text and '>' not in text:
            return text
        return text

    def _convert_html_fragment_to_aozora(self, value: str, *, text_type: str) -> str:
        if not value:
            return ''
        pre_html = text_type == 'story' and '<' not in value and '>' not in value
        text = self._html_to_aozora(value, pre_html=pre_html)
        text = self._hankakukana_to_zenkakukana(text)
        if text_type == 'story':
            text = self._ensure_story_linebreaks(text)
        text = self._auto_join_line(text)
        text = text.replace('【改ページ】', '')
        text = re.sub(r'<KBR>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<PBR>', '\n', text, flags=re.IGNORECASE)
        text, urls = self._stash_urls(text)
        text, english_sentences = self._stash_english_sentences(text)
        text = self._stash_kome(text)
        text = self._symbols_to_zenkaku(text)
        text, num_and_comma = self._convert_numbers(text, text_type=text_type)
        if text_type not in ('subtitle', 'chapter', 'story'):
            text = self._exception_reconvert_kanji_to_num(text)
        text = self._insert_separate_space(text)
        text = self._convert_tatechuyoko(text)
        text = self._convert_novel_rule(text)
        text = self._convert_horizontal_ellipsis(text)
        text = self._restore_explicit_ruby(text)
        text = self._replace_tatesen(text)
        text = self._convert_double_angle_quotation_to_gaiji(text)
        text = self._rebuild_english_sentences(text, english_sentences)
        text = self._rebuild_hankaku_num_and_comma(text, num_and_comma)
        text = self._rebuild_urls(text, urls)
        text = self._rebuild_kome_to_gaiji(text)
        text = re.sub('　{3,}', '　　', text)
        if text_type in ('body', 'textfile'):
            text = self._half_indent_bracket(text)
            text = self._pack_blank_lines(text)
            text = self._convert_tatechuyoko(text)
        elif text_type in ('introduction', 'postscript'):
            text = self._pack_blank_lines(text)
        text = re.sub(r'[ 　\t]+$', '', text, flags=re.MULTILINE)
        text = re.sub(r'[　\s]+\Z', '', text)
        return text
