#!/usr/bin/env python3
"""
ASR 模块 — 语音识别生成字幕

支持:
1. 百炼 ASR API（主要）
2. 本地 Whisper 模型（备选）

用法:
    python3 -m core.asr audio.wav --output subtitles.json
    python3 -m core.asr audio.wav --output subtitles.srt --format srt
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from config import DASHSCOPE_API_KEY


# ── FFmpeg 配置 ──

FFMPEG = shutil.which("ffmpeg") or "/usr/local/bin/ffmpeg"
FFPROBE = shutil.which("ffprobe") or "/usr/local/bin/ffprobe"


def transcribe(input_path: str, language: str = "zh",
               output_json: Optional[str] = None) -> Optional[Dict]:
    """语音转文字（ASR）

    Args:
        input_path: 输入文件路径（音频或视频）
        language: 语言代码 (zh/en)
        output_json: 输出 JSON 文件路径（可选）

    Returns:
        dict: {"text": "全文", "segments": [...], "duration": N}
    """
    print(f"[asr] 语音识别: {input_path}")

    input_path = Path(input_path)

    if not input_path.exists():
        print(f"[Error] 文件不存在: {input_path}", file=sys.stderr)
        return None

    # 检查文件类型
    ext = input_path.suffix.lower()
    is_video = ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]
    is_audio = ext in [".wav", ".mp3", ".aac", ".m4a", ".flac"]

    if not (is_video or is_audio):
        print(f"[Error] 不支持文件类型: {ext}", file=sys.stderr)
        return None

    # 视频文件提取音轨
    if is_video:
        audio_path = _extract_audio_from_video(str(input_path))
        if audio_path is None:
            return None
    else:
        audio_path = str(input_path)

    # 获取时长
    duration = _get_audio_duration(audio_path)

    # 尝试百炼 ASR
    if DASHSCOPE_API_KEY:
        result = _call_dashscope_asr(audio_path, language)
    else:
        # 尝试本地 Whisper
        result = _call_whisper_asr(audio_path, language)

    if result is None:
        return None

    result["duration"] = duration
    result["source"] = str(input_path)

    # 清理临时文件
    if is_video and audio_path.startswith(tempfile.gettempdir()):
        try:
            os.remove(audio_path)
        except Exception:
            pass

    # 保存 JSON
    if output_json:
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  JSON 保存至: {output_json}")

    return result


def _extract_audio_from_video(video_path: str) -> Optional[str]:
    """从视频提取音轨"""

    temp_audio = tempfile.mktemp(suffix=".wav")

    cmd = [
        FFMPEG, "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        temp_audio
    ]

    try:
        subprocess.run(cmd, capture_output=True, timeout=60, check=True)
        return temp_audio
    except Exception as e:
        print(f"[Error] 音轨提取失败: {e}", file=sys.stderr)
        return None


def _get_audio_duration(audio_path: str) -> float:
    """获取音频时长"""

    cmd = [
        FFPROBE, "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        audio_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception:
        pass

    return 0.0


def _call_dashscope_asr(audio_path: str, language: str) -> Optional[Dict]:
    """调用百炼 ASR API - 使用 Transcription（文件上传）方式"""

    try:
        import dashscope
        from dashscope.audio.asr import Transcription
        import time

        dashscope.api_key = DASHSCOPE_API_KEY

        # 方式1：使用 Transcription API（文件上传，更稳定）
        try:
            transcription = Transcription()

            # 使用 async_call 获取任务结果
            task_response = transcription.async_call(
                model='paraformer-v2',
                file_urls=[f'file://{audio_path}'],
                language=language,
            )

            # 检查任务状态
            if task_response.status_code == 200:
                # 获取任务 ID
                task_id = task_response.output.get('task_id') if hasattr(task_response, 'output') else None

                if task_id:
                    # 等待任务完成
                    result = transcription.wait(task_id)

                    if result and hasattr(result, 'output'):
                        output = result.output

                        # 解析结果
                        segments = []
                        full_text = ""

                        if isinstance(output, dict):
                            results_list = output.get('results', [])

                            for idx, res in enumerate(results_list, 1):
                                text = res.get('transcription_text', '')
                                if not text:
                                    continue

                                full_text += text
                                begin_time = res.get('begin_time', idx * 2000)
                                end_time = res.get('end_time', (idx + 1) * 2000)

                                segments.append({
                                    "id": f"L{idx}",
                                    "text": text,
                                    "start": round(begin_time / 1000.0, 2),
                                    "end": round(end_time / 1000.0, 2),
                                })

                        if segments:
                            print(f"  Transcription 完成: {len(segments)} 段")
                            return {
                                "text": full_text,
                                "segments": segments,
                                "language": language,
                            }

        except Exception as e:
            print(f"[Warning] Transcription API 失败: {e}, 尝试实时 ASR", file=sys.stderr)

        # 方式2：使用实时 Recognition API（流式）
        from dashscope.audio.asr import Recognition, RecognitionCallback

        class ASRCallback(RecognitionCallback):
            def __init__(self):
                self.sentences = []
                self.errors = []
                self.current_sentence = None

            def on_event(self, result):
                sentence = result.get_sentence()
                if sentence:
                    text = sentence.get("text", "")
                    # Check if this is a complete sentence (sentence_end=True)
                    if sentence.get("sentence_end"):
                        # Store the complete sentence with proper timestamps
                        begin_time = sentence.get("begin_time", 0)
                        end_time = sentence.get("end_time", 0)
                        # Handle None values
                        if begin_time is None:
                            begin_time = 0
                        if end_time is None:
                            end_time = begin_time + len(text) * 100  # Estimate

                        self.sentences.append({
                            "text": text,
                            "begin_time": begin_time,
                            "end_time": end_time,
                        })

            def on_error(self, error):
                self.errors.append(str(error))

        callback = ASRCallback()

        recognition = Recognition(
            model="paraformer-realtime-v2",
            format="pcm",
            sample_rate=16000,
            callback=callback
        )

        recognition.start()

        # 发送音频数据 (优化参数: 小chunk, 适当延迟)
        with open(audio_path, "rb") as f:
            # 跳过 WAV header
            f.read(44)
            chunk_size = 3200  # 更小的 chunk 让 ASR 处理更及时
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                recognition.send_audio_frame(chunk)
                time.sleep(0.1)  # 增加延迟让 ASR 有时间处理

        recognition.stop()

        if callback.errors:
            print(f"[Error] ASR API 错误: {callback.errors[0]}", file=sys.stderr)
            return None

        # 解析结果
        segments = []
        full_text = ""

        for idx, s in enumerate(callback.sentences, 1):
            text = s.get("text", "")
            full_text += text

            start_ms = s.get("begin_time", 0)
            end_ms = s.get("end_time", 0)

            segments.append({
                "id": f"L{idx}",
                "text": text,
                "start": round(start_ms / 1000.0, 2),
                "end": round(end_ms / 1000.0, 2),
            })

        print(f"  ASR 完成: {len(segments)} 段")

        return {
            "text": full_text,
            "segments": segments,
            "language": language,
        }

    except ImportError:
        print("[Warning] dashscope 未安装，尝试本地 Whisper", file=sys.stderr)
        return _call_whisper_asr(audio_path, language)

    except Exception as e:
        print(f"[Error] 百炼 ASR 失败: {e}", file=sys.stderr)
        return _call_whisper_asr(audio_path, language)


def _call_whisper_asr(audio_path: str, language: str) -> Optional[Dict]:
    """调用本地 Whisper 模型（备选）"""

    try:
        import whisper

        model = whisper.load_model("base")

        result = model.transcribe(audio_path, language=language)

        segments = []
        full_text = ""

        for idx, seg in enumerate(result.get("segments", []), 1):
            text = seg.get("text", "").strip()
            full_text += text

            segments.append({
                "id": f"L{idx}",
                "text": text,
                "start": round(seg.get("start", 0), 2),
                "end": round(seg.get("end", 0), 2),
            })

        print(f"  Whisper 完成: {len(segments)} 段")

        return {
            "text": full_text,
            "segments": segments,
            "language": language,
            "model": "whisper-base",
        }

    except ImportError:
        print("[Error] whisper 未安装，ASR 不可用", file=sys.stderr)
        return None

    except Exception as e:
        print(f"[Error] Whisper 失败: {e}", file=sys.stderr)
        return None


def save_srt(result: Dict, output_path: str) -> bool:
    """保存 SRT 格式字幕"""

    segments = result.get("segments", [])

    lines = []
    for seg in segments:
        idx = seg["id"].replace("L", "")
        start = _format_srt_time(seg["start"])
        end = _format_srt_time(seg["end"])

        lines.append(idx)
        lines.append(f"{start} --> {end}")
        lines.append(seg["text"])
        lines.append("")

    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return True
    except Exception as e:
        print(f"[Error] SRT 保存失败: {e}", file=sys.stderr)
        return False


def _format_srt_time(seconds: float) -> str:
    """格式化 SRT 时间"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main():
    parser = argparse.ArgumentParser(description="ASR 模块")
    parser.add_argument("input", help="输入文件（音频或视频）")
    parser.add_argument("--output", default="subtitles.json", help="输出文件路径")
    parser.add_argument("--format", default="json", choices=["json", "srt"], help="输出格式")
    parser.add_argument("--language", default="zh", help="语言代码")
    args = parser.parse_args()

    result = transcribe(args.input, args.language)

    if result is None:
        sys.exit(1)

    if args.format == "srt":
        save_srt(result, args.output)
    else:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"输出: {args.output}")


if __name__ == "__main__":
    main()