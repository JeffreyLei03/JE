# Je ⚡

> **运行在终端中的新一代自主 AI 编码智能体 (Autonomous Terminal Coding Agent)**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Package Manager: uv](https://img.shields.io/badge/PackageManager-uv-purple.svg)](https://docs.astral.sh/uv/)

Je 是一个面向专业开发者、轻量且高度可扩展的终端 AI 编程助手。只需输入自然语言需求（例如 *“解释这个模块的实现”*、*“为这个函数补充单元测试”* 或 *“重构这个模块的异步边界”*），Je 便能自主检索工程文件、规划变更方案、精准编辑源码、执行终端命令并持续流式展示执行过程，同时将完整的会话历史安全持久化在本地。

---

## 🏗 核心架构设计 (Architecture)

Je 秉承**极简、高内聚、低耦合**的工程哲学，严格遵循三层分层解耦架构：

```mermaid
flowchart TD
    subgraph UI[前端交互层 Presentation Layer]
        TUI["Textual TUI (富交互界面)"]
        CLI["Print Mode (命令行无头模式)"]
    end

    subgraph Coding[je_coding 工程适配环境]
        Session["CodingSession (编码会话)"]
        Tools["CodingTools (read / write / edit / bash)"]
        Context["ContextLoader (AGENTS.md / .je/skills)"]
    end

    subgraph Core[je_agent 可复用核心大脑]
        Harness["AgentHarness (调度线束引擎)"]
        Loop["AgentLoop (ReAct 自治推理主循环)"]
        Tree["SessionTree (不可变/只追加树状存储)"]
    end

    subgraph AI[je_ai 统一模型通信层]
        Provider["ProviderAdapter (适配 OpenAI / Claude / Ollama)"]
        Stream["EventStream (统一异步流式分发)"]
    end

    UI -->|订阅事件流 / 发送输入| Coding
    Coding -->|组装工具与工程上下文| Core
    Core -->|调度模型并驱动自治循环| AI
```

| 分层命名 | 核心定位 | 主要职责与边界 |
| :--- | :--- | :--- |
| **`je_ai`** | 统一大模型通信层 | 封装异构大模型协议（OpenAI、Anthropic、Ollama、DeepSeek、Hugging Face 等），将其转换为与厂商中立的标准异步事件流（Event Stream）。不含任何 Agent 业务逻辑。 |
| **`je_agent`** | 通用 Agent 调度引擎 | 整个智能体的核心大脑：包含自主推理执行循环（ReAct Loop）、工具调用编排、状态机流转、不可变消息模型及树状持久化存储。**完全独立于 UI 和文件系统**，可作为纯 Python 库嵌入任意后端或应用。 |
| **`je_coding`** | 终端编码助理环境 | 完整的终端落地应用：集成面向本地工程的实用工具集、工作区规则感知（`.je/`、`AGENTS.md`、Skills 技能包）、Textual 现代化交互 TUI 及命令行无头输出模式。 |

---

## 💡 核心亮点设计 (Key Highlights)

### 1. 纯事件驱动的主脑架构 (Pure Event-Driven Agent)
`je_agent` 不直接依赖任何渲染代码（不依赖 Rich、不依赖 Textual）。Agent 内部执行流（思考、工具调用、模型回复、错误捕获）均以**强类型事件流 (`AgentEvent`)** 的形式向上抛出。前端无论是 Textual TUI、Web 前端还是 CLI 脚本，只需简单消费事件即可无缝渲染，实现了 UI 与核心逻辑的彻底解耦。

### 2. 只追加树状会话持久化 (Append-Only Tree Session)
会话记录不是简单的平面聊天日志，而是基于 **JSONL 的只追加树状历史存储 (Tree-structured History)**：
- **零破坏性存储**：每一次提问、回答与工具执行均作为不可变节点按需追加，永不重写已有文件。
- **自由分叉与时光倒流**：支持像 Git 分支一样从任意历史节点派生新对话分支，会话恢复（`/resume`）绝对无损。

### 3. 高精度原子化文件编辑系统 (Atomic Precision Editing)
专为代码修改设计的智能编辑工具链：
- **唯一性锚定 (`edit`)**：严格要求定位文本具有唯一上下文特征，杜绝模糊匹配改错代码。
- **原子化执行与自动回滚**：编辑操作在内存缓冲中执行校验，任意异常即刻回滚，确保本地工作区源码绝不处于中间破坏状态。

### 4. 开放无绑定的模型中立性 (Vendor-Neutral Provider)
底层统一抽象了大模型调用规范，开箱支持：
- **新一代及旗舰大模型**：DeepSeek 全系列（V3/R1、`deepseek-v4-flash`、`deepseek-v4-pro`）、OpenAI（GPT-4o、GPT-5/6 系列、Codex 专版）、Claude（Sonnet 4/Opus 5 系列）、Kimi（K2.7-Code/K3）、GLM-5 等。
- **任意兼容规范接口**：任何兼容 OpenAI `/chat/completions` 或 `/v1/responses` 协议的提供商（Together、Fireworks、Vercel AI Gateway、OpenCode 等）。
- **本地私有化推理**：通过 Ollama 或 vLLM 驱动本地开源模型，完全离线亦可自主编码。

### 5. 极速轻量与即插即用 (Zero-Bloat Engineering)
抛弃沉重的重型框架（如 LangChain、AutoGPT 等重构层级），基于纯原生 Python 3.12 异步高并发特性构建，依赖极简、启动毫秒级、内存占用极低。

---

## 🚀 快速上手 (Quickstart)

### 前置环境

- **Python 3.12+**
- 推荐使用现代 Python 包管理器 [**`uv`**](https://docs.astral.sh/uv/)

### 源码安装与运行

```bash
# 1. 克隆仓库
git clone git@github.com:JeffreyLei03/JE.git
cd JE

# 2. 安装项目依赖与开发环境
uv sync --dev

# 3. 验证安装
uv run je --version
# 输出: je 0.1.0
```

### 两种运行模式

#### 1. 交互式终端模式 (TUI)
启动全功能、支持主题和键盘快捷键的 Textual 终端界面：
```bash
uv run je
```

#### 2. 命令行单次执行模式 (Print Mode)
无需进入交互界面，适用于脚本化调用或快速提问：
```bash
uv run je -p "总结当前代码库的核心架构"
uv run je --cwd /path/to/project -p "定位 CLI 入口文件"
```

#### 3. 安装为全局命令
将当前开发版本安装为系统的全局命令工具：
```bash
uv tool install --editable .
je --help
```

---

## 🛠 核心功能特性 (Features)

- **现代终端交互界面 (TUI)**：基于 Textual 构建，支持快捷键导航、多主题切换（`je-dark` / `je-light` / 高对比度）、流式打字机效果及实时进度看板。
- **全功能内置工具集**：
  - `read`：高效读取文本与多模态图片文件（JPEG、PNG、GIF、WebP），超大文件自动智能截断与续读提示。
  - `write`：原子化全量写入或新建文件，自动处理缺失父目录。
  - `edit`：高精度局部块替换，具备严格的唯一性校验与原子回滚机制。
  - `bash`：在当前工作区安全执行终端命令，实时捕获输出并支持超时熔断。
- **只追加树状会话持久化**：所有交互记录保存在 `~/.je/sessions/`，以 JSONL 树状结构存储，支持会话无损恢复（`/resume`）与历史分支分叉。
- **工程上下文规则注入**：自动识别工作区中的 `AGENTS.md`、`.je/skills/` 技能及 `.je/SYSTEM.md` 系统提示词。
- **多模型与本地生态支持**：无缝对接 OpenAI、Anthropic、Ollama 本地大模型、DeepSeek 以及任何兼容 OpenAI 规范的 API 接口。

---

## 📦 作为独立 Python 库调用 (Library Usage)

得益于 `je_agent` 核心引擎的无 UI 依赖设计，你可以在自己的脚本或独立应用中直接嵌入 Je 的智能体大脑：

```python
import asyncio
from je_ai.openai_compatible import OpenAICompatibleProvider, OpenAICompatibleConfig
from je_agent import AgentHarness, AgentHarnessConfig
from je_coding.tools import create_coding_tools

async def main():
    # 配置模型提供商
    provider = OpenAICompatibleProvider(
        OpenAICompatibleConfig(
            api_key="your-api-key",
            base_url="https://api.deepseek.com/v1",
        )
    )
    
    # 构建智能体大脑
    harness = AgentHarness(
        AgentHarnessConfig(
            provider=provider,
            model="deepseek-chat",
            system="你是一名资深的自主软件架构师。",
            tools=create_coding_tools(cwd="."),
        )
    )

    # 订阅事件流并输出
    async for event in harness.prompt("分析当前目录下的核心文件"):
        if event.type == "message_delta":
            print(event.delta, end="", flush=True)

asyncio.run(main())
```

---

## 🧪 自动化测试与质量保障 (Verification)

本项目包含完善的自动化测试套件与代码规范检查：

```bash
# 运行单元测试
uv run pytest

# 静态代码规范检查
uv run ruff check .

# 检查代码格式
uv run ruff format --check .

# 严格类型检查
uv run mypy
```

---

## 🛡 开发流程规范 (Development Workflow)

本项目遵循严格的工业级工程规范：

- **主分支保护 (Branch Protection)**：`main` 分支作为唯一的生产发布分支，受到受控保护，禁止强制推送与直接变更。
- **分支开发模式**：所有新特性与缺陷修复均基于功能分支开发（`feat/*`、`fix/*`）。
- **持续集成门禁 (CI Pipeline)**：通过 GitHub Actions 自动化门禁检测，所有 PR 必须在通过 `pytest`、`ruff` 和 `mypy` 校验后方可合并。

---

## 📄 开源许可证与致谢 (License & Acknowledgments)

本项目基于 [MIT 许可证](LICENSE) 开源。

**致谢声明 (Acknowledgments)**：
Je 的架构设计灵感来源于 Pi 与 Tau 极简智能体线束架构，并在其思想之上进行了深度本土化重构与工程演进。
