#!/usr/bin/env python3
"""
视频模板引擎 — 解析 HTML 模板的 CSS 变量，映射到 FFmpeg 参数

支持三种模板类型：
- static_*.html: 静态模板（纯文字样式，无媒体背景）
- image_*.html: 图片模板（AI图片/用户图片背景）
- video_*.html: 视频模板（素材视频背景）

用法:
    python3 -m core.template_engine --list
    python3 -m core.template_engine --template static_minimal --output config.json
"""

import argparse
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 模板目录
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def list_templates(category: Optional[str] = None) -> List[Dict]:
    """列出所有可用模板

    Args:
        category: 模板类别 (static/image/video)，可选

    Returns:
        模板信息列表
    """
    templates = []

    if not TEMPLATE_DIR.exists():
        return templates

    for template_file in TEMPLATE_DIR.glob("*.html"):
        name = template_file.stem

        # 分类
        if name.startswith("static_"):
            template_type = "static"
        elif name.startswith("image_"):
            template_type = "image"
        elif name.startswith("video_"):
            template_type = "video"
        else:
            template_type = "unknown"

        # 过滤类别
        if category and template_type != category:
            continue

        # 解析模板获取描述
        config = parse_template(template_file)

        templates.append({
            "name": name,
            "type": template_type,
            "file": str(template_file),
            "description": config.get("description", f"{template_type} 模板"),
            "transition_type": config.get("transition_type", "fade"),
            "transition_duration": config.get("transition_duration", 0.3),
        })

    return templates


def parse_template(template_path: Path) -> Dict:
    """解析模板文件，提取 CSS 变量

    Args:
        template_path: 模板文件路径

    Returns:
        模板配置字典
    """
    if not template_path.exists():
        template_path = TEMPLATE_DIR / template_path

    if not template_path.exists():
        raise FileNotFoundError(f"模板不存在: {template_path}")

    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 提取 CSS 变量
    config = _extract_css_vars(content)

    # 提取标题
    title_match = re.search(r'<title>(.*?)</title>', content)
    if title_match:
        config["description"] = title_match.group(1)

    # 映射到 FFmpeg 参数
    config["ffmpeg_params"] = _map_to_ffmpeg(config)

    return config


def _extract_css_vars(content: str) -> Dict:
    """提取 :root 中的 CSS 变量"""

    # 匹配 :root 块
    root_match = re.search(r':root\s*\{([^}]+)\}', content, re.DOTALL)

    if not root_match:
        return {}

    root_content = root_match.group(1)

    config = {}

    # 匹配每个 CSS 变量
    var_pattern = r'--([\w-]+):\s*([^;]+);'

    for match in re.finditer(var_pattern, root_content):
        var_name = match.group(1)
        var_value = match.group(2).strip()

        # 转换值类型
        config[var_name] = _convert_value(var_value)

    return config


def _convert_value(value: str) -> any:
    """转换 CSS 变量值到 Python 类型"""

    # 数字
    if re.match(r'^[\d.]+$', value):
        return float(value) if '.' in value else int(value)

    # 带单位的数字
    if re.match(r'^[\d.]+(px|s|ms)$', value):
        num = float(re.match(r'^[\d.]+', value).group())
        if value.endswith('ms'):
            return num / 1000
        return num

    # 颜色值
    if value.startswith('#') or value.startswith('rgb'):
        return value

    # 颜色带透明度 (white@0.9)
    if '@' in value and not value.startswith('#'):
        base, alpha = value.split('@')
        return {"color": base, "alpha": float(alpha)}

    # 位置值 (h-150 表示距底部 150px)
    if value.startswith('h-'):
        return {"position": "bottom", "offset": int(value[2:])}

    # 布尔值
    if value in ('true', 'false'):
        return value == 'true'

    # 列表 (逗号分隔)
    if ',' in value:
        return [v.strip() for v in value.split(',')]

    return value


