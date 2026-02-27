# Aozora Export Maintenance Agent Guide

本文件记录 `narou-py` 中 Aozora 导出逻辑的拆分结构，以及与 `narou.rb` 的映射关系，便于后续维护时快速定位与回归。

## 1. 代码组织（拆分后）

- `narou_py/aozora_exporter.py`
  - 角色：导出编排层（orchestrator）
  - 负责：
    - 解析 toc/sections 并拼装整本 `.aozora.txt`
    - 定位并调用 `AozoraEpub3.jar`
    - 处理生成 epub 的检测与重命名
    - 写入 `dc:subject`
  - 不负责：具体文本转换细节（已下沉到 mixin）

- `narou_py/aozora/text_converter_mixin.py`
  - 角色：文本转换层（converter pipeline）
  - 负责：
    - HTML -> 青空文库文本转换
    - ルビ、縦中横、数字、英文保留、URL 保留/重建
    - 句読点/省略号规则
    - 区切り記号前后空行压缩规则
    - `text_type` 维度的差异处理（story/subtitle/chapter/body/introduction/postscript）

- `narou_py/aozora/__init__.py`
  - 包标记文件。

## 2. 与 narou.rb 的主要映射

以下映射用于“行为对齐”时快速对照：

- `narou/lib/converterbase.rb`
  - `symbols_to_zenkaku` -> `AozoraTextConverterMixin._symbols_to_zenkaku`
  - `convert_numbers` / `hankaku_num_to_zenkaku_num` / `exception_reconvert_kanji_to_num`
    -> `_convert_numbers` / `_hankaku_num_to_zenkaku_num` / `_exception_reconvert_kanji_to_num`
  - `insert_separate_space` -> `_insert_separate_space`
  - `convert_tatechuyoko` -> `_convert_tatechuyoko`
  - `convert_novel_rule` -> `_convert_novel_rule`
  - `convert_horizontal_ellipsis` -> `_convert_horizontal_ellipsis`
  - `convert_double_angle_quotation_to_gaiji` -> `_convert_double_angle_quotation_to_gaiji`
  - `replace_tatesen` -> `_replace_tatesen`
  - `auto_join_line` -> `_auto_join_line`
  - `half_indent_bracket` -> `_half_indent_bracket`
  - `insert_blank_line_to_border_symbol` + `enable_pack_blank_line` 系列行为
    -> `_normalize_border_line` + `_pack_blank_lines`

- `narou/lib/novelconverter.rb`（文本拼装层行为）
  - 各 section/chapter/subtitle 的输出顺序和分页规则
    -> `AozoraEpubExporter._write_aozora_input_text`

## 3. 维护约束（重要）

- 转换链路的调用顺序是行为敏感项，不要随意调整顺序。
- `text_type` 分支（尤其 `story` 与 `body`）是高风险点，修改时必须做双样本回归。
- 空行压缩 `_pack_blank_lines` 为经验化对齐规则，任何改动都必须跑全文 diff 回归。

## 4. 标准回归流程

### 4.1 单元测试

```bash
python3 -m unittest discover -s tests -v
```

### 4.2 原版文本一致性回归（必跑）

```bash
python3 - <<'PY'
from pathlib import Path
import difflib
from narou_py.aozora_exporter import AozoraEpubExporter

checks=[
('n3638hn',Path('archive/小説家になろう/n3638hn 拳聖・聖女もの'),Path('/Users/antimony/projects/narou/小説データ/ノクターンノベルズ/n3638hn 拳聖・聖女もの/[つれつれつれ] 拳聖・聖女もの.txt')),
('n7820gz',Path('archive/小説家になろう/n7820gz 出来過ぎるクールな妹に見下されてると思ったら実は俺にべた惚れだったようです'),Path('/Users/antimony/projects/narou/小説データ/ノクターンノベルズ/n7820gz 出来過ぎるクールな妹に見下されてると思ったら実は俺にべた惚れだったようです/[車馬超] 出来過ぎるクールな妹に見下されてると思ったら実は俺にべた惚れだったようです.txt')),
]
for code,novel_dir,ref in checks:
    exporter=AozoraEpubExporter(novel_dir)
    out=exporter._write_aozora_input_text(exporter._load_toc(), exporter._load_sections(), novel_dir)
    a=ref.read_text(encoding='utf-8').splitlines()
    b=out.read_text(encoding='utf-8').splitlines()
    ops=[op for op in difflib.SequenceMatcher(a=a,b=b).get_opcodes() if op[0] != 'equal']
    print(code, 'diff_hunks=', len(ops))
PY
```

目标：`n3638hn` 与 `n7820gz` 均 `diff_hunks=0`。
