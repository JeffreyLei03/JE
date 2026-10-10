# JE Desktop 设计与架构

## 用户界面

布局借鉴编辑器的工作区组织，而以 Agent 任务为中心：活动栏 → 项目/会话/文件 → 聊天与代码 → 资源检查栏，底部为命令输出与模型状态。默认浅色，使用低饱和绿色作为 JE 标识、选中与运行状态颜色。Monaco 按需加载，首次进入聊天不会加载整个编辑器。

会话与文件使用独立标签；分栏模式将聊天和编辑器放在同一视野。右侧不会根据终端行数隐藏，空 Skills/Prompts 显示真实路径说明。工具调用以 ID 关联开始、增量和结束事件，历史轨迹从已保存的消息恢复。运行结束以 `agent_settled` 为准，保留重试与压缩的中间状态。

## 分层边界

```text
React + Monaco renderer
  ↓ 窄接口 contextBridge / IPC
Electron main process
  ├─ 原生窗口、目录选择、工作区文件与 Git
  └─ JSONL subprocess client
       ↓ stdin/stdout
je_coding.desktop / DesktopRpcServer
       ↓
CodingSession → je_agent + je_ai
```

没有改变 `je_agent` 与 `je_ai` 的前端依赖边界。新 Python 模块复用既有 RpcServer；只扩展 `desktop_info`、`desktop_login`、`desktop_reload`，提供资源发现、会话列表和登录。原有 prompt、abort、模型、思考强度、bash、新建/恢复、压缩命令直接复用。stdout 只传 JSONL，stderr 为诊断。

后端首次缺少凭据时可启动工作区；用户连接模型后启用真实提供商。每个窗口维护一个当前项目会话进程，切换目录会取消并关闭旧进程。新的空会话在首次持久化时才进入会话索引。

## 桌面边界

Electron 使用 contextIsolation、sandbox 与关闭 nodeIntegration 的 renderer。preload 只暴露所需操作，main 验证发送方 frame；不向 renderer 暴露整个 IPC 或任意 Node API。页面使用 `jeapp://app/` 静态协议，资源限定为 dist 文件，便于模块与 Monaco Worker 在打包后正常加载。外部窗口与导航被禁止。

工作区文件操作要求相对路径，并用 realpath 校验位于选定工作区；文件树省略符号链接与生成目录。编辑器只读取 2 MB 内的文本文件，保存时验证内容 revision。项目内指令必须显式授权，默认关闭扩展代码。这个边界不限制已授权 Agent 的 shell 工具为操作系统沙箱。

API key 复用 JE 的 FileCredentialStore，避免出现在聊天、stdout 返回值或浏览器持久存储。OAuth 登录使用既有终端流程。浏览器 QA 服务有独立的来源检查与临时 token，凭据/信任操作在该服务禁用；生产桌面没有 HTTP 控制接口。

参考：[Electron 隔离上下文](https://www.electronjs.org/docs/latest/tutorial/context-isolation)、[Electron IPC](https://www.electronjs.org/docs/latest/tutorial/ipc)。

## 打包和验证

PyInstaller 收集 JE 数据目录与模型适配器，输出独立 `je-engine.exe`；Electron Builder 生成 Windows x64 便携 EXE。发布应用从本地空工作目录启动，用户通过原生对话框选择项目。生成目录与运行依赖不进入 Git。

检查覆盖路径穿越、文本保存冲突、二进制过滤、Unicode/CRLF JSONL、响应关联、多工具增量、历史工具恢复、无模型登录时资源发现和既有 RPC 兼容性。Python 相关回归共 22 项，前端与桥接测试共 6 项。真实 Electron smoke 验证开发构建和便携 EXE 的原生窗口、preload、IPC 与内置引擎联通；同一 renderer 通过浏览器验收文件浏览、编辑器、分栏、模型切换、命令输出及 DeepSeek 的只读 read 任务。截图保存在 `desktop/screenshots/`。

当前终端为单次命令执行器；完整 PTY、LSP、调试器和 VS Code 扩展兼容不在这版实现中。
