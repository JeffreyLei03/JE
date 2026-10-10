"""Run JE agent on the Synthwave 3D Highway demo task in an isolated workspace."""

import os
import subprocess
import sys
import time
from pathlib import Path

# Force UTF-8 on Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

WORKSPACE = Path("D:/projects/tmp/je-synthwave-demo")
WORKSPACE.mkdir(parents=True, exist_ok=True)

PROMPT = """【独立高表现力创作任务：赛博朋克 3D 霓虹公路交互应用】
请在当前目录从零创建单文件自包含、零外部依赖的现代交互式网页应用 index.html。
主题：80s 赛博朋克 3D 霓虹公路 (Cyberpunk Synthwave Outrun Highway)。

设计与技术指标：
1. 纯原生技术：零外部 CDN、零第三方库、零外部图片与音频文件。完全使用 HTML5 Canvas、CSS3 与原生 JavaScript，单文件可离线双击打开。
2. 视觉盛宴：
   - 背景：深邃紫黑星空，地平线上发光渐变落日（Neon Synthwave Sun），远景暗紫色透视线框山脉；
   - 伪 3D 网格公路：利用数学透视投影（Perspective Projection）渲染向地平线收敛、向玩家高速滚动的发光青色/品红霓虹网格公路，带平滑弯道曲率与地形起伏；
   - 赛博超跑：居中绘制流线型炫酷跑车，随转向侧倾与车轮偏转，尾部排气管喷射动态粒子火焰与双条霓虹红光尾灯拖影；
   - 环境要素：道路两侧掠过的发光霓虹棕榈树与发光路标；路面根据速度产生动态速度线；
   - 屏幕滤镜：支持复古 CRT 扫描线与暗角滤镜开关。
3. 操控与交互：
   - 键盘控制：方向键/WASD 变道转向、加速制动；空格键触发氮气加速喷射（画面震颤加速与火焰粒子爆发）；C 键切换 CRT 扫描线；
   - Web Audio API：纯原生振荡器（Oscillator）合成 Synthwave 复古引擎轰鸣与电子合成器背景琶音（支持一键静音/开启）；
   - UI 面板：优雅的未来科技 HUD（显示时速 MPH、齿轮档位、氮气槽 Nitro、当前弯道距离）。
4. 保证静态语法无误，在完成后执行验证并输出简洁摘要。"""

print(f"Starting JE task in {WORKSPACE}...")
start_time = time.time()

je_exe = "D:/projects/JE/.venv/Scripts/je.exe"

process = subprocess.Popen(
    [je_exe, "-p", PROMPT, "--cwd", str(WORKSPACE)],
    cwd="d:/projects/JE",
    stdin=subprocess.DEVNULL,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    encoding="utf-8",
    errors="replace",
)

stdout, stderr = process.communicate()
elapsed = time.time() - start_time

print(f"Task finished in {elapsed:.2f}s, exit code: {process.returncode}")
print("--- STDOUT ---")
print(stdout[-2000:] if stdout else "(none)")
if process.returncode != 0:
    print("--- STDERR ---")
    print(stderr[-1000:] if stderr else "(none)")
