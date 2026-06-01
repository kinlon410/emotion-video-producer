#!/usr/bin/env python3
"""
用户素材分析模块 — 分析用户上传的图片/视频，生成匹配的文案脚本

支持：
1. 图片分析: 使用 AI 视觉模型分析内容、情感、场景
2. 视频分析: 提取关键帧 + AI 分析画面内容
3. 脚本生成: 基于素材内容生成匹配的叙事文案

用法:
    python3 -m core.user_asset_analyzer --asset image.jpg --output analysis.json
    python3 -m core.user_asset_analyzer --asset video.mp4 --output analysis.json
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from config import DASHSCOPE_API_KEY
from core.logging_config import get_logger

logger = get_logger("user_asset_analyzer")


@dataclass
class AssetAnalysis:
    """素材分析结果"""
    asset_type: str  # image/video
    asset_path: str
    duration: float = 0.0  # 视频时长

    # 视觉分析结果
    content_description: str = ""  # 内容描述
    scene_type: str = ""  # 场景类型 (城市/自然/人物/抽象...)
    emotion_tags: List[str] = []  # 情感标签 (温暖/冷峻/动感/宁静...)
    color_palette: List[str] = []  # 主要颜色
    objects: List[str] = []  # 检测到的物体
    style_tags: List[str] = []  # 风格标签 (电影感/纪实/动漫...)

    # 生成的脚本建议
    suggested_keywords: List[str] = []  # 建议的视觉关键词
    suggested_narration: str = ""  # 建议的旁白文案
    suggested_style: str = ""  # 建议的风格预设


def analyze_image(image_path: str, output_json: Optional[str] = None) -> AssetAnalysis:
    """分析图片素材

    Args:
        image_path: 图片文件路径
        output_json: 输出 JSON 文件路径（可选）

    Returns:
        AssetAnalysis: 分析结果
    """
    logger.info(f"分析图片: {image_path}")

    analysis = AssetAnalysis(
        asset_type="image",
        asset_path=image_path,
    )

    if not DASHSCOPE_API_KEY:
        logger.warning("DASHSCOPE_API_KEY 未设置，使用本地分析")
        return _fallback_image_analysis(image_path, analysis)

    # 使用 AI 视觉模型分析
    try:
        result = _call_vision_api(image_path)

        if result:
            analysis.content_description = result.get("description", "")
            analysis.scene_type = result.get("scene_type", "")
            analysis.emotion_tags = result.get("emotion_tags", [])
            analysis.color_palette = result.get("color_palette", [])
            analysis.objects = result.get("objects", [])
            analysis.style_tags = result.get("style_tags", [])

            # 生成脚本建议
            analysis.suggested_keywords = _generate_keywords(result)
            analysis.suggested_narration = _generate_narration(result)
            analysis.suggested_style = _suggest_style(result)

    except Exception as e:
        logger.error(f"AI 分析失败: {e}")
        return _fallback_image_analysis(image_path, analysis)

    # 保存结果
    if output_json:
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(asdict(analysis), f, ensure_ascii=False, indent=2)
        logger.info(f"分析结果已保存: {output_json}")

    return analysis


def analyze_video(video_path: str, output_json: Optional[str] = None,
                   keyframe_count: int = 5) -> AssetAnalysis:
    """分析视频素材

    Args:
        video_path: 视频文件路径
        output_json: 输出 JSON 文件路径（可选）
        keyframe_count: 关键帧提取数量

    Returns:
        AssetAnalysis: 分析结果
    """
    logger.info(f"分析视频: {video_path}")

    analysis = AssetAnalysis(
        asset_type="video",
        asset_path=video_path,
    )

    # 获取视频时长
    analysis.duration = _get_video_duration(video_path)

    if not DASHSCOPE_API_KEY:
        logger.warning("DASHSCOPE_API_KEY 未设置，使用本地分析")
        return _fallback_video_analysis(video_path, analysis)

    # 提取关键帧
    keyframes = _extract_keyframes(video_path, keyframe_count)

    if not keyframes:
        logger.warning("关键帧提取失败")
        return _fallback_video_analysis(video_path, analysis)

    # 分析每个关键帧
    frame_results = []
    for frame_path in keyframes:
        try:
            result = _call_vision_api(frame_path)
            if result:
                frame_results.append(result)
        except Exception as e:
            logger.warning(f"关键帧分析失败: {e}")

    if not frame_results:
        return _fallback_video_analysis(video_path, analysis)

    # 合并分析结果
    combined_result = _combine_frame_results(frame_results)

    analysis.content_description = combined_result.get("description", "")
    analysis.scene_type = combined_result.get("scene_type", "")
    analysis.emotion_tags = combined_result.get("emotion_tags", [])
    analysis.color_palette = combined_result.get("color_palette", [])
    analysis.objects = combined_result.get("objects", [])
    analysis.style_tags = combined_result.get("style_tags", [])

    # 生成脚本建议
    analysis.suggested_keywords = _generate_keywords(combined_result)
    analysis.suggested_narration = _generate_narration(combined_result)
    analysis.suggested_style = _suggest_style(combined_result)

    # 清理关键帧
    for frame_path in keyframes:
        try:
            os.remove(frame_path)
        except Exception:
            pass

    # 保存结果
    if output_json:
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(asdict(analysis), f, ensure_ascii=False, indent=2)
        logger.info(f"分析结果已保存: {output_json}")

    return analysis


def _call_vision_api(image_path: str) -> Optional[Dict]:
    """调用 AI 视觉模型分析图片"""

    import urllib.request
    import base64

    # 读取图片并编码
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    # 判断图片格式
    ext = Path(image_path).suffix.lower()
    if ext in [".jpg", ".jpeg"]:
        mime_type = "image/jpeg"
    elif ext == ".png":
        mime_type = "image/png"
    elif ext == ".webp":
        mime_type = "image/webp"
    else:
        mime_type = "image/jpeg"

    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

    prompt = """分析这张图片，以 JSON 格式输出以下信息：
{
    "description": "简短描述图片内容（20-30字）",
    "scene_type": "场景类型（城市/自然/人物/建筑/抽象/夜景/日出/日落/水面/天空）",
    "emotion_tags": ["情感标签，如温暖/冷峻/动感/宁静/神秘/欢快/忧伤"],
    "color_palette": ["主要颜色（3-5个）"],
    "objects": ["检测到的关键物体"],
    "style_tags": ["风格标签，如电影感/纪实/动漫/复古/现代"]
}"""

    payload = json.dumps({
        "model": "qwen-vl-plus",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_data}"}}
                ]
            }
        ]
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DASHSCOPE_API_KEY}"
        },
        method="POST"
    )

    try:
        response = urllib.request.urlopen(req, timeout=60)
        result_data = json.loads(response.read().decode("utf-8"))

        full_text = result_data["choices"][0].get("message", {}).get("content", [])

        # 解析 content（可能是数组）
        if isinstance(full_text, list):
            full_text = "".join([c.get("text", "") for c in full_text if c.get("type") == "text"])

        # 提取 JSON
        json_start = full_text.find("{")
        json_end = full_text.rfind("}") + 1

        if json_start >= 0 and json_end > json_start:
            return json.loads(full_text[json_start:json_end])

    except Exception as e:
        logger.error(f"视觉 API 调用失败: {e}")

    return None


def _extract_keyframes(video_path: str, count: int = 5) -> List[str]:
    """提取视频关键帧"""

    duration = _get_video_duration(video_path)

    if duration <= 0:
        return []

    # 计算关键帧时间点
    intervals = [duration * i / (count + 1) for i in range(1, count + 1)]

    keyframes = []
    temp_dir = tempfile.mkdtemp()

    for i, time in enumerate(intervals):
        frame_path = os.path.join(temp_dir, f"frame_{i}.jpg")

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-ss", str(time),
            "-vframes", "1",
            "-q:v", "2",
            frame_path
        ]

        try:
            subprocess.run(cmd, capture_output=True, timeout=30, check=True)
            keyframes.append(frame_path)
        except Exception as e:
            logger.warning(f"关键帧提取失败 (time={time}): {e}")

    return keyframes


def _get_video_duration(video_path: str) -> float:
    """获取视频时长"""

    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        video_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception:
        pass

    return 0.0


def _combine_frame_results(frame_results: List[Dict]) -> Dict:
    """合并多个关键帧的分析结果"""

    combined = {
        "description": "",
        "scene_type": "",
        "emotion_tags": [],
        "color_palette": [],
        "objects": [],
        "style_tags": [],
    }

    # 使用第一个帧的描述
    if frame_results:
        combined["description"] = frame_results[0].get("description", "")

    # 合并所有标签（去重）
    for result in frame_results:
        for tag in result.get("emotion_tags", []):
            if tag not in combined["emotion_tags"]:
                combined["emotion_tags"].append(tag)

        for color in result.get("color_palette", []):
            if color not in combined["color_palette"]:
                combined["color_palette"].append(color)

        for obj in result.get("objects", []):
            if obj not in combined["objects"]:
                combined["objects"].append(obj)

        for style in result.get("style_tags", []):
            if style not in combined["style_tags"]:
                combined["style_tags"].append(style)

    # 统计场景类型（取最常见的）
    scene_types = [r.get("scene_type", "") for r in frame_results]
    if scene_types:
        combined["scene_type"] = scene_types[0]

    return combined


def _generate_keywords(result: Dict) -> List[str]:
    """根据分析结果生成搜索关键词"""

    keywords = []

    # 场景类型作为关键词
    scene = result.get("scene_type", "")
    if scene:
        keywords.append(scene)

    # 物体作为关键词
    objects = result.get("objects", [])
    keywords.extend(objects[:3])

    # 情感标签翻译为英文关键词
    emotion_map = {
        "温暖": "warm",
        "冷峻": "cold",
        "动感": "dynamic",
        "宁静": "peaceful",
        "神秘": "mysterious",
        "欢快": "happy",
        "忧伤": "sad",
        "城市": "city",
        "自然": "nature",
        "夜景": "night",
        "日出": "sunrise",
        "日落": "sunset",
    }

    for tag in result.get("emotion_tags", []):
        en_keyword = emotion_map.get(tag, tag)
        keywords.append(en_keyword)

    return keywords[:5]


def _generate_narration(result: Dict) -> str:
    """根据分析结果生成旁白文案"""

    description = result.get("description", "")
    scene = result.get("scene_type", "")
    emotions = result.get("emotion_tags", [])

    # 简单的模板生成
    templates = {
        "城市": "繁华的都市，承载着无数故事",
        "自然": "自然的气息，洗涤着心灵",
        "夜景": "夜幕降临，城市开始苏醒",
        "日出": "黎明破晓，希望升起",
        "日落": "夕阳西下，时光流转",
        "水面": "水波荡漾，心随波动",
        "天空": "仰望天空，无限遐想",
    }

    if scene in templates:
        return templates[scene]

    if description:
        return f"画面中：{description}"

    return "这一刻，值得被记住"


def _suggest_style(result: Dict) -> str:
    """根据分析结果建议风格预设"""

    emotions = result.get("emotion_tags", [])
    scene = result.get("scene_type", "")

    # 情感映射到风格
    style_map = {
        "动感": "热血",
        "欢快": "欢快",
        "温暖": "治愈",
        "宁静": "治愈",
        "神秘": "文艺",
        "忧伤": "治愈",
        "冷峻": "文艺",
    }

    for emotion in emotions:
        if emotion in style_map:
            return style_map[emotion]

    # 场景映射到风格
    scene_style_map = {
        "城市": "励志",
        "夜景": "热血",
        "日出": "励志",
        "日落": "文艺",
        "自然": "治愈",
        "水面": "治愈",
        "天空": "文艺",
    }

    if scene in scene_style_map:
        return scene_style_map[scene]

    return "励志"


def _fallback_image_analysis(image_path: str, analysis: AssetAnalysis) -> AssetAnalysis:
    """图片备用分析（无 AI）"""

    # 使用图片文件名作为描述
    filename = Path(image_path).stem
    analysis.content_description = f"图片：{filename}"

    # 默认值
    analysis.scene_type = "未知"
    analysis.emotion_tags = ["通用"]
    analysis.suggested_keywords = ["generic"]
    analysis.suggested_narration = "这是上传的图片素材"
    analysis.suggested_style = "励志"

    return analysis


def _fallback_video_analysis(video_path: str, analysis: AssetAnalysis) -> AssetAnalysis:
    """视频备用分析（无 AI）"""

    filename = Path(video_path).stem
    analysis.content_description = f"视频：{filename}"

    analysis.scene_type = "未知"
    analysis.emotion_tags = ["通用"]
    analysis.suggested_keywords = ["generic"]
    analysis.suggested_narration = "这是上传的视频素材"
    analysis.suggested_style = "励志"

    return analysis


def generate_script_from_assets(analyses: List[AssetAnalysis], theme: str) -> Dict:
    """根据多个素材分析结果生成完整脚本

    Args:
        analyses: 素材分析结果列表
        theme: 视频主题

    Returns:
        dict: 生成的脚本 {"narration_script": "...", "segment_narrations": [...]}
    """
    logger.info(f"根据 {len(analyses)} 个素材生成脚本")

    # 收集所有描述和情感
    descriptions = [a.content_description for a in analyses]
    all_emotions = []
    for a in analyses:
        all_emotions.extend(a.emotion_tags)

    # 确定主导风格
    if analyses:
        dominant_style = analyses[0].suggested_style
    else:
        dominant_style = "励志"

    # 构建脚本
    if DASHSCOPE_API_KEY:
        try:
            script = _call_script_generation_api(theme, descriptions, all_emotions, dominant_style)
            if script:
                return script
        except Exception as e:
            logger.error(f"脚本生成 API 调用失败: {e}")

    # 备用生成
    return _fallback_script_generation(theme, analyses)


def _call_script_generation_api(theme: str, descriptions: List[str],
                                  emotions: List[str], style: str) -> Optional[Dict]:
    """调用 AI 生成脚本"""

    import urllib.request

    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

    prompt = f"""根据以下素材内容，为视频主题 "{theme}" 生成叙事脚本。

