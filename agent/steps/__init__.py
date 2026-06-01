#!/usr/bin/env python3
"""
独立步骤函数 — 拆分 producer.py 为可独立调用的步骤

每个步骤：
1. 有明确的输入参数（Pydantic schema）
2. 返回明确的结果
3. 可独立调用，支持部分重做
"""

import json
import os
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any

from core.logging_config import get_logger
from core.exceptions import (
    AudioNotFoundError, RenderError, FFmpegError,
    DownloadError, NetworkError
)

logger = get_logger("steps")


def step1_analyze(bgm_path: str, output_json: str = None) -> Dict[str, Any]:
    """Step 1: 音乐情感分析

    Args:
        bgm_path: BGM 音频文件路径
        output_json: 输出 JSON 文件路径（可选）

    Returns:
        音乐分析结果字典
    """
    logger.info(f"[Step 1] 音乐情感分析: {bgm_path}")

    if not os.path.exists(bgm_path):
        raise AudioNotFoundError(f"BGM 文件不存在: {bgm_path}")

    from core.music_analyzer import analyze_music
    analysis = analyze_music(bgm_path, output_json)

    if analysis is None:
        raise RenderError("音乐分析失败")

    logger.info(f"  完成: BPM={analysis.get('bpm')}, 结构段数={len(analysis.get('structure', []))}")
    return analysis


