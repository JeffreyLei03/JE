已完成。新增测试文件 `tests/test_edit_tool_block_operations.py`（15 个用例全部通过，ruff lint/format 通过）。

## 覆盖内容

**1. 正常单次替换**
- `test_single_replacement_updates_file_and_reports_details`：替换后校验文件内容、`result.text`、`details["edits"]`、`first_changed_line` 与 diff。
- `test_single_replacement_respects_internal_whitespace`：确认缩进/行尾空格必须精确匹配。

**2. 未找到目标 → 报错且原文未变**
- `test_missing_target_raises_and_leaves_file_unchanged`：断言 `ToolInputError` 匹配 `Could not find the exact text`，并比对 `read_text` 与 `read_bytes` 完全一致。
- `test_missing_second_edit_rolls_back_and_leaves_file_unchanged`：多编辑中第二个失败时整体回滚。

**3. 歧义多匹配 → 拒绝修改**
- `test_ambiguous_match_is_rejected_and_file_is_unchanged`：`Found 2 occurrences` + 原文/字节未变。
- `test_ambiguous_multiple_edits_reports_occurrence_count`：多编辑场景下报 `Found 3 occurrences of edits[0]`。

**4. CRLF / LF 混杂规范化**
- LF 文件 + CRLF `oldText`、CRLF 文件 + LF `oldText`、跨 CRLF/LF 边界的 mixed 文件匹配及主导行尾恢复。
- `test_crlf_normalization_does_not_loosen_uniqueness`：规范化不会绕过唯一性检查。
- 直接对纯函数 `normalize_to_lf` / `detect_line_ending` / `restore_line_endings` 的单元测试（平台无关）。

**5. tmp_path 隔离**
- 所有用例使用 `tmp_path` fixture；另有相邻文件不受影响、嵌套相对路径解析后仍位于 `tmp_path` 内的断言。

## 需要说明的发现
测试过程中发现一个平台相关的实际行为差异：工具用 `path.write_text(...)` 写回，而 Windows 上 `Path.write_text` 会把 `\n` 转成 `\r\n`，因此**在 Windows 上 LF 文件编辑后落盘会变成 CRLF**（尽管 `read_text()` 读回仍是 LF，逻辑内容正确）。这与工具 docstring 声称的“恢复原始主导行尾”在 LF 场景下不完全一致。因此 LF 用例采用“规范化后的字节比较”以保持跨平台可执行，并在注释中记录原因。我未改动工具实现，如需修复（例如写回时使用 `newline=""`）请告知。

另：`tests/test_coding_tools.py::test_bash_tool_cancellation_kills_shell_children` 在 Windows 上失败，属于既有的、与本次改动无关的 bash 取消测试。
