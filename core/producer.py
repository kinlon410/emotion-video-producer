#!/usr/bin/env python3
"""
主演编器模块 — 协调所有核心模块完成视频生产

完整流程:
1. 音乐情感分析 → music_analyzer
2. AI叙事生成 → narrative_generator
3. 视觉素材选择 → visual_selector
4. 转场效果映射 → transition_mapper
5. 字幕同步 → subtitle_sync
6. TTS生成 → tts
7. 视觉素材下载 → visual
8. 视频渲染 → FFmpeg

用法:
    python3 -m core.producer --theme "东京夜行" --bgm music.mp3 --output output.mp4
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional

import redis

from config import (
    DASHSCOPE_API_KEY,
    DEFAULT_VOICE,
    DEFAULT_TTS_SPEED,
    DEFAULT_TTS_PROVIDER,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_WIDTH,
    DEFAULT_HEIGHT,
    DEFAULT_FPS,
    FONT_PATH,
    BGM_VOLUME,
    BGM_VOLUME_WITH_NARRATION,
    NARRATION_VOLUME,
    DEFAULT_MAX_SEGMENT_DURATION,
    SHORT_VIDEO_MAX_SEGMENT,
    MIN_SEGMENT_DURATION,
)

from .music_analyzer import analyze_music
from .narrative_generator import generate_narrative
from .visual_selector import select_visuals
from .transition_mapper import map_transitions
from .subtitle_sync import sync_subtitles, sync_subtitles_to_narration, sync_subtitles_from_asr, _remove_punctuation
from .style_presets import get_style_preset, apply_preset_to_analysis
from .tts import text_to_speech, get_audio_duration
from .asr import transcribe
from .visual import download_visuals


# ── 进度推送 ──

def push_progress(session_id: str, step: int, percent: int, message: str, status: str = "running"):
    """推送进度到 Redis

    Args:
        session_id: Session ID
        step: 当前步骤 (1-8)
        percent: 进度百分比
        message: 进度消息
        status: 状态 (running/completed/error)
    """
    try:
        from celeryconfig import broker_url
        redis_client = redis.from_url(broker_url)

        progress_data = {
            "step": step,
            "percent": percent,
            "message": message,
            "status": status,
            "session_id": session_id,
            "timestamp": int(os.times()[4] * 1000) if hasattr(os, 'times') else 0,
        }

        channel = f"emotion_video:progress:{session_id}"
        redis_client.publish(channel, json.dumps(progress_data, ensure_ascii=False))

        print(f"  [Progress] Step {step}: {percent}% - {message}")
    except Exception as e:
        # 进度推送失败不影响主流程（Redis 可选）
        print(f"  [Progress] Step {step}: {percent}% - {message} (本地模式)")
        # 不打印错误，避免干扰


def produce_video(
    theme: str,
    bgm_path: str,
    output_path: str,
    style: Optional[str] = None,
    voice: str = DEFAULT_VOICE,
    tts_speed: float = DEFAULT_TTS_SPEED,
    tts_provider: str = DEFAULT_TTS_PROVIDER,
    tts_instruction: str = "",  # MOSS-TTS 语音指令
    visual_mode: str = "auto",
    unified_style: Optional[str] = None,
    subtitle_style: Optional[str] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    session_id: Optional[str] = None,  # 用于进度推送
    keep_temp: bool = False,
    # 30s 短视频参数
    mode: str = "normal",  # normal/short
    duration_limit: Optional[int] = None,  # 时长限制 (秒)
    transition_intensity: str = "normal",  # normal/fast/cinematic
    segment_count: Optional[int] = None,  # 片段数量
    max_segment_duration: Optional[float] = None,  # 每片段最大时长 (秒)
    # 用户确认的文案（优先使用）
    title_text: Optional[str] = None,
    narration_script: Optional[str] = None,
) -> Optional[str]:
    """情感驱动视频生产

    Args:
        theme: 视频主题
        bgm_path: BGM 音频文件路径
        output_path: 输出视频文件路径
        style: 风格预设（可选）
        voice: TTS 语音选择
        tts_speed: TTS 语速
        tts_provider: TTS 提供者 (edge/dashscope/moss/cosyvoice)
        tts_instruction: MOSS-TTS 语音指令（自然语言描述语音风格）
        visual_mode: 素材获取模式
        unified_style: 统一视觉风格 (city/nature/night/cinematic/travel)
                       None 表示动态模式（根据能量变化）
        subtitle_style: 字幕样式名称 (impact/minimal/neon/cinematic/typewriter/bounce/card)
                       None 表示自动根据能量选择
        width: 视频宽度（默认 1920）
        height: 视频高度（默认 1080 或根据 ratio 计算）
        session_id: Session ID（用于 WebSocket 进度推送）
        keep_temp: 保留临时文件
        mode: 生产模式 (normal=标准/short=短视频)
        duration_limit: 时长限制 (秒)，用于短视频模式
        transition_intensity: 转场强度 (normal/fast/cinematic)
        segment_count: 片段数量，短视频模式自动计算约 15-20 段
        max_segment_duration: 每片段最大时长 (秒)，短视频默认 1.5s，标准模式默认 2s
        title_text: 用户确认的标题文案（优先使用）
        narration_script: 用户确认的旁白文案（优先使用）

    Returns:
        str: 输出视频路径，失败返回 None
    """
    # 确定目标尺寸
    target_width = width or DEFAULT_WIDTH
    target_height = height or DEFAULT_HEIGHT

    # 短视频模式参数处理
    effective_max_segment_duration = max_segment_duration  # 用户传入的值

    if mode == "short":
        # 短视频模式：默认 30s，每片段最多 1.5-2s，更多片段更激烈
        if duration_limit is None:
            duration_limit = 30
        if effective_max_segment_duration is None:
            effective_max_segment_duration = SHORT_VIDEO_MAX_SEGMENT  # 短视频每片段最多 1.5 秒
        if segment_count is None:
            segment_count = None  # 让 visual_selector 根据时长自动计算（约 20 片段）
        if transition_intensity == "normal":
            transition_intensity = "fast"  # 短视频默认快切
        print(f"  短视频模式: 时长限制={duration_limit}s, 每片段≤{effective_max_segment_duration}s, 转场={transition_intensity}")
    else:
        # 标准模式：每片段最多 2s，更多片段更流畅
        if effective_max_segment_duration is None:
            effective_max_segment_duration = DEFAULT_MAX_SEGMENT_DURATION
        if segment_count is None:
            segment_count = None  # 自动计算

    print(f"\n{'='*60}")
    print(f"  Emotion Video Producer")
    print(f"  主题: {theme}")
    print(f"  BGM: {bgm_path}")
    print(f"  尺寸: {target_width}x{target_height}")
    print(f"  模式: {mode}")
    print(f"{'='*60}\n")

    # 创建工作目录
    work_dir = Path(tempfile.mkdtemp(prefix="emotion_video_"))

    try:
        # ── Step 1: 音乐情感分析 (10%) ──
        if session_id:
            push_progress(session_id, 1, 10, "开始音乐情感分析...")
        print(f"\n[Step 1] 音乐情感分析...")
        analysis_path = str(work_dir / "analysis.json")
        analysis = analyze_music(bgm_path, analysis_path)

        if analysis is None:
            if session_id:
                push_progress(session_id, 1, 10, "音乐分析失败", "error")
            print("[Error] 音乐分析失败", file=sys.stderr)
            return None

        if session_id:
            push_progress(session_id, 1, 15, "音乐情感分析完成")

        # 应用风格预设
        if style:
            print(f"  应用风格预设: {style}")
            analysis = apply_preset_to_analysis(analysis, style)

        # ── Step 2: AI 叙事生成 (20%) ──
        if session_id:
            push_progress(session_id, 2, 20, "开始 AI 叙事生成...")
        print(f"\n[Step 2] AI 叙事生成...")

        # 检查是否有用户确认的文案
        if title_text or narration_script:
            print(f"  使用用户确认的文案")
            narrative = {
                "title_text": title_text or theme,
                "narration_script": narration_script or "",
                "segments": []
            }
            narrative_path = str(work_dir / "narrative.json")
            with open(narrative_path, "w", encoding="utf-8") as f:
                json.dump(narrative, f, ensure_ascii=False, indent=2)
        else:
            # 没有确认文案，自动生成
            narrative_path = str(work_dir / "narrative.json")
            narrative = generate_narrative(theme, analysis, style, narrative_path)

            if narrative is None:
                if session_id:
                    push_progress(session_id, 2, 20, "叙事生成失败", "error")
                print("[Error] 叙事生成失败", file=sys.stderr)
                return None

        title_text_final = narrative.get("title_text", theme)
        title_text_final = _remove_punctuation(title_text_final)  # 去除标点符号
        narration_script_final = narrative.get("narration_script", "")

        print(f"  标题: {title_text_final}")
        print(f"  文案: {narration_script_final[:50]}...")

        if session_id:
            push_progress(session_id, 2, 25, "AI 叙事生成完成")

        # ── Step 3: 视觉素材选择 (30%) ──
        if session_id:
            push_progress(session_id, 3, 30, "开始视觉素材选择...")
        print(f"\n[Step 3] 视觉素材选择...")
        visuals_path = str(work_dir / "visuals.json")
        visuals = select_visuals(analysis, segment_count=segment_count, output_json=visuals_path,
                                 unified_style=unified_style, max_segment_duration=effective_max_segment_duration)

        if session_id:
            push_progress(session_id, 3, 35, f"视觉素材选择完成 ({len(visuals)}个片段)")

        # ── Step 4: 转场映射 (40%) ──
        if session_id:
            push_progress(session_id, 4, 40, "开始转场效果映射...")
        print(f"\n[Step 4] 转场效果映射...")
        transitions_path = str(work_dir / "transitions.json")
        transitions = map_transitions(analysis, visuals, transitions_path,
                                      transition_intensity=transition_intensity)

        if session_id:
            push_progress(session_id, 4, 45, "转场效果映射完成")

        # ── Step 5: 字幕同步 (50%) ──
        if session_id:
            push_progress(session_id, 5, 50, "开始字幕同步...")
        print(f"\n[Step 5] 字幕同步...")
        subtitles_path = str(work_dir / "subtitles.json")
        subtitles = sync_subtitles(analysis, narrative, subtitles_path)

        if session_id:
            push_progress(session_id, 5, 55, "字幕同步完成")

        # ── Step 6: TTS 生成 (60%) ──
        if session_id:
            push_progress(session_id, 6, 60, "开始 TTS 语音合成...")
        print(f"\n[Step 6] TTS 生成旁白...")
        narration_audio = str(work_dir / "narration.wav")

        if narration_script_final:
            tts_result = text_to_speech(narration_script_final, narration_audio, voice, tts_speed, tts_provider, tts_instruction)
            if tts_result:
                narration_duration = get_audio_duration(narration_audio)
                print(f"  旁白时长: {narration_duration}s")

                if session_id:
                    push_progress(session_id, 6, 65, "TTS 语音合成完成")

                # ── ASR 语音识别 (65%) ──
                if session_id:
                    push_progress(session_id, 6, 66, "开始 ASR 语音识别...")
                print(f"\n[Step 6.5] ASR 语音识别...")
                asr_result_path = str(work_dir / "asr_result.json")
                asr_result = transcribe(narration_audio, language="zh", output_json=asr_result_path)

                if asr_result and asr_result.get("segments"):
                    print(f"  ASR 分段: {len(asr_result['segments'])} 段")
                    # 使用 ASR 结果生成字幕（每条 ≤ 8 字）
                    subtitles = sync_subtitles_from_asr(
                        asr_result,
                        analysis.get("structure", []),
                        max_chars=8,
                        subtitle_style=subtitle_style,  # 添加字幕样式参数
                        output_json=subtitles_path
                    )
                    print(f"  字幕生成: {len(subtitles)} 条")

                    if session_id:
                        push_progress(session_id, 6, 68, "ASR 语音识别完成")
                else:
                    # ASR 失败时回退到时长均分
                    print(f"  [Warning] ASR 失败，回退到时长均分")
                    subtitles = sync_subtitles_to_narration(
                        narrative, narration_duration,
                        analysis.get("structure", []),
                        subtitles_path
                    )

                    if session_id:
                        push_progress(session_id, 6, 68, "字幕分段完成")
            else:
                narration_audio = None
                if session_id:
                    push_progress(session_id, 6, 65, "TTS 语音合成跳过")
        else:
            narration_audio = None
            if session_id:
                push_progress(session_id, 6, 65, "无旁白文案，跳过 TTS")

        # ── Step 7: 视觉素材下载 (70%) ──
        if session_id:
            push_progress(session_id, 7, 70, f"并发下载视觉素材 ({segment_count}个片段)...")
        print(f"\n[Step 7] 视觉素材下载（并发模式）...")
        clips_dir = str(work_dir / "clips")

        visual_queries = []
        for v in visuals:
            visual_queries.append({
                "id": v["id"],
                "keyword": v["keyword"],
                "duration": v["duration"],
            })

        clips = download_visuals(visual_queries, clips_dir, visual_mode,
                                 width=target_width, height=target_height)

        if len(clips) < len(visuals):
            print(f"[Warning] {len(visuals) - len(clips)} 个素材获取失败，将使用备选方案", file=sys.stderr)

        if session_id:
            push_progress(session_id, 7, 80, f"素材下载完成 ({len(clips)}/{len(visuals)})")

        # ── Step 8: 视频渲染 (85%) ──
        if session_id:
            push_progress(session_id, 8, 85, "开始视频渲染...")
        print(f"\n[Step 8] 视频渲染...")

        # 构建渲染配置
        render_config = {
            "title_text": title_text_final,
            "bgm_path": bgm_path,
            "narration_path": narration_audio,
            "clips": clips,
            "transitions": transitions,
            "subtitles": subtitles,
            "output_path": output_path,
            "width": target_width,
            "height": target_height,
            "fps": DEFAULT_FPS,
        }

        # 保存渲染配置
        render_config_path = str(work_dir / "render_config.json")
        with open(render_config_path, "w", encoding="utf-8") as f:
            json.dump(render_config, f, ensure_ascii=False, indent=2)

        # 执行渲染
        result = _render_video(render_config)

        if result:
            if session_id:
                push_progress(session_id, 8, 95, "视频渲染完成")
                push_progress(session_id, 8, 100, "生产完成!", "completed")

            print(f"\n{'='*60}")
            print(f"  完成!")
            print(f"  输出: {output_path}")
            print(f"  风格: {style or analysis.get('recommended_style', 'auto')}")
            print(f"  时长: {analysis.get('duration', 0)}s")
            print(f"{'='*60}\n")
            return output_path
        else:
            if session_id:
                push_progress(session_id, 8, 85, "视频渲染失败", "error")
            print("[Error] 视频渲染失败", file=sys.stderr)
            return None

    finally:
        if not keep_temp and work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)


def _render_video(config: Dict) -> bool:
    """执行视频渲染

    使用 FFmpeg 将多个片段拼接，统一编码参数避免停顿
    """

    clips = config.get("clips", {})
    transitions = config.get("transitions", [])
    subtitles = config.get("subtitles", [])
    bgm_path = config.get("bgm_path", "")
    narration_path = config.get("narration_path")
    title_text = config.get("title_text", "")
    output_path = config.get("output_path", "output.mp4")
    width = config.get("width", DEFAULT_WIDTH)
    height = config.get("height", DEFAULT_HEIGHT)

    if not clips:
        print("[Error] 无素材片段", file=sys.stderr)
        return False

    # 获取所有片段路径
    clip_paths = []
    for trans in transitions:
        seg_idx = trans["segment_index"]
        if seg_idx < len(transitions):
            seg_id = f"S{seg_idx + 1}"
            if seg_id in clips:
                clip_paths.append(clips[seg_id])

    if not clip_paths:
        print("[Error] 无有效片段", file=sys.stderr)
        return False

    print(f"  渲染 {len(clip_paths)} 个片段...")

    # ── 方案：先统一编码所有片段，再拼接 ──
    # 这可以避免因编码参数不同导致的停顿

    # 创建临时目录存放统一编码的片段
    temp_dir = tempfile.mkdtemp()
    normalized_clips = []

    # 统一编码参数：相同分辨率、帧率、编码
    for i, clip_path in enumerate(clip_paths):
        norm_path = os.path.join(temp_dir, f"norm_{i}.mp4")

        # 统一编码：25fps, 相同分辨率, 快速编码
        norm_cmd = [
            "ffmpeg", "-y", "-i", clip_path,
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps=25",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-an",  # 移除原音频，使用统一 BGM
            norm_path
        ]

        try:
            subprocess.run(norm_cmd, capture_output=True, timeout=60, check=True)
            normalized_clips.append(norm_path)
        except Exception as e:
            print(f"  [Warning] 片段 {i} 编码失败，使用原始文件")
            normalized_clips.append(clip_path)

    # 创建 concat 文件
    concat_file = tempfile.mktemp(suffix=".txt")
    with open(concat_file, "w") as f:
        for path in normalized_clips:
            f.write(f"file '{path}'\n")

    # 构建字幕滤镜
    subtitle_filter = ""
    srt_path = None  # 初始化
    if subtitles:
        srt_path = tempfile.mktemp(suffix=".srt")
        _save_srt(subtitles, srt_path)
        subtitle_filter = f",subtitles='{srt_path}'"

    # 构建标题滤镜
    title_filter = ""
    if title_text:
        title_filter = f",drawtext=text='{title_text}':fontfile='{FONT_PATH}':fontsize=64:fontcolor=white:borderw=3:bordercolor=black@0.7:x=(w-text_w)/2:y=100:enable='between(t,0,3)'"

    # 渲染命令
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_file,
        "-i", bgm_path,
    ]

    # 添加旁白
    has_narration = narration_path and os.path.exists(narration_path)
    if has_narration:
        cmd.extend(["-i", narration_path])

    # 视频滤镜：统一帧率 + 字幕 + 标题
    video_filter = f"fps=25,format=yuv420p{subtitle_filter}{title_filter}"

    cmd.extend(["-vf", video_filter])

    # 视频编码
    cmd.extend(["-c:v", "libx264", "-preset", "medium", "-crf", "23"])

    # 音频处理 - 智能音量调整
    if has_narration:
        # 有旁白时：BGM 作为背景音，旁白为主
        audio_filter = (
            f"[1:a]volume={BGM_VOLUME_WITH_NARRATION}[bgm];"
            f"[2:a]volume={NARRATION_VOLUME}[narr];"
            f"[bgm][narr]amix=inputs=2:duration=longest:dropout_transition=0.5:normalize=0[aout]"
        )
        cmd.extend([
            "-filter_complex", audio_filter,
            "-map", "0:v",
            "-map", "[aout]",
        ])
    else:
        # 无旁白：BGM 音量适中
        cmd.extend([
            "-map", "0:v",
            "-map", "1:a",
            "-af", f"volume={BGM_VOLUME}",
        ])

    cmd.extend([
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest",
        output_path
    ])

    # 初始化清理变量
    srt_path = None

    try:
        # Debug: 打印命令
        print(f"  FFmpeg 命令: {' '.join(cmd[:10])}...")
        result = subprocess.run(cmd, capture_output=True, timeout=300, check=True)

        # 清理临时文件
        if os.path.exists(concat_file):
            os.remove(concat_file)
        if srt_path and os.path.exists(srt_path):
            os.remove(srt_path)
        # 清理统一编码的临时目录
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

        print(f"  ✓ 渲染完成")
        return True

    except subprocess.TimeoutExpired:
        print("[Error] 渲染超时", file=sys.stderr)
        return False
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8', errors='replace')
        print(f"[Error] 渲染失败:", file=sys.stderr)
        for line in error_msg.split('\n')[-20:]:
            if line.strip():
                print(f"  {line}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[Error] 渲染异常: {e}", file=sys.stderr)
        return False


def _save_srt(subtitles: List[Dict], output_path: str):
    """保存 SRT 格式字幕"""

    lines = []
    for i, sub in enumerate(subtitles):
        # id 可能是字符串 "L1" 或整数 1
        sub_id = sub.get("id", i + 1)
        if isinstance(sub_id, str):
            idx = sub_id.replace("L", "")
        else:
            idx = str(sub_id)

        start = _format_srt_time(sub["start"])
        end = _format_srt_time(sub["end"])

        text = sub.get("text_zh", "")

        lines.append(idx)
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _format_srt_time(seconds: float) -> str:
    """格式化 SRT 时间"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main():
    parser = argparse.ArgumentParser(description="情感驱动视频生产")
    parser.add_argument("--theme", required=True, help="视频主题")
    parser.add_argument("--bgm", required=True, help="BGM 音频文件路径")
    parser.add_argument("--output", default=None, help="输出视频路径")
    parser.add_argument("--style", default=None, help="风格预设")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help="TTS 语音")
    parser.add_argument("--tts-speed", type=float, default=DEFAULT_TTS_SPEED, help="TTS 语速")
    parser.add_argument("--tts-provider", default=DEFAULT_TTS_PROVIDER,
                        choices=["edge", "dashscope", "moss", "cosyvoice"], help="TTS 提供者")
    parser.add_argument("--tts-instruction", default="", help="MOSS-TTS 语音指令")
    parser.add_argument("--visual-mode", default="auto", help="素材获取模式")
    parser.add_argument("--keep-temp", action="store_true", help="保留临时文件")
    args = parser.parse_args()

    output_path = args.output or f"{DEFAULT_OUTPUT_DIR}/{args.theme.replace(' ', '_')}.mp4"

    result = produce_video(
        theme=args.theme,
        bgm_path=args.bgm,
        output_path=output_path,
        style=args.style,
        voice=args.voice,
        tts_speed=args.tts_speed,
        tts_provider=args.tts_provider,
        tts_instruction=args.tts_instruction,
        visual_mode=args.visual_mode,
        keep_temp=args.keep_temp,
    )

    if result:
        print(f"成功: {result}")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()