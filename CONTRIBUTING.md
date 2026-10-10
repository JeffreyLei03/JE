# 贡献指南 (Contributing to Je)

感谢你关注并参与 **Je** 的开发！Je 不仅是一个高效实用的终端 AI 编码助理，也是一个现代智能体工程架构的范例代码库。所有贡献都应遵循这一核心理念：**在拓展功能的同时，始终保持代码库模块清晰、架构精简且易于理解。**

---

## 项目架构与设计哲学 (Project Philosophy)

Je 由三个清晰解耦的分层构建：

```text
je_ai      大模型流式调用与协议转换层
je_agent   核心 Agent 调度引擎、事件循环、工具与会话抽象
je_coding  终端应用环境、CLI/TUI、文件与命令工具、技能与扩展
```

核心原则约束：

```text
AgentHarness  = 通用 Agent 大脑
CodingSession = 面向实际工程的编码助理环境
TUI / CLI     = 前端消费层
```

1. **小而精的模块胜于过度封装**：每个包的边界必须单一且明确。
2. **事件流即唯一契约**：Agent 引擎只抛出类型化事件，UI 与渲染层只负责订阅消费。
3. **内核保持完全可移植**：`je_agent` 绝不允许反向依赖 CLI、Textual、Rich 或特定的磁盘文件组织。
4. **工具是纯粹的强类型函数**：采用明确的 JSON Schema 和结构化返回结果。
5. **会话持久化透明可溯**：会话以 Append-Only JSONL 格式存储，保障中断恢复与分支历史追溯。

---

## 本地开发指南 (Local Development)

统一使用 [`uv`](https://docs.astral.sh/uv/) 管理虚拟环境：

```bash
# 1. 安装开发依赖
uv sync --dev

# 2. 验证版本
uv run je --version

# 3. 运行交互式终端或 Print 模式
uv run je
uv run je -p "解释这个工程的架构"
```

如果需要将当前源码直接作为全局命令调试，可以安装为可编辑全局工具：

```bash
uv tool install --editable --force .
je --version
```

---

## 提交前代码质量检查 (Checks Before Submitting)

在提交 Pull Request 前，请确保通过以下静态检查和自动化测试：

```bash
# 运行类型检查
uv run mypy

# 运行代码规范检查
uv run ruff check .

# 检查代码格式
uv run ruff format --check .

# 运行自动化测试套件
uv run pytest
```

---

## 提交信息规范 (Commit Guidelines)

请遵循 Conventional Commits 提交格式：

- `feat:` 新增功能
- `fix:` 缺陷修复
- `refactor:` 代码重构（不改变外部行为）
- `docs:` 文档更新
- `test:` 测试用例补充
- `chore:` 构建或辅助工具调整
