# JE 与 Codex 编码任务实测

JE 源码提交：`9e85cfff5876cc6a779d4161c27cbff165ffe73e`。

每题一次编码运行、三次外部验证/计时。性能预算每题 2000 ms，正确性全通过才得分。

| 执行者 | 完成度 | 准确率 | 性能达标率 |
|---|---:|---:|---:|
| codex | 100.0% | 100.0% | 100% |
| je | 92.5% | 96.32% | 80% |

| 任务 | 执行者 | 完成度 | 准确率 | 性能 | 代码耗时 ms | JE执行秒 |
|---|---|---:|---:|---:|---:|---:|
| CSV 金额汇总 | codex | 100.0 | 100.0 | 100 | 119.806 | N/A |
| CSV 金额汇总 | je | 100.0 | 100.0 | 100 | 59.646 | 17.85 |
| 区间合并缺陷修复 | codex | 100.0 | 100.0 | 100 | 33.901 | N/A |
| 区间合并缺陷修复 | je | 75.0 | 78.57 | 0 | N/A | 18.64 |
| 确定性依赖调度 | codex | 100.0 | 100.0 | 100 | 10.129 | N/A |
| 确定性依赖调度 | je | 100.0 | 100.0 | 100 | 9.095 | 17.323 |
| TTL 与 LRU 缓存 | codex | 100.0 | 100.0 | 100 | 39.625 | N/A |
| TTL 与 LRU 缓存 | je | 100.0 | 100.0 | 100 | 20.419 | 22.853 |
| 有界异步映射 | codex | 100.0 | 100.0 | 100 | 5.157 | N/A |
| 有界异步映射 | je | 100.0 | 100.0 | 100 | 5.612 | 24.26 |
| 原子 SQLite 迁移 | codex | 100.0 | 100.0 | 100 | 58.720 | N/A |
| 原子 SQLite 迁移 | je | 100.0 | 100.0 | 100 | 84.681 | 49.63 |
| 流式 JSONL 命令行工具 | codex | 100.0 | 100.0 | 100 | 103.780 | N/A |
| 流式 JSONL 命令行工具 | je | 100.0 | 100.0 | 100 | 101.517 | 15.873 |
| 安全 ZIP 解压 | codex | 100.0 | 100.0 | 100 | 921.253 | N/A |
| 安全 ZIP 解压 | je | 50.0 | 84.62 | 0 | N/A | 50.122 |
| 确定性文本检索 | codex | 100.0 | 100.0 | 100 | 120.187 | N/A |
| 确定性文本检索 | je | 100.0 | 100.0 | 100 | 133.038 | 19.006 |
| 分轮重试作业队列 | codex | 100.0 | 100.0 | 100 | 15.325 | N/A |
| 分轮重试作业队列 | je | 100.0 | 100.0 | 100 | 18.649 | 13.702 |

## 验证失败

- je / 02_intervals: invalid [(False, 3)]: TypeError: interval start must be an int, got False; invalid [(1.0, 3)]: TypeError: interval start must be an int, got 1.0; invalid [(1,)]: TypeError: interval must be an iterable of exactly two integers, got (1,)
- je / 08_zip: unsafe x\bad: AssertionError: expected True, got False; parent file conflict: FileExistsError: [WinError 183] 当文件已存在时，无法创建该文件。: 'C:\\Users\\onepl\\AppData\\Local\\Temp\\tmpk9st4mil\\out\\a'

## 运行统计

JE 总执行耗时 249.259 秒，78 次请求、81 次工具调用、572427 reported tokens（含缓存）。实际通过 111/116 个检查；表格准确率为题目等权平均。
账单金额不可观测；Usage.cost 的 0 是未配置价格的默认值，不代表免费。

## 解释范围

Codex 基线由当前助手亲自实现，且助手知道规格与验证器，存在作者优势。
Codex 在验证后改进了 DAG 查询并修复 ZIP 原始路径检查；JE 为首轮运行结果，未修补答案。
没有把 Codex 的推理时间/token 伪装成可观测数据。JE 的完整请求/token/工具统计见 JSON。
这不是盲测排名；单次小样本适合诊断 JE 工作流。没有修补生产 JE 源码来适应测试。
