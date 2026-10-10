# JE 编码能力 benchmark

10 个标准库 Python 3.12 编码任务，见 [tasks.json](tasks.json)。任务涵盖数据处理、修复、调度、缓存、并发、数据库、CLI、安全和检索。所有新代码和运行记录位于本目录，不修改 `src/`。

## 评分与边界

- **完成度**：每题四个独立验收组通过比例（0–100），需实际运行正确才算完成，不能只凭文件存在。
- **准确率**：外部检查的断言通过比例（0–100），题目等权平均；每项断言在异常时明确记为失败。
- **性能**：同机独立子进程执行，每题三次计时取中位数，报告原始毫秒与性能预算达标率。只有所有正确性检查通过才获得该题性能分，错误但很快的代码得 0。另外记录 JE 推理/工具总耗时、请求数、tokens；这些与代码速度分开。

每个任务独立工作目录、独立 JE_HOME、新 CodingSession，复用 JE 原有 read/write/edit/bash 与事件流。扩展和全局 skills 关闭，未改生产源码。bash 执行使用 Windows shell；提示公开 Python 解释器路径。每题至多 24 模型轮次、480 秒、单响应最多 8192 tokens，供应商请求超时 120 秒，失败不自动改用其他模型。默认单题单次，任务串行执行。

密钥只从环境变量或隐藏输入读取，绝不写入报告/工作区；模型进程工具命令也不继承密钥。公开规格、starter 和公开 smoke 相同；外部 evaluator 与报告不放入 JE 任务工作区。这里的目录隔离防止意外相互影响，**不是针对恶意代理的操作系统沙箱**。

Codex 基线是本次由助手亲自实现并验证的答案，不是伪造的 JE 输出。助手同时编写了规格和评测器，知晓测试，存在作者优势；这是一组小规模项目回归/能力诊断，不能作为盲测模型排行榜。Codex 的聊天 token/端到端推理耗时无法由此脚本准确读取，记为不可用，不与 JE 的推理吞吐量做虚假对比。

Codex 基线经过验证后修正了 Windows ZIP 原始路径检查并改进了 DAG 查询；JE 答案保存首次运行结果，未作修改。性能得分为正确性门槛之上的预算达标率，并不是比对模型推理快慢。所有失败详情和原始代码计时在报告中保留。

## 运行

在仓库根目录：

```powershell
.venv/Scripts/python -m benchmark.runner prepare
.venv/Scripts/python -m benchmark.runner je
.venv/Scripts/python -m benchmark.runner score
.venv/Scripts/python -m pytest benchmark/tests -q
```

`je` 会提示隐藏输入 DeepSeek key；也可用 `DEEPSEEK_API_KEY`。官方 V4.1 Flash 使用 `deepseek-flash`，来源：[DeepSeek 发布说明](https://deepseek.com/news/deepseek-v4-1-flash/)。运行前通过 `/models` 验证可用性，保留返回的模型列表和实际响应模型。报告见 `reports/`，原始解决方案/会话在忽略的 `runs/` 中。已保存的 Codex 基线见 `baseline/`，重跑时会复制到独立工作区。

本轮 JE 答案和自测代码另存于 `submissions/je/`，统计在 `submissions/metadata/`，SHA-256 清单在 `reports/artifact-manifest.json`。新 checkout 无 `runs/` 时，`score` 会直接评测这些归档答案，无需联网或 key。`prepare` 拒绝覆盖既有工作区；开展下一轮前先将 `runs/` 另存。报告的零 cost 字段不是实际账单，账单金额记为不可用。
