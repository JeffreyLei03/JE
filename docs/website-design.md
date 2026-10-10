# JE 项目作品展示页

网站继续使用仓库中的 Astro 静态构建，默认部署前缀为 `/JE/`。首页以中文展示项目定位、真实运行、三层架构与工程改进，英文文档保持原有地址。使用深色背景、薄荷色强调、系统字体和留白，减少外部字体加载造成的布局变化。

## 演示来源

`website/static/images/demo/` 中的三个 SVG 是实际 `JeTuiApp` 在 Textual 无头终端中运行后，通过原生 `save_screenshot` 导出的画面。它们不是拼接的聊天记录或模拟模型输出。模型为 DeepSeek `deepseek-v4-flash`，终端尺寸为 120 × 40。

任务在隔离目录中读取 `greeting.py`、编辑函数、写入 `test_greeting.py`，再读取两个文件。生成测试验证 `greet()` 和 `greet('Ada')`，两条断言通过。`capture.json` 保存模型、工具调用、日期与渲染方式，不包含凭据或会话原始请求。

复现截图，在仓库根目录运行：

```powershell
uv run python scripts/capture_website_demo.py
```

脚本通过隐藏输入读取 API key，真实调用会产生模型用量。只向模型提供脚本创建的示例文件；工作区、配置和会话均在仓库同级的 `tmp/je-portfolio-demo/` 内。每次使用新的会话文件，避免上一次会话影响演示。脚本导出输入、完成结果、Ctrl+O 工具详情三个画面，并执行生成测试。

首页使用同名 JPG，避免 SVG 作为 img 嵌入时外部字体被浏览器限制而回退。图片由原生 SVG 在浏览器中实际渲染后截图，保留完整终端画面；放大弹窗也提供原生 SVG 链接。重新捕获后，应同步更新 JPG 和 `capture.json` 的图片记录。

输入栏空闲时显示 `JE`，为两个字母预留三列宽度；执行任务时继续显示活动动画，Shell 模式显示 `$`。侧栏底部与终端窗口标题同样使用 `JE`。品牌更新后的演示截图通过当前 TUI 重载此前真实 DeepSeek 会话重新导出，模型内容与工具记录沿用原始运行。首页移除项目来源介绍区块；页脚采用基于 PI 的表述。

## 交互与验证

- 三个步骤按钮同步切换截图、标题、说明与 `aria-pressed` 状态。
- 原生 dialog 提供截图放大、焦点约束、Esc 关闭；手机可在截图容器中横向滚动查看细节。
- 文档搜索使用一个共享索引，让中文首页也能搜索英文文档。原生搜索 dialog 支持 Ctrl/Cmd+K。
- 保留全部文档、RSS、站点地图、安装脚本、编辑链接和 `/JE/` 前缀。
- 系统字体、清晰的键盘焦点与减少动画偏好保证阅读和导航可用。

验证命令：

```powershell
cd website
$env:ASTRO_TELEMETRY_DISABLED = '1'
npm run check
npm run build
npm test
npm run format:check
npm run preview -- --host 127.0.0.1 --port 4321
```

本轮浏览器验证覆盖桌面首屏、390px 手机导航、演示步骤切换、截图放大、首页搜索 Sessions 并打开文档。搜索索引、静态链接、截图文件与凭据排除由回归测试检查。分享卡片 JPG 由同目录的 SVG 在浏览器中以 1200 × 630 导出。
