#!/usr/bin/env python3
"""
风格预设库模块 — 一键选择风格，自动调优参数

预设风格：
- 热血: 高张力阈值，激烈转场，impact 字幕
- 励志: 中张力阈值，平衡转场，minimal 字幕
- 治愈: 低张力阈值，柔和转场，minimal 字幕
- 文艺: 低张力阈值，艺术转场，cinematic 字幕
- 欢快: 中张力阈值，活泼转场，neon 字幕

用法:
    python3 -m core.style_presets --style 热血 --output preset.json
"""

import argparse
import json
from typing import Dict, Optional

from config import TRANSITION_DURATIONS, SUBTITLE_STYLES


# ── 风格预设定义 ──

STYLE_PRESETS = {
    "热血": {
        "description": "激情澎湃，节奏强烈",
        "tension_threshold": 0.75,
        "transitions": ["pixelize", "zoomin", "spinzoom", "circleopen", "wipeleft"],
        "transition_duration": 0.12,
        "subtitle_style": "impact",
        "visual_types": ["人群", "运动", "光效", "都市夜景"],
        "narration_style": {
            "chorus": "爆发式短句",
            "verse": "铺垫式描述",
            "intro": "引入氛围",
            "outro": "收束沉淀",
        },
        "color_palette": "neon",
        "bgm_style": "fast_electronic",
        "default_template": "static_impact",  # 关联默认模板
        "video_template": "video_dynamic",
    },
    "励志": {
        "description": "激励人心，正能量",
        "tension_threshold": 0.55,
        "transitions": ["circleopen", "wipeleft", "zoomin", "revealleft"],
        "transition_duration": 0.18,
        "subtitle_style": "minimal",
        "visual_types": ["城市", "行走", "地标", "日出日落"],
        "narration_style": {
            "chorus": "有力感悟",
            "verse": "温柔叙事",
            "intro": "启发开场",
            "outro": "沉淀收尾",
        },
        "color_palette": "warm",
        "bgm_style": "medium_pop",
        "default_template": "static_minimal",
        "video_template": "video_cinematic",
    },
    "治愈": {
        "description": "温柔细腻，情感共鸣",
        "tension_threshold": 0.35,
        "transitions": ["fade", "dissolve", "smoothup", "smoothdown", "radial"],
        "transition_duration": 0.35,
        "subtitle_style": "minimal",
        "visual_types": ["风景", "空镜", "自然", "水面"],
        "narration_style": {
            "chorus": "温暖高潮",
            "verse": "舒缓叙事",
            "intro": "安静开场",
            "outro": "温柔收尾",
        },
        "color_palette": "ocean",
        "bgm_style": "slow_ballad",
        "default_template": "static_minimal",
        "video_template": "video_cinematic",
    },
    "文艺": {
        "description": "诗意意境，含蓄表达",
        "tension_threshold": 0.30,
        "transitions": ["fade", "fadeblack", "dissolve", "hblur", "revealup"],
        "transition_duration": 0.40,
        "subtitle_style": "cinematic",
        "visual_types": ["天空", "月亮", "星空", "光影"],
        "narration_style": {
            "chorus": "诗意高潮",
            "verse": "含蓄叙事",
            "intro": "意境开场",
            "outro": "留白收尾",
        },
        "color_palette": "minimal",
        "bgm_style": "slow_ballad",
        "default_template": "static_cinematic",
        "video_template": "video_cinematic",
        "image_template": "image_art",
    },
    "欢快": {
        "description": "轻松愉悦，积极向上",
        "tension_threshold": 0.45,
        "transitions": ["circleopen", "slidedown", "wipeleft", "zoomin", "revealright"],
        "transition_duration": 0.15,
        "subtitle_style": "neon",
        "visual_types": ["人群", "市场", "美食", "节日"],
        "narration_style": {
            "chorus": "欢快高潮",
            "verse": "轻松叙事",
            "intro": "活跃开场",
            "outro": "愉快收尾",
        },
        "color_palette": "warm",
        "bgm_style": "medium_pop",
        "default_template": "static_impact",
        "video_template": "video_dynamic",
        "image_template": "image_photo",
    },
}


def get_style_preset(style_name: str, output_json: Optional[str] = None) -> Dict:
    """获取风格预设配置

    Args:
        style_name: 风格名称
        output_json: 输出 JSON 文件路径（可选）

    Returns:
        dict: 风格预设配置
    """
    preset = STYLE_PRESETS.get(style_name, STYLE_PRESETS["励志"])

    print(f"[style_presets] 获取风格预设: {style_name}")

    # 补充字幕样式详情
    preset["subtitle_style_config"] = SUBTITLE_STYLES.get(
        preset["subtitle_style"],
        SUBTITLE_STYLES["minimal"]
    )

    # 保存 JSON
    if output_json:
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(preset, f, ensure_ascii=False, indent=2)
        print(f"  输出已保存: {output_json}")

    return preset


def list_styles() -> list:
    """列出所有可用风格"""

    return [
        {
            "name": name,
            "description": preset["description"],
        }
        for name, preset in STYLE_PRESETS.items()
    ]


def apply_preset_to_analysis(analysis: Dict, preset_name: str) -> Dict:
    """将风格预设应用到分析结果

    Args:
        analysis: 音乐情感分析结果
        preset_name: 风格名称

    Returns:
        dict: 调整后的分析结果
    """
    preset = get_style_preset(preset_name)

    # 调整张力阈值
    tension_threshold = preset["tension_threshold"]

    # 重新检测张力峰值
    emotion_curve = analysis.get("emotion_curve", [])
    tension_peaks = []

    for i in range(1, len(emotion_curve) - 1):
        prev_val = emotion_curve[i - 1]["value"]
        curr_val = emotion_curve[i]["value"]
        next_val = emotion_curve[i + 1]["value"]

        if curr_val > prev_val and curr_val > next_val and curr_val >= tension_threshold:
            tension_peaks.append(emotion_curve[i]["time"])

    # 更新分析结果
    analysis["tension_peaks"] = tension_peaks
    analysis["applied_style"] = preset_name
    analysis["style_config"] = preset

    return analysis


def main():
    parser = argparse.ArgumentParser(description="风格预设库模块")
    parser.add_argument("--style", required=True, help="风格名称")
    parser.add_argument("--output", default=None, help="输出 JSON 文件路径")
    parser.add_argument("--list", action="store_true", help="列出所有风格")
    args = parser.parse_args()

    if args.list:
        styles = list_styles()
        print(json.dumps(styles, ensure_ascii=False, indent=2))
        return

    preset = get_style_preset(args.style, args.output)

    if args.output is None:
        print(json.dumps(preset, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()