def step2_narrative(
    theme: str,
    analysis: Dict[str, Any],
    style: str = None,
    output_json: str = None,
    style_profile: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Step 2: AI 叙事生成

    Args:
        theme: 视频主题
        analysis: 音乐分析结果
        style: 风格预设（可选）
        output_json: 输出 JSON 文件路径（可选）
        style_profile: 风格分析结果（用于 few-shot，可选）

    Returns:
        叙事脚本结果字典
    """
    logger.info(f"[Step 2] AI 叙事生成: {theme}")

    from core.narrative_generator import generate_narrative

    # 如果有风格 profile，传递给生成器实现风格迁移
    if style_profile:
        logger.info(f"  应用风格 profile: tags={style_profile.get('style_tags', [])}")

    narrative = generate_narrative(theme, analysis, style, output_json, style_profile)

    if narrative is None:
        raise RenderError("叙事生成失败")

    logger.info(f"  完成: 标题={narrative.get('title_text')}")
    return narrative


def step3_visual_select(
    analysis: Dict[str, Any],
    segment_count: int = 7,
    output_json: str = None
) -> List[Dict[str, Any]]:
    """Step 3: 视觉素材选择

    Args:
        analysis: 音乐分析结果
        segment_count: 目标片段数量
        output_json: 输出 JSON 文件路径（可选）

    Returns:
        视觉选择结果列表
    """
    logger.info(f"[Step 3] 视觉素材选择: {segment_count} 段")

    from core.visual_selector import select_visuals
    visuals = select_visuals(analysis, segment_count, output_json)

    logger.info(f"  完成: {len(visuals)} 个视觉片段")
    return visuals


def step4_transition(
    analysis: Dict[str, Any],
    visuals: List[Dict[str, Any]],
    output_json: str = None
) -> List[Dict[str, Any]]:
    """Step 4: 转场映射

    Args:
        analysis: 音乐分析结果
        visuals: 视觉选择结果
        output_json: 输出 JSON 文件路径（可选）

    Returns:
        转场配置列表
    """
    logger.info(f"[Step 4] 转场效果映射")

    from core.transition_mapper import map_transitions
    transitions = map_transitions(analysis, visuals, output_json)

    logger.info(f"  完成: {len(transitions)} 个转场")
    return transitions


def step5_subtitle(
    analysis: Dict[str, Any],
    narrative: Dict[str, Any],
    output_json: str = None,
    narration_duration: float = None,
    asr_result: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """Step 5: 字幕同步

    Args:
        analysis: 音乐分析结果
        narrative: 叙事结果
        output_json: 输出 JSON 文件路径（可选）
        narration_duration: 旁白时长（可选）
        asr_result: ASR 结果（可选）

    Returns:
        字幕配置列表
    """
    logger.info(f"[Step 5] 字幕同步")

    from core.subtitle_sync import (
        sync_subtitles, sync_subtitles_to_narration, sync_subtitles_from_asr
    )

    if asr_result and asr_result.get("segments"):
        subtitles = sync_subtitles_from_asr(
            asr_result, analysis.get("structure", []),
            max_chars=8, output_json=output_json
        )
    elif narration_duration:
        subtitles = sync_subtitles_to_narration(
            narrative, narration_duration,
            analysis.get("structure", []), output_json
        )
    else:
        subtitles = sync_subtitles(analysis, narrative, output_json)

    logger.info(f"  完成: {len(subtitles)} 条字幕")
    return subtitles


def step6_tts(
    text: str,
    output_path: str,
    voice: str = "longxiaochun",
    speed: float = 1.0
) -> Optional[str]:
    """Step 6: TTS 生成旁白

    Args:
        text: 要转换的文本
        output_path: 输出文件路径
        voice: 语音名称
        speed: 语速

    Returns:
        输出文件路径，失败返回 None
    """
    logger.info(f"[Step 6] TTS 生成旁白: {text[:30]}...")

    if not text:
        logger.info("  跳过: 无旁白文本")
        return None

    from core.tts import text_to_speech, get_audio_duration
    result = text_to_speech(text, output_path, voice, speed)

    if result:
        duration = get_audio_duration(result)
        logger.info(f"  完成: 旁白时长={duration}s")
        return result

    return None


def step7_asr(
    audio_path: str,
    language: str = "zh",
    output_json: str = None
) -> Optional[Dict[str, Any]]:
    """Step 7: ASR 语音识别

    Args:
        audio_path: 音频文件路径
        language: 语言
        output_json: 输出 JSON 文件路径（可选）

    Returns:
        ASR 结果字典，失败返回 None
    """
    logger.info(f"[Step 7] ASR 语音识别")

    if not audio_path or not os.path.exists(audio_path):
        logger.info("  跳过: 无旁白音频")
        return None

    from core.asr import transcribe
    result = transcribe(audio_path, language, output_json)

    if result:
        logger.info(f"  完成: {len(result.get('segments', []))} 个分段")
        return result

    return None


async def step8_visual_download(
    visual_queries: List[Dict[str, Any]],
    output_dir: str,
    visual_mode: str = "auto"
) -> Dict[str, str]:
    """Step 8: 视觉素材下载（async 并行）

    Args:
        visual_queries: 视觉查询列表
        output_dir: 输出目录
        visual_mode: 素材获取模式

    Returns:
        素材片段路径字典 {segment_id: file_path}
    """
    logger.info(f"[Step 8] 视觉素材下载: {len(visual_queries)} 个片段")

    import asyncio
    from core_async.visual_downloader import download_visuals_async

    clips = await download_visuals_async(visual_queries, output_dir, visual_mode)

    logger.info(f"  完成: {len(clips)} 个素材片段")
    return clips


def step9_render(
    title_text: str,
    bgm_path: str,
    narration_path: str = None,
    clips: Dict[str, str] = None,
    transitions: List[Dict[str, Any]] = None,
    subtitles: List[Dict[str, Any]] = None,
    output_path: str = "output.mp4",
    width: int = 1920,
    height: int = 1080,
    fps: int = 30
) -> Optional[str]:
    """Step 9: 视频渲染

    Args:
        title_text: 标题文本
        bgm_path: BGM 文件路径
        narration_path: 旁白文件路径（可选）
        clips: 素材片段路径字典
        transitions: 转场配置列表
        subtitles: 字幕配置列表
        output_path: 输出视频路径
        width: 视频宽度
        height: 视频高度
        fps: 帧率

    Returns:
        输出视频路径，失败返回 None
    """
    logger.info(f"[Step 9] 视频渲染: {output_path}")

    if not clips:
        raise RenderError("无素材片段")

    from core.video_renderer import render_video

    config = {
        "title_text": title_text,
        "bgm_path": bgm_path,
        "narration_path": narration_path,
        "clips": clips,
        "transitions": transitions,
        "subtitles": subtitles,
        "output_path": output_path,
        "width": width,
        "height": height,
        "fps": fps,
    }

    result = render_video(config)

    if result:
        logger.info(f"  完成: {output_path}")
        return output_path

    raise FFmpegError("视频渲染失败")


# 步骤名称映射
STEP_NAMES = {
    1: "analyze",
    2: "narrative",
    3: "visual_select",
    4: "transition",
    5: "subtitle",
    6: "tts",
    7: "asr",
    8: "visual_download",
    9: "render",
}

TOTAL_STEPS = 9