def _map_to_ffmpeg(config: Dict) -> Dict:
    """映射模板配置到 FFmpeg 参数"""

    ffmpeg_params = {}

    # 字幕滤镜
    subtitle_filter = []

    fontsize = config.get("subtitle_fontsize", 42)
    fontcolor = config.get("subtitle_fontcolor", "white")

    # 处理颜色带透明度
    if isinstance(fontcolor, dict):
        color_str = f"{fontcolor['color']}@{fontcolor['alpha']}"
    else:
        color_str = fontcolor

    borderw = config.get("subtitle_borderw", 2)
    bordercolor = config.get("subtitle_bordercolor", "black@0.6")

    if isinstance(bordercolor, dict):
        bordercolor_str = f"{bordercolor['color']}@{bordercolor['alpha']}"
    else:
        bordercolor_str = bordercolor

    # 位置
    position_y = config.get("subtitle_position_y", "h-150")
    if isinstance(position_y, dict):
        y_expr = f"h-{position_y['offset']}"
    else:
        y_expr = position_y

    ffmpeg_params["subtitle"] = {
        "fontsize": fontsize,
        "fontcolor": color_str,
        "borderw": borderw,
        "bordercolor": bordercolor_str,
        "y": y_expr,
        "bold": config.get("subtitle_bold", False),
    }

    # 标题滤镜
    ffmpeg_params["title"] = {
        "fontsize": config.get("title_fontsize", 64),
        "fontcolor": config.get("title_fontcolor", "white"),
        "borderw": config.get("title_borderw", 3),
        "bordercolor": config.get("title_bordercolor", "black@0.7"),
        "y": config.get("title_position_y", 100),
        "duration": config.get("title_duration", 3),
    }

    # 转场参数
    ffmpeg_params["transition"] = {
        "type": config.get("transition_type", "fade"),
        "duration": config.get("transition_duration", 0.3),
    }

    # 尺寸
    ffmpeg_params["video"] = {
        "width": config.get("width", 1920),
        "height": config.get("height", 1080),
        "fps": config.get("fps", 30),
    }

    # 图片/视频模板特有参数
    if config.get("kenburns_zoom_start"):
        ffmpeg_params["kenburns"] = {
            "zoom_start": config.get("kenburns_zoom_start", 1.0),
            "zoom_end": config.get("kenburns_zoom_end", 1.15),
        }

    if config.get("video_speed"):
        ffmpeg_params["video_speed"] = config.get("video_speed", 1.0)

    if config.get("image_blur"):
        ffmpeg_params["image_blur"] = config.get("image_blur", 0)

    return ffmpeg_params


def get_template_config(template_name: str) -> Dict:
    """获取模板配置（便捷函数）

    Args:
        template_name: 模板名称（不含 .html）

    Returns:
        模板配置字典
    """
    template_path = TEMPLATE_DIR / f"{template_name}.html"
    return parse_template(template_path)


def apply_template_to_render_config(render_config: Dict, template_name: str) -> Dict:
    """应用模板到渲染配置

    Args:
        render_config: 原始渲染配置
        template_name: 模板名称

    Returns:
        合并后的渲染配置
    """
    template_config = get_template_config(template_name)
    ffmpeg_params = template_config.get("ffmpeg_params", {})

    # 合并尺寸
    if "video" in ffmpeg_params:
        render_config["width"] = ffmpeg_params["video"].get("width", 1920)
        render_config["height"] = ffmpeg_params["video"].get("height", 1080)
        render_config["fps"] = ffmpeg_params["video"].get("fps", 30)

    # 合并转场
    if "transition" in ffmpeg_params:
        trans_type = ffmpeg_params["transition"]["type"]
        trans_duration = ffmpeg_params["transition"]["duration"]

        for trans in render_config.get("transitions", []):
            trans["transition_out"] = trans_type
            trans["transition_duration"] = trans_duration

    # 存储字幕/标题样式供渲染器使用
    render_config["template_styles"] = ffmpeg_params

    return render_config


def main():
    parser = argparse.ArgumentParser(description="视频模板引擎")
    parser.add_argument("--list", action="store_true", help="列出所有模板")
    parser.add_argument("--category", default=None, choices=["static", "image", "video"],
                        help="过滤模板类别")
    parser.add_argument("--template", default=None, help="解析指定模板")
    parser.add_argument("--output", default=None, help="输出 JSON 文件路径")
    args = parser.parse_args()

    if args.list:
        templates = list_templates(args.category)
        print(json.dumps(templates, ensure_ascii=False, indent=2))
        return

    if args.template:
        config = get_template_config(args.template)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            print(f"输出已保存: {args.output}")
        else:
            print(json.dumps(config, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()