---
title: "04 — 会话体系与持久化 (Sessions)"
---

会话（Sessions）负责跨运行生命周期保留对话上下文、工具交互历史与智能体状态。

## 架构设计 (Design)

Je 采用只追加（Append-Only）的树状会话结构。Je 不会原地修改旧状态，而是通过追加条目并在恢复时重放来重建线性对话分支。

底层实现位于：
```text
src/je_agent/session/
```

## 会话条目类型 (Entry Types)

- `message`：用户、助手或工具执行结果消息
- `model_change`：大模型切换记录
- `thinking_level_change`：深度思考预算调整记录
- `compaction`：上下文压缩事件
- `branch_summary`：会话分支摘要
- `label`：用户对会话节点的打标命名
- `session_info`：会话初始元数据
- `custom`：扩展或前端自定义元数据

## 持久化边界与安全保证

`CodingSession` 将 `MessageEndEvent` 视为持久化写入的边界。持久化采用 Push 模型：编码会话作为监听者订阅 Harness，在事件传递给前端渲染之前立即写入存储。

这意味着即使前端 UI 意外退出或被中断，已完成的消息与工具结果绝不会丢失。

## 系统提示词重建策略

会话恢复（`/resume`）由两部分组合：
```text
保存的对话分支历史 + 当前工作区最新解析的系统提示词
```
这保证了当工作区的 `AGENTS.md`、`.je/` 技能或提示词调整后，恢复的会话能够立即感知并应用最新的工程规则，而无需强行锁定陈旧的系统提示词快照。