素材描述：
{json.dumps(descriptions, ensure_ascii=False)}

情感标签：
{json.dumps(emotions, ensure_ascii=False)}

风格要求：{style}

请以 JSON 格式输出：
{
    "narration_script": "完整旁白文案（30-50字）",
    "segment_narrations": [
        {"segment_index": 0, "text": "第一段旁白"},
        {"segment_index": 1, "text": "第二段旁白"},
        ...
    ]
}"""

    payload = json.dumps({
        "model": "qwen-plus",
        "max_tokens": 500,
        "messages": [
            {"role": "system", "content": "你是 CutClaw 视频脚本生成器，根据素材内容创作简洁有力的旁白文案。"},
            {"role": "user", "content": prompt}
        ]
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DASHSCOPE_API_KEY}"
        },
        method="POST"
    )

    try:
        response = urllib.request.urlopen(req, timeout=60)
        result_data = json.loads(response.read().decode("utf-8"))

        full_text = result_data["choices"][0].get("message", {}).get("content", "")

        json_start = full_text.find("{")
        json_end = full_text.rfind("}") + 1

        if json_start >= 0 and json_end > json_start:
            return json.loads(full_text[json_start:json_end])

    except Exception as e:
        logger.error(f"脚本生成失败: {e}")

    return None


def _fallback_script_generation(theme: str, analyses: List[AssetAnalysis]) -> Dict:
    """备用脚本生成"""

    narration_parts = []

    for i, a in enumerate(analyses):
        narration_parts.append(a.suggested_narration)

    full_narration = " ".join(narration_parts)

    segment_narrations = [
        {"segment_index": i, "text": a.suggested_narration}
        for i, a in enumerate(analyses)
    ]

    return {
        "narration_script": f"{theme}，{full_narration}",
        "segment_narrations": segment_narrations,
    }


def main():
    parser = argparse.ArgumentParser(description="用户素材分析模块")
    parser.add_argument("--asset", required=True, help="素材文件路径（图片或视频）")
    parser.add_argument("--output", default=None, help="输出 JSON 文件路径")
    parser.add_argument("--keyframes", type=int, default=5, help="视频关键帧数量")
    args = parser.parse_args()

    asset_path = args.asset

    if not os.path.exists(asset_path):
        print(f"[Error] 素材文件不存在: {asset_path}", file=sys.stderr)
        sys.exit(1)

    # 判断素材类型
    ext = Path(asset_path).suffix.lower()
    if ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
        analysis = analyze_image(asset_path, args.output)
    elif ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
        analysis = analyze_video(asset_path, args.output, args.keyframes)
    else:
        print(f"[Error] 不支持的素材格式: {ext}", file=sys.stderr)
        sys.exit(1)

    if args.output is None:
        print(json.dumps(asdict(analysis), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()