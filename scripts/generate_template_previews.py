#!/usr/bin/env python3
"""
生成模板预览视频 — 用于 Web UI 展示
"""

import subprocess
import os
from pathlib import Path

PREVIEWS_DIR = Path(__file__).parent.parent / "web" / "static" / "previews"
PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)

# 字幕样式配置
TEMPLATE_CONFIGS = {
    "default": {
        "name": "默认模板",
        "subtitle": {
            "fontsize": 48,
            "fontcolor": "white",
            "borderw": 2,
            "bordercolor": "black",
            "y": "h-100",
        },
        "bg_color": "#1a1a1a",
        "sample_text": "情感驱动视频生产",
    },
    "cinematic": {
        "name": "电影风格",
        "subtitle": {
            "fontsize": 36,
            "fontcolor": "white",
            "borderw": 1,
            "bordercolor": "black@0.5",
            "y": "h-80",
        },
        "bg_color": "#1a1a2e",
        "sample_text": "让音乐讲述故事",
    },
    "minimal": {
        "name": "极简风格",
        "subtitle": {
            "fontsize": 32,
            "fontcolor": "#333333",
            "borderw": 0,
            "bordercolor": "transparent",
            "y": "h-60",
        },
        "bg_color": "#f5f5f5",
        "sample_text": "简洁之美",
    },
    "neon": {
        "name": "霓虹风格",
        "subtitle": {
            "fontsize": 52,
            "fontcolor": "#00ffff",
            "borderw": 0,
            "bordercolor": "transparent",
            "shadowcolor": "#00ffff",
            "y": "h-120",
        },
        "bg_color": "#0a0a1a",
        "sample_text": "霓虹之夜",
    },
}

def get_font_path():
    """获取字体路径"""
    # macOS
    macos_fonts = [
        "/System/Library/Fonts/PingFang.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for font in macos_fonts:
        if os.path.exists(font):
            return font
    return "Arial"

def generate_preview_video(template_name: str, config: dict, duration: int = 8):
    """生成单个模板预览视频

    Args:
        template_name: 模板名称
        config: 模板配置
        duration: 视频时长（秒）
    """
    output_path = PREVIEWS_DIR / f"{template_name}.mp4"
    font_path = get_font_path()

    subtitle = config["subtitle"]
    bg_color = config["bg_color"]
    text = config["sample_text"]

    # 构建 FFmpeg 命令
    # 生成渐变背景视频 + 字幕
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c={bg_color}:s=1920x1080:d={duration}:r=30",
        "-vf",
        f"drawtext=text='{text}':fontfile='{font_path}':"
        f"fontsize={subtitle['fontsize']}:fontcolor={subtitle['fontcolor']}:"
        f"borderw={subtitle['borderw']}:bordercolor={subtitle['bordercolor']}:"
        f"x=(w-text_w)/2:y={subtitle['y']}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        str(output_path)
    ]

    # 霓虹风格特殊处理 - 添加发光效果
    if template_name == "neon":
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c={bg_color}:s=1920x1080:d={duration}:r=30",
            "-vf",
            f"drawtext=text='{text}':fontfile='{font_path}':"
            f"fontsize={subtitle['fontsize']}:fontcolor={subtitle['fontcolor']}:"
            f"borderw=0:x=(w-text_w)/2:y={subtitle['y']},"
            f"gblur=sigma=3:enable='between(t,0,{duration})'",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            str(output_path)
        ]

    print(f"生成 {config['name']} 预览视频...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"  ✓ 已保存: {output_path}")
        return True
    else:
        print(f"  ✗ 错误: {result.stderr[:200]}")
        return False

def generate_all_previews():
    """生成所有模板预览视频"""
    print("=" * 50)
    print("生成模板预览视频")
    print("=" * 50)

    success_count = 0
    for template_name, config in TEMPLATE_CONFIGS.items():
        if generate_preview_video(template_name, config):
            success_count += 1

    print("=" * 50)
    print(f"完成: {success_count}/{len(TEMPLATE_CONFIGS)} 个预览视频")
    print("=" * 50)

if __name__ == "__main__":
    generate_all_previews()