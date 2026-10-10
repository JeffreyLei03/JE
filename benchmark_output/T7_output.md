已完成。脚本位于 `scripts/repo_health_check.py`，并已通过 ruff、ruff format 和 mypy 检查。

## 设计要点

**跨平台**
- 只用标准库，无第三方依赖。
- 通过 `shutil.which("git")` / `shutil.which("uv")` 定位可执行文件，规避 Windows 与 Linux 的路径/扩展名差异。
- 所有子进程使用 `subprocess.run(command_list, shell=False)`，避免 shell 差异（`pwsh` / `bash` 行为一致）。
- 路径输出统一用 `/` 分隔符。

**6 项检查**（结果汇聚为结构化 JSON）
1. `python`：`sys.version_info >= (3, 12)`
2. `git_available`：`git --version`
3. `uv_available`：`uv --version`
4. `git_clean`：`git status --porcelain --untracked-files=normal`，列出未提交/未追踪条目
5. `large_files`：`os.walk` 扫描超过阈值的文件（默认 5 MiB），输出相对路径与字节/MiB 大小，默认跳过 `.git`、`.venv`、`node_modules`、各类缓存等
6. `ruff`：优先用 PATH 上的 `ruff`，否则用 `uv run ruff`，以 `--output-format json` 捕获返回码与诊断总数

**退出码**：仅当全部 6 项通过时返回 `0`，否则 `1`。

## 使用方式

```bash
python scripts/repo_health_check.py
uv run python scripts/repo_health_check.py --max-size-mb 10 --timeout 180 --root .
```

输出示例（节选）：

```json
{
  "project_root": "D:\\projects\\JE",
  "passed": false,
  "summary": { "total": 6, "passed": 3, "failed": 3 },
  "checks": {
    "python": { "passed": true, "message": "Python 3.12.14 satisfies >= 3.12", "details": { ... } },
    "git_clean": { "passed": false, "message": "working tree has 38 ...", "details": { "entries": [...] } },
    "large_files": { "passed": false, "message": "21 file(s) exceed 5 MiB", "details": { "files": [...] } },
    "ruff": { "passed": false, "message": "ruff check exit code 1 (...)", "details": { "returncode": 1, "error_count": 31 } }
  }
}
```

几点说明：
- 当前对真实仓库运行的结果为 `passed: false`（工作区有未提交文件、`desktop/release` 下有大构建产物、ruff 有 31 个告警），这属于真实状态，非脚本缺陷。
- 大文件扫描默认排除构建/缓存目录；若企业仓库需要把 `release/` 也纳入，可以再缩短 `DEFAULT_EXCLUDES`，或我加一个 `--include-dir` 选项来覆盖。需要的话我可以补。
