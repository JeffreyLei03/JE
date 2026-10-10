"""JE Autonomous Agent 8-Dimensional Capability Benchmark Runner.

Runs 8 comprehensive capability assessment tests on JE configured with DeepSeek-V4-Pro.
Records outputs, tool executions, timing, and errors for systematic scoring and comparison.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Force UTF-8 stdout/stderr on Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BENCHMARK_TESTS = [
    {
        "id": "T1",
        "dimension": "代码语义理解与架构分析 (Codebase Comprehension & Architecture Analysis)",
        "title": "深入剖析 JE 三层解耦架构与事件流运行时",
        "prompt": (
            "深入分析当前 JE 项目的架构分层设计。请详细阐述：\n"
            "1. je_ai, je_agent, je_coding 这三层的具体职责、调用单向依赖关系与设计边界；\n"
            "2. je_agent 的核心推理主循环（ReAct Loop）是如何基于异步生成器（AsyncIterator[AgentEvent]）实现细粒度事件流驱动的；\n"
            "3. 树状持久化（SessionTree / JsonlSessionStorage）的实现原理及如何保证会话只追加与故障可恢复性。"
        ),
        "evaluation_criteria": {
            "completion": "涵盖三层架构职责与依赖边界、ReAct事件流机制、树状持久化只追加原理三部分",
            "accuracy": "技术术语准确，模块划分与源码一致（如je_ai不含业务逻辑，je_agent纯调度，je_coding承载CLI/TUI/Tools），无技术幻觉",
        },
    },
    {
        "id": "T2",
        "dimension": "跨模块精准检索与代码定位 (Cross-Module Code Navigation & Symbol Retrieval)",
        "title": "定位生命周期 Hook、取消级联与工作区信任机制实现",
        "prompt": (
            "在当前项目中进行精准代码定位并给出相对文件路径、函数名及关键代码行号范围：\n"
            "1. 定位工具调用生命周期 Hook（before_tool_call / after_tool_call）的类型定义与在 AgentLoop 中的触发调用点；\n"
            "2. 定位终端命令超时熔断与取消级联（CancellationToken / run_process_interruptible）在 bash 工具或底层执行器中的具体实现代码；\n"
            "3. 定位工作区信任机制（Project Trust / project_trust.py）的鉴权判断入口函数。"
        ),
        "evaluation_criteria": {
            "completion": "给出全部3处源码的相对路径、函数名及行号范围",
            "accuracy": "路径真实存在，函数名称精准，行号与代码实现吻合，无虚构文件或符号",
        },
    },
    {
        "id": "T3",
        "dimension": "高阶并发算法与工程代码实现 (Complex Concurrency & Algorithmic Implementation)",
        "title": "编写生产级异步复合滑动窗口限流器",
        "prompt": (
            "请在 Python 中实现一个生产级、异步线程/协程安全的复合滑动窗口限流器（CompositeSlidingWindowLimiter）：\n"
            "1. 结合滑动日志（Sliding Log）精确计数与令牌桶（Token Bucket）突发平滑特性；\n"
            "2. 支持动态突发容忍度（burst_ratio）与滑动窗口秒数（window_seconds）；\n"
            "3. 支持异步获取许可 async def acquire(self, tokens: int = 1, timeout: float | None = None) -> bool，带最大排队超时抛弃或返回 False；\n"
            "4. 包含严谨的类型注解、基于 asyncio.Lock/Condition 的无死锁并发安全设计、边界异常处理及类定义文档。"
        ),
        "evaluation_criteria": {
            "completion": "类结构完整，包含acquire接口、超时丢弃、动态突发、滑动日志与令牌桶双重校验",
            "accuracy": "并发逻辑严密无死锁，单调时间计算准确，边界条件无越界，类型提示符合PEP规范",
        },
    },
    {
        "id": "T4",
        "dimension": "运行时状态机异常排查与上下文自愈 (Agent Runtime State & Context Repair)",
        "title": "分析缺少 ToolResult 的协议冲突并设计上下文自愈算法",
        "prompt": (
            "在自主 Agent 的 ReAct 循环中，假设大模型在一次请求中输出了两个并发工具调用 ToolCall-1 和 ToolCall-2。此时若 ToolCall-1 正常返回结果，但 ToolCall-2 在执行中遭遇宿主进程被强制中断或未捕获的严重异常（例如 OS 信号中断或网络超时），导致历史消息队列中只记录了 ToolCall-1 的 ToolResult。\n"
            "1. 请从 OpenAI / Anthropic 等主流模型协议约束出发，分析缺少 ToolResult 会给后续推理带来什么严重后果；\n"
            "2. 结合 JE 自身的 repair_tool_history 或健壮上下文修复机制，给出修复该断裂上下文的标准状态机修复算法；\n"
            "3. 给出一段 Python 实现代码，演示如何检测并自动插入合成的错误占位结果以修复对话历史。"
        ),
        "evaluation_criteria": {
            "completion": "涵盖主流大模型协议约束分析、状态机修复原理阐释及可执行的自愈修复算法代码",
            "accuracy": "协议机制分析准确（OpenAI 400 invalid_request_error、Anthropic role alternating 违规），修复逻辑严密",
        },
    },
    {
        "id": "T5",
        "dimension": "严苛单元测试编写与边界覆盖 (Unit Testing & Boundary Coverage)",
        "title": "为局部代码块编辑工具编写全覆盖 pytest 用例",
        "prompt": (
            "为当前项目中的局部块代码编辑工具（位于 src/je_coding/tools.py 或相关模块中的 edit 工具）编写一套严密的 pytest 单元测试用例。测试必须包含：\n"
            "1. 正常单次替换并验证文件内容；\n"
            "2. 目标文本在文件中未找到时的报错与原始内容未变断言；\n"
            "3. 目标文本在文件中出现多次（歧义多匹配）时拒绝修改的错误断言；\n"
            "4. 换行符（CRLF 与 LF）跨平台混杂时的规范化匹配测试；\n"
            "5. 使用 tmp_path fixture 进行完整的文件隔离；\n"
            "要求代码可直接在 pytest 环境下执行。"
        ),
        "evaluation_criteria": {
            "completion": "包含所要求的5大测试场景，涵盖正常与边界异常",
            "accuracy": "断言逻辑严谨，fixture 使用标准，语法与真实工具接口契约吻合，无语法错误",
        },
    },
    {
        "id": "T6",
        "dimension": "复杂代码异味重构与设计模式设计 (Refactoring & Design Patterns)",
        "title": "重构 20+ if/else 分支的庞大模型适配器函数",
        "prompt": (
            "假设现有系统有一个庞大的单体函数 def call_llm(provider: str, model: str, prompt: str, ...)，内部充斥着 20 多个针对 OpenAI、Claude、DeepSeek、Ollama 等厂商的 if/elif 逻辑，且耦合了鉴权读取、请求体构造、流式响应解析、思考标签提取（<think> / reasoning_content）和失败重试。\n"
            "请遵循面向对象 SOLID 原则与面向协议编程思想：\n"
            "1. 提出重构方案，说明采用了哪些设计模式（如 Factory, Strategy/Adapter, Pipeline 等）；\n"
            "2. 使用 mermaid classDiagram 绘制重构后的类与协议关系图；\n"
            "3. 给出重构后的抽象协议（Protocol/BaseProvider）、DeepSeek 适配器实现及统一调用入口代码。"
        ),
        "evaluation_criteria": {
            "completion": "提供架构重构设计、Mermaid 类图、完整协议定义与 DeepSeek 适配器落地代码",
            "accuracy": "SOLID原则与设计模式运用恰当，Mermaid语法无解析报错，代码解耦彻底且具备扩展性",
        },
    },
    {
        "id": "T7",
        "dimension": "系统集成、跨平台脚本与运维排错 (Cross-Platform Automation & System Health Check)",
        "title": "编写跨平台 (Win/Linux) 代码库健康审计与静态质检脚本",
        "prompt": (
            "请编写一个适用于企业级代码库健康检查的跨平台自动化脚本（使用 Python 3.12+ 编写，以便在 Windows pwsh 和 Linux bash 下均可一键运行）：\n"
            "1. 自动化检测 Python 版本（>= 3.12）、Git 工具是否安装、uv 命令是否可用；\n"
            "2. 使用 Git 命令检查当前工作区是否干净（是否有未提交或未追踪的文件）；\n"
            "3. 扫描项目根目录下超过 5MB 的大文件（输出路径与文件大小）；\n"
            "4. 自动尝试调用 ruff check 进行快速 lint 检查并捕获其返回值与错误总数；\n"
            "5. 将所有检查结果汇聚为结构化 JSON 格式打印输出，并根据检查是否全部通过返回 0 或 1 退出码。"
        ),
        "evaluation_criteria": {
            "completion": "实现所有5项健康检查功能，具备JSON格式化汇总与退出码控制",
            "accuracy": "跨平台兼容（路径分隔符、子进程调用安全），命令错误捕获周全，JSON输出符合规范",
        },
    },
    {
        "id": "T8",
        "dimension": "负向约束遵循与多智能体长流程规划 (Constraint Following & Agent Planning)",
        "title": "零外部依赖规划 Multi-Agent Code Review Pipeline",
        "prompt": (
            "【严苛约束任务】：请为 JE 架构设计一个‘多智能体协同代码审查（Multi-Agent Code Review Pipeline）’。\n"
            "【强制负向约束】：\n"
            "1. 严禁使用任何外部多智能体框架（如 LangChain / CrewAI / AutoGen / Semantic Kernel 等），只能基于 JE 原生的 AgentHarness、SessionTree 和自定义 Tool 架构进行设计；\n"
            "2. 严禁使用任何模糊代词或省略号（如'// 省略其他实现'），关键方法必须给出完整定义。\n"
            "【强制输出要求】：\n"
            "1. 定义三个不同视角的专职 Agent 角色（架构合规、安全漏洞、性能与并发）及其 Prompt 策略；\n"
            "2. 给出基于 Mermaid 的协同工作流序列图（sequenceDiagram）；\n"
            "3. 结尾必须包含一段独立的、严格符合 JSON 标准的配置对象（包含这三个 Agent 的 name, role, system_prompt, allowed_tools），JSON 中严禁包含任何注释或尾随逗号，确保 json.loads 可以直接解析。"
        ),
        "evaluation_criteria": {
            "completion": "包含3个专职Agent角色设定、完整实现代码、Mermaid时序图、合法JSON配置",
            "accuracy": "零外部依赖约束完全遵守，无代码省略，Mermaid语法规范，JSON 100% 可被 json.loads 解析",
        },
    },
]


def run_benchmark():
    project_root = Path("d:/projects/JE")
    output_dir = project_root / "benchmark_output"
    output_dir.mkdir(exist_ok=True)
    results_file = output_dir / "je_benchmark_results.json"

    print("=" * 70)
    print(">>> JE-Agent (DeepSeek-V4-Pro) 8-Dimensional Capability Benchmark")
    print(f"Working Directory: {project_root}")
    print(f"Total Test Cases: {len(BENCHMARK_TESTS)}")
    print("=" * 70)

    results = []

    for index, test in enumerate(BENCHMARK_TESTS, 1):
        test_id = test["id"]
        title = test["title"]
        dimension = test["dimension"]
        prompt = test["prompt"]

        print(f"\n[{index}/{len(BENCHMARK_TESTS)}] Running {test_id}: {title}...")
        print(f"Dimension: {dimension}")

        start_time = time.time()
        process = subprocess.Popen(
            ["uv", "run", "je", "-p", prompt],
            cwd=str(project_root),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        stdout, stderr = process.communicate()
        elapsed = time.time() - start_time

        success = process.returncode == 0
        status_str = "SUCCESS" if success else f"FAILED (code {process.returncode})"
        print(f"-> Completed in {elapsed:.2f}s | Status: {status_str} | Output Length: {len(stdout)} chars")

        test_result = {
            "id": test_id,
            "dimension": dimension,
            "title": title,
            "prompt": prompt,
            "evaluation_criteria": test["evaluation_criteria"],
            "status": "success" if success else "failed",
            "return_code": process.returncode,
            "elapsed_seconds": round(elapsed, 2),
            "stdout": stdout,
            "stderr": stderr,
        }
        results.append(test_result)

        # Write intermediate results
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print(f" Benchmark Run Completed! Saved to: {results_file}")
    print("=" * 70)


if __name__ == "__main__":
    run_benchmark()
