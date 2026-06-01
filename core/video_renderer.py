#!/usr/bin/env python3
"""
视频渲染模块 — 使用 FFmpeg xfade 转场合成视频

支持:
- 多片段 xfade 转场合成
- 字幕叠加（中英双语）
- BGM + 旁白混音
- 标题/水印叠加
- 动态字幕样式

用法:
    python3 -m core.video_renderer --config render_config.json --output output.mp4
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from config import (
    DEFAULT_WIDTH,
    DEFAULT_HEIGHT,
    DEFAULT_FPS,
    FONT_PATH,
    FONT_FALLBACK,
)


def _build_subtitle_filter(sub: Dict, template_styles: Optional[Dict] = None) -> str:
    """构建字幕滤镜，支持模板样式

    Args:
        sub: 字幕配置 {"text_zh", "text_en", "start", "end"}
        template_styles: 模板样式配置（可选）

    Returns:
        FFmpeg drawtext 滤镜字符串
    """
    text_zh = sub.get("text_zh", "")
    text_en = sub.get("text_en", "")
    start = sub.get("start", 0)
    end = sub.get("end", 0)

    # 获取模板样式或默认值
    if template_styles and "subtitle" in template_styles:
        style = template_styles["subtitle"]
        fontsize = style.get("fontsize", 42)
        fontcolor = style.get("fontcolor", "white")
        borderw = style.get("borderw", 2)
        bordercolor = style.get("bordercolor", "black@0.6")
        y_expr = style.get("y", "h-150")
        bold = style.get("bold", False)
    else:
        fontsize = 42
        fontcolor = "white"
        borderw = 2
        bordercolor = "black@0.6"
        y_expr = "h-150"
        bold = False

    filters = []

    if text_zh:
        enable = f"between(t,{start},{end})"
        bold_param = ":fontcolor_bold=1" if bold else ""
        filters.append(
            f"drawtext=text='{text_zh}':fontfile='{FONT_PATH}':fontsize={fontsize}:fontcolor={fontcolor}:borderw={borderw}:bordercolor={bordercolor}:x=(w-text_w)/2:y={y_expr}:enable='{enable}'{bold_param}"
        )

    if text_en:
        enable = f"between(t,{start},{end})"
        # 英文字幕在中文上方
        filters.append(
            f"drawtext=text='{text_en}':fontfile='{FONT_FALLBACK}':fontsize={fontsize-14}:fontcolor={fontcolor}@0.7:borderw={borderw-1}:bordercolor={bordercolor}:x=(w-text_w)/2:y={y_expr}-50:enable='{enable}'"
        )

    return ",".join(filters) if filters else ""


def _build_title_filter(title_text: str, template_styles: Optional[Dict] = None) -> str:
    """构建标题滤镜，支持模板样式

    Args:
        title_text: 标题文字
        template_styles: 模板样式配置（可选）

    Returns:
        FFmpeg drawtext 滤镜字符串
    """
    if not title_text:
        return ""

    if template_styles and "title" in template_styles:
        style = template_styles["title"]
        fontsize = style.get("fontsize", 64)
        fontcolor = style.get("fontcolor", "white")
        borderw = style.get("borderw", 3)
        bordercolor = style.get("bordercolor", "black@0.7")
        y_pos = style.get("y", 100)
        duration = style.get("duration", 3)
    else:
        fontsize = 64
        fontcolor = "white"
        borderw = 3
        bordercolor = "black@0.7"
        y_pos = 100
        duration = 3

    return f"drawtext=text='{title_text}':fontfile='{FONT_PATH}':fontsize={fontsize}:fontcolor={fontcolor}:borderw={borderw}:bordercolor={bordercolor}:x=(w-text_w)/2:y={y_pos}:enable='between(t,0,{duration})'"


# ── FFmpeg xfade 转场效果映射 ──

XFADE_EFFECTS = {
    "fade": "fade",
    "fadeblack": "fadeblack",
    "dissolve": "dissolve",
    "wipeleft": "wipeleft",
    "wiperight": "wiperight",
    "wipeup": "wipeup",
    "wipedown": "wipedown",
    "slideleft": "slideleft",
    "slideright": "slideright",
    "slideup": "slideup",
    "slidedown": "slidedown",
    "circleopen": "circleopen",
    "circleclose": "circleclose",
    "rectcrop": "rectcrop",
    "pixelize": "pixelize",
    "distance": "distance",
    "diag1": "diag1",
    "diag2": "diag2",
    "diag3": "diag3",
    "hblur": "hblur",
    "vblur": "vblur",
    "zoomin": "zoomin",
    "zoomout": "zoomout",
    "coverleft": "coverleft",
    "coverright": "coverright",
    "revealleft": "revealleft",
    "revealright": "revealright",
    "revealup": "revealup",
    "revealdown": "revealdown",
    "radial": "radial",
    "smoothup": "smoothup",
    "smoothdown": "smoothdown",
}


def render_video(
    clips: List[str],
    transitions: List[Dict],
    subtitles: List[Dict],
    bgm_path: str,
    output_path: str,
    title_text: Optional[str] = None,
    narration_path: Optional[str] = None,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    fps: int = DEFAULT_FPS,
    bgm_volume: float = 0.6,
    narration_volume: float = 1.0,
    template_styles: Optional[Dict] = None,
) -> bool:
    """渲染视频

    Args:
        clips: 视频片段路径列表
        transitions: 转场配置列表 [{"type": "fade", "duration": 0.3}, ...]
        subtitles: 字幕列表 [{"text_zh": "...", "text_en": "...", "start": N, "end": N}, ...]
        bgm_path: BGM 文件路径
        output_path: 输出视频路径
        title_text: 标题文字（可选）
        narration_path: 旁白文件路径（可选）
        width, height, fps: 输出规格
        bgm_volume: BGM 音量 (0-1)
        narration_volume: 旁白音量 (0-1)
        template_styles: 模板样式配置（可选）

    Returns:
        bool: 成功返回 True
    """
    print(f"[video_renderer] 渲染视频...")
    print(f"  片段数: {len(clips)}")
    print(f"  输出规格: {width}x{height} @ {fps}fps")

    if len(clips) == 0:
        print("[Error] 无素材片段", file=sys.stderr)
        return False

    # ── Step 1: 获取片段信息 ──

    clip_info = []
    for clip_path in clips:
        info = get_clip_info(clip_path)
        clip_info.append(info)

    total_duration = sum(info["duration"] for info in clip_info)
    print(f"  总时长: {total_duration:.1f}s")

    # ── Step 2: 构建 xfade 滤镜链 ──

    if len(clips) == 1:
        # 单片段：直接处理
        filter_complex = _build_single_clip_filter(
            clips[0], subtitles, title_text, width, height, template_styles
        )
        return _render_single_clip(
            clips[0], bgm_path, narration_path, output_path,
            filter_complex, bgm_volume, narration_volume
        )

    # 多片段：使用 xfade 转场
    filter_complex = _build_xfade_filter_chain(
        clips, clip_info, transitions, subtitles, title_text, width, height, template_styles
    )

    # ── Step 3: 构建完整渲染命令 ──

    cmd = _build_render_command(
        clips, bgm_path, narration_path, output_path,
        filter_complex, width, height, fps, bgm_volume, narration_volume
    )

    # ── Step 4: 执行渲染 ──

    try:
        result = subprocess.run(
            cmd, capture_output=True, timeout=600, check=True
        )
        print(f"  ✓ 渲染完成: {output_path}")
        return True

    except subprocess.TimeoutExpired:
        print("[Error] 渲染超时", file=sys.stderr)
        return False

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode("utf-8", errors="replace")[:500]
        print(f"[Error] 渲染失败: {error_msg}", file=sys.stderr)
        return False


def get_clip_info(clip_path: str) -> Dict:
    """获取视频片段信息"""

    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration:stream=width,height",
        "-of", "json",
        clip_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        data = json.loads(result.stdout)

        duration = float(data.get("format", {}).get("duration", 0))

        # 获取视频流信息
        streams = data.get("streams", [])
        width = 1920
        height = 1080

        for s in streams:
            if s.get("width"):
                width = s["width"]
                height = s["height"]
                break

        return {
            "path": clip_path,
            "duration": duration,
            "width": width,
            "height": height,
        }

    except Exception:
        return {
            "path": clip_path,
            "duration": 3.0,
            "width": 1920,
            "height": 1080,
        }


def _build_single_clip_filter(
    clip_path: str,
    subtitles: List[Dict],
    title_text: Optional[str],
    width: int,
    height: int,
    template_styles: Optional[Dict] = None,
) -> str:
    """构建单片段滤镜，支持模板样式"""

    filters = [
        f"scale={width}:{height}:force_original_aspect_ratio=decrease",
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
        "format=yuv420p",
    ]

    # 字幕
    if subtitles:
        subtitle_strs = []
        for sub in subtitles:
            sub_filter = _build_subtitle_filter(sub, template_styles)
            if sub_filter:
                subtitle_strs.append(sub_filter)

        if subtitle_strs:
            filters.extend(subtitle_strs)

    # 标题
    if title_text:
        title_filter = _build_title_filter(title_text, template_styles)
        if title_filter:
            filters.append(title_filter)

    return ",".join(filters)


def _build_xfade_filter_chain(
    clips: List[str],
    clip_info: List[Dict],
    transitions: List[Dict],
    subtitles: List[Dict],
    title_text: Optional[str],
    width: int,
    height: int,
    template_styles: Optional[Dict] = None,
) -> str:
    """构建 xfade 转场滤镜链，支持模板样式"""

    n_clips = len(clips)

    # 构建 filter_complex
    filter_parts = []

    # 输入标签
    inputs = []
    for i, info in enumerate(clip_info):
        inputs.append(f"[{i}:v]")

    # 第一步：缩放所有片段
    for i in range(n_clips):
        filter_parts.append(
            f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
            f"format=yuv420p[v{i}]"
        )

    # 第二步：xfade 转场链
    # 计算转场偏移 (xfade 的 offset 是相对于第一个输入的时间点)
    # 正确公式: offset_N = sum(duration_1..duration_N) - N * trans_duration
    offsets = []
    cumulative_duration = 0.0

    for i in range(n_clips - 1):
        info = clip_info[i]
        trans = transitions[i] if i < len(transitions) else {"type": "fade", "duration": 0.3}

        trans_duration = trans.get("transition_duration", 0.3)

        # 累加当前片段时长
        cumulative_duration += info["duration"]

        # xfade 偏移 = 累计时长 - 转场时长
        # 这样转场会在当前片段的末尾开始
        offset = cumulative_duration - trans_duration

        # 确保 offset 不为负数
        if offset < 0:
            offset = 0
            trans_duration = min(trans_duration, cumulative_duration)

        offsets.append(offset)

    # 构建 xfade 链
    prev_label = "v0"

    for i in range(n_clips - 1):
        trans = transitions[i] if i < len(transitions) else {"type": "fade", "duration": 0.3}
        trans_type = trans.get("transition_out", "fade")
        trans_duration = trans.get("transition_duration", 0.3)

        xfade_type = XFADE_EFFECTS.get(trans_type, "fade")
        next_label = f"v{i+1}"
        out_label = f"xf{i}" if i < n_clips - 2 else "final"

        filter_parts.append(
            f"[{prev_label}][{next_label}]xfade=transition={xfade_type}:"
            f"duration={trans_duration}:offset={offsets[i]:.2f}[{out_label}]"
        )

        prev_label = out_label

    # 第三步：添加字幕和标题
    final_filters = []

    if subtitles:
        # 创建字幕滤镜
        subtitle_strs = []
        for sub in subtitles:
            sub_filter = _build_subtitle_filter(sub, template_styles)
            if sub_filter:
                subtitle_strs.append(sub_filter)

        if subtitle_strs:
            final_filters.extend(subtitle_strs)

    if title_text:
        title_filter = _build_title_filter(title_text, template_styles)
        if title_filter:
            final_filters.append(title_filter)

    if final_filters:
        filter_parts.append(
            f"[final]{','.join(final_filters)}[outv]"
        )
    else:
        filter_parts.append("[final]null[outv]")

    return ";".join(filter_parts)


def _build_render_command(
    clips: List[str],
    bgm_path: str,
    narration_path: Optional[str],
    output_path: str,
    filter_complex: str,
    width: int,
    height: int,
    fps: int,
    bgm_volume: float,
    narration_volume: float,
) -> List[str]:
    """构建 FFmpeg 渲染命令"""

    cmd = ["ffmpeg", "-y"]

    # 输入所有视频片段
    for clip in clips:
        cmd.extend(["-i", clip])

    # 输入 BGM
    cmd.extend(["-i", bgm_path])

    # 输入旁白
    input_count = len(clips) + 1
    if narration_path and os.path.exists(narration_path):
        cmd.extend(["-i", narration_path])
        input_count += 1

    # 滤镜
    cmd.extend(["-filter_complex", filter_complex])

    # 视频编码
    cmd.extend([
        "-map", "[outv]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
    ])

    # 音频混音
    bgm_idx = len(clips)
    if narration_path and os.path.exists(narration_path):
        narration_idx = len(clips) + 1
        cmd.extend([
            "-filter_complex",
            f"[{bgm_idx}:a]volume={bgm_volume}[bgm];"
            f"[{narration_idx}:a]volume={narration_volume}[narr];"
            f"[bgm][narr]amix=inputs=2:duration=longest:dropout_transition=2[aout]",
            "-map", "[aout]",
        ])
    else:
        cmd.extend([
            "-map", f"{bgm_idx}:a",
            "-af", f"volume={bgm_volume}",
        ])

    # 音频编码
    cmd.extend([
        "-c:a", "aac",
        "-b:a", "128k",
    ])

    # 输出
    cmd.extend([
        "-movflags", "+faststart",
        "-shortest",
        output_path
    ])

    return cmd


def _render_single_clip(
    clip_path: str,
    bgm_path: str,
    narration_path: Optional[str],
    output_path: str,
    filter_complex: str,
    bgm_volume: float,
    narration_volume: float,
) -> bool:
    """渲染单片段视频"""

    cmd = ["ffmpeg", "-y"]

    # 输入
    cmd.extend(["-i", clip_path])
    cmd.extend(["-i", bgm_path])

    if narration_path and os.path.exists(narration_path):
        cmd.extend(["-i", narration_path])

    # 滤镜
    cmd.extend(["-vf", filter_complex])

    # 视频
    cmd.extend([
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
    ])

    # 音频
    if narration_path and os.path.exists(narration_path):
        cmd.extend([
            "-filter_complex",
            f"[1:a]volume={bgm_volume}[bgm];[2:a]volume={narration_volume}[narr];[bgm][narr]amix=inputs=2:duration=longest[aout]",
            "-map", "0:v",
            "-map", "[aout]",
        ])
    else:
        cmd.extend([
            "-map", "0:v",
            "-map", "1:a",
            "-af", f"volume={bgm_volume}",
        ])

    cmd.extend([
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        "-shortest",
        output_path
    ])

    try:
        subprocess.run(cmd, capture_output=True, timeout=120, check=True)
        print(f"  ✓ 渲染完成: {output_path}")
        return True
    except Exception as e:
        print(f"[Error] 渲染失败: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="视频渲染模块")
    parser.add_argument("--config", required=True, help="渲染配置 JSON")
    parser.add_argument("--output", required=True, help="输出视频路径")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    success = render_video(
        clips=config.get("clips", []),
        transitions=config.get("transitions", []),
        subtitles=config.get("subtitles", []),
        bgm_path=config.get("bgm_path", ""),
        output_path=args.output,
        title_text=config.get("title_text"),
        narration_path=config.get("narration_path"),
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()