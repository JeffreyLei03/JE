"""Encode the captured demo frames into web-optimized MP4, extract poster, and generate metadata."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

DESKTOP_DIR = Path("D:/projects/tmp/je-pelican-desktop-capture")
OUTPUT_DIR = Path("D:/projects/tmp/je-pelican-output-capture")
TARGET_DIR = Path("D:/projects/JE/website/static/media/desktop")
HTML_SOURCE = Path("D:/projects/tmp/je-pelican-demo/index.html")

TARGET_DIR.mkdir(parents=True, exist_ok=True)
(TARGET_DIR / "output").mkdir(parents=True, exist_ok=True)

# 1. Copy generated HTML
html_dest = TARGET_DIR / "output" / "pelican.html"
html_dest.write_bytes(HTML_SOURCE.read_bytes())
print(f"Copied HTML to {html_dest}")

# 2. Encode Part 1 (Desktop)
part1 = Path("D:/projects/tmp/part1.mp4")
print("Encoding Part 1 (Desktop Session: 3414 frames)...")
subprocess.run(
    [
        "ffmpeg", "-y",
        "-framerate", "45",
        "-i", str(DESKTOP_DIR / "%06d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "22",
        "-preset", "fast",
        str(part1),
    ],
    check=True,
)

# 3. Encode Part 2 (Output animation)
part2 = Path("D:/projects/tmp/part2.mp4")
print("Encoding Part 2 (Output Preview: 322 frames)...")
subprocess.run(
    [
        "ffmpeg", "-y",
        "-framerate", "16",
        "-i", str(OUTPUT_DIR / "%06d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "22",
        "-preset", "fast",
        str(part2),
    ],
    check=True,
)

# 4. Concat Part 1 + Part 2
final_mp4 = TARGET_DIR / "task-demo.mp4"
print("Concatenating into final web-ready MP4...")
concat_filter = "[0:v]fps=30,scale=1480:960[v0];[1:v]fps=30,scale=1480:960[v1];[v0][v1]concat=n=2:v=1:a=0[outv]"
subprocess.run(
    [
        "ffmpeg", "-y",
        "-i", str(part1),
        "-i", str(part2),
        "-filter_complex", concat_filter,
        "-map", "[outv]",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "22",
        "-preset", "medium",
        "-movflags", "+faststart",
        str(final_mp4),
    ],
    check=True,
)

# 5. Extract poster
poster_dest = TARGET_DIR / "poster.jpg"
print("Generating poster.jpg...")
subprocess.run(
    [
        "ffmpeg", "-y",
        "-i", str(OUTPUT_DIR / "000100.png"),
        "-vf", "scale=1480:960",
        "-q:v", "2",
        str(poster_dest),
    ],
    check=True,
)

# 6. Generate record.json
# Part 1 length = 3414 / 45 = ~75.87s
# Part 2 length = 322 / 16 = ~20.125s
# Total length = ~96s
record_data = {
    "playback_note": "4倍速回放",
    "task": "从零创建「鹈鹕骑自行车」纯前端单文件交互动画",
    "model": "deepseek-v4-flash",
    "started_at": "2026-10-10T11:58:27Z",
    "duration_seconds": 96.0,
    "chapters": [
        {"time": 0, "label": "输入任务与意图理解"},
        {"time": 18, "label": "内联 SVG 矢量结构规划"},
        {"time": 38, "label": "踏板与车轮运动学推导"},
        {"time": 56, "label": "自动化静态校验与语法自测"},
        {"time": 76, "label": "真实渲染与昼夜交互体验"},
    ],
    "verification": {
        "html_syntax": "passed",
        "svg_tags": "passed",
        "zero_dependency": True,
        "reduced_motion": True,
    },
}
(TARGET_DIR / "record.json").write_text(
    json.dumps(record_data, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("Generated record.json")

# 7. Generate captions.vtt
vtt_content = """WEBVTT - JE Desktop Task Showcase: Pelican on a Bicycle

00:00.000 --> 00:18.000
01 / 输入任务：要求用原生 HTML/SVG/CSS/JS 从零实现「鹈鹕骑自行车」沿海骑行动画

00:18.000 --> 00:38.000
02 / 矢量图形构建：手绘鹈鹕白色身躯、橙色喉囊与自行车部件，分层设计视差滚动海景

00:38.000 --> 00:56.000
03 / 运动学计算：实现车轮旋转、脚随曲柄画圆与自然屈膝联动的运动学实时计算

00:56.000 --> 00:76.000
04 / 静态语法自验：编写检查脚本，验证 DOM 结构、事件监听与无障碍偏好

00:76.000 --> 01:36.000
05 / 最终交付体验：全屏运行动画，支持速度调节、昼夜模式切换与键盘快捷键
"""
(TARGET_DIR / "captions.vtt").write_text(vtt_content.strip() + "\n", encoding="utf-8")
print("Generated captions.vtt")

print("All showcase assets created successfully!")
