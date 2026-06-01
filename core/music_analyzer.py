#!/usr/bin/env python3
"""
音乐情感分析模块 — 使用 librosa 分析音频情感特征

输出结构:
{
    "duration": 20.5,
    "structure": [
        {"type": "intro", "start": 0, "end": 3, "energy": "low"},
        {"type": "verse", "start": 3, "end": 8, "energy": "medium"},
        {"type": "chorus", "start": 8, "end": 15, "energy": "high"},
        {"type": "verse2", "start": 15, "end": 18, "energy": "medium"},
        {"type": "outro", "start": 18, "end": 20.5, "energy": "low"}
    ],
    "emotion_curve": [
        {"time": 0, "value": 0.2},
        {"time": 8.5, "value": 0.95},
        {"time": 13, "value": 0.88},
        {"time": 20, "value": 0.1}
    ],
    "tension_peaks": [8.5, 13.2],
    "recommended_style": "热血"
}

用法:
    python3 -m core.music_analyzer --audio music.mp3 --output analysis.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING, Any

if TYPE_CHECKING:
    import numpy as np

try:
    import librosa
    import numpy as np
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    np = None  # type: ignore
    print("[Warning] librosa not installed, music analysis will use fallback", file=sys.stderr)

from config import ANALYSIS_SAMPLE_RATE, ANALYSIS_HOP_LENGTH, MIN_TENSION_THRESHOLD


# ── 情感风格映射 ──

ENERGY_TO_STYLE = {
    "high": "热血",
    "medium": "励志",
    "low": "治愈",
}

ENERGY_LEVELS = ["low", "medium", "high"]


def analyze_music(audio_path: str, output_json: Optional[str] = None) -> Dict:
    """分析音乐情感特征

    Args:
        audio_path: 音频文件路径
        output_json: 输出 JSON 文件路径（可选）

    Returns:
        dict: 情感分析结果
    """
    if not LIBROSA_AVAILABLE:
        return _fallback_analysis(audio_path)

    print(f"[music_analyzer] 分析音频: {audio_path}")

    try:
        # 加载音频
        y, sr = librosa.load(audio_path, sr=ANALYSIS_SAMPLE_RATE)
        duration = librosa.get_duration(y=y, sr=sr)

        print(f"  时长: {duration:.1f}s, 采样率: {sr}")

        # 1. 检测节拍
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        bpm = float(tempo) if hasattr(tempo, '__iter__') else tempo
        beat_times = librosa.frames_to_time(beats, sr=sr, hop_length=ANALYSIS_HOP_LENGTH)

        print(f"  BPM: {bpm:.0f}, 节拍数: {len(beat_times)}")

        # 2. 计算能量曲线 (RMS)
        rms = librosa.feature.rms(y=y, hop_length=ANALYSIS_HOP_LENGTH)[0]
        rms_times = librosa.frames_to_time(range(len(rms)), sr=sr, hop_length=ANALYSIS_HOP_LENGTH)

        # 归一化 RMS 到 [0, 1]
        rms_normalized = (rms - rms.min()) / (rms.max() - rms.min() + 1e-6)

        # 3. 检测结构边界 (使用 novelty 检测)
        structure = _detect_structure(y, sr, rms_normalized, rms_times, duration)

        # 4. 计算情感曲线 (平滑 RMS)
        emotion_curve = _smooth_emotion_curve(rms_times, rms_normalized)

        # 5. 检测张力峰值
        tension_peaks = _detect_tension_peaks(emotion_curve, MIN_TENSION_THRESHOLD)

        print(f"  结构段数: {len(structure)}, 张力峰值: {len(tension_peaks)}")

        # 6. 推荐风格
        recommended_style = _recommend_style(rms_normalized, bpm)

        # 构建结果
        result = {
            "duration": round(duration, 2),
            "bpm": round(bpm, 0),
            "beat_count": len(beat_times),
            "beat_times": [round(t, 2) for t in beat_times[:20]],  # 只保留前20个
            "structure": structure,
            "emotion_curve": emotion_curve,
            "tension_peaks": tension_peaks,
            "recommended_style": recommended_style,
            "energy_stats": {
                "mean": round(float(rms_normalized.mean()), 3),
                "max": round(float(rms_normalized.max()), 3),
                "std": round(float(rms_normalized.std()), 3),
            }
        }

        # 保存 JSON
        if output_json:
            Path(output_json).parent.mkdir(parents=True, exist_ok=True)
            with open(output_json, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"  输出已保存: {output_json}")

        return result

    except Exception as e:
        print(f"[Error] 音频分析失败: {e}", file=sys.stderr)
        return _fallback_analysis(audio_path, error=str(e))


def _detect_structure(y: Any, sr: int, rms: Any,
                      rms_times: Any, duration: float) -> List[Dict]:
    """检测音乐结构边界 (intro/verse/chorus/outro)"""

    # 使用简单的能量阈值分割
    # 将音频分成若干段，根据能量高低分类

    segment_count = max(4, min(10, int(duration / 3)))  # 每3秒一段
    segment_duration = duration / segment_count

    structure = []

    for i in range(segment_count):
        start = i * segment_duration
        end = min((i + 1) * segment_duration, duration)

        # 计算该段的平均能量
        seg_mask = (rms_times >= start) & (rms_times < end)
        if seg_mask.any():
            seg_energy = float(rms[seg_mask].mean())
        else:
            seg_energy = 0.3  # 默认中等

        # 分类能量级别
        if seg_energy > 0.7:
            energy_level = "high"
        elif seg_energy > 0.35:
            energy_level = "medium"
        else:
            energy_level = "low"

        # 根据位置命名结构类型
        if i == 0:
            struct_type = "intro"
        elif i == segment_count - 1:
            struct_type = "outro"
        elif energy_level == "high":
            struct_type = "chorus"
        else:
            struct_type = "verse"

        structure.append({
            "type": struct_type,
            "start": round(start, 2),
            "end": round(end, 2),
            "energy": energy_level,
            "avg_energy": round(seg_energy, 3),
        })

    return structure


def _smooth_emotion_curve(times: Any, values: Any) -> List[Dict]:
    """平滑情感曲线，输出关键时间点"""

    # 降采样到 ~50 个点
    target_points = 50
    step = max(1, len(times) // target_points)

    curve = []
    for i in range(0, len(times), step):
        curve.append({
            "time": round(float(times[i]), 2),
            "value": round(float(values[i]), 3),
        })

    # 确保包含最后一个点
    if curve[-1]["time"] < float(times[-1]):
        curve.append({
            "time": round(float(times[-1]), 2),
            "value": round(float(values[-1]), 3),
        })

    return curve


def _detect_tension_peaks(curve: List[Dict], threshold: float) -> List[float]:
    """检测张力峰值（情感曲线的局部最大值）"""

    peaks = []

    for i in range(1, len(curve) - 1):
        prev_val = curve[i - 1]["value"]
        curr_val = curve[i]["value"]
        next_val = curve[i + 1]["value"]

        # 局部最大值且超过阈值
        if curr_val > prev_val and curr_val > next_val and curr_val >= threshold:
            peaks.append(curve[i]["time"])

    return peaks


def _recommend_style(rms: Any, bpm: float) -> str:
    """推荐风格"""

    mean_energy = float(rms.mean())

    if mean_energy > 0.6 and bpm > 120:
        return "热血"
    elif mean_energy > 0.4:
        return "励志"
    else:
        return "治愈"


def _fallback_analysis(audio_path: str, error: str = "") -> Dict:
    """备用分析（当 librosa 不可用时）"""

    # 使用 ffprobe 获取时长
    import subprocess

    try:
        cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
               "-of", "csv=p=0", audio_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        duration = float(result.stdout.strip())
    except Exception:
        duration = 20.0  # 默认

    # 返回简单分析结果
    return {
        "duration": round(duration, 2),
        "bpm": 120,
        "beat_count": 0,
        "beat_times": [],
        "structure": [
            {"type": "intro", "start": 0, "end": round(duration * 0.2, 2), "energy": "low"},
            {"type": "verse", "start": round(duration * 0.2, 2), "end": round(duration * 0.5, 2), "energy": "medium"},
            {"type": "chorus", "start": round(duration * 0.5, 2), "end": round(duration * 0.8, 2), "energy": "high"},
            {"type": "outro", "start": round(duration * 0.8, 2), "end": round(duration, 2), "energy": "low"},
        ],
        "emotion_curve": [
            {"time": 0, "value": 0.2},
            {"time": round(duration * 0.5, 2), "value": 0.95},
            {"time": round(duration, 2), "value": 0.1},
        ],
        "tension_peaks": [round(duration * 0.5, 2)],
        "recommended_style": "励志",
        "error": error,
        "fallback": True,
    }


def main():
    parser = argparse.ArgumentParser(description="音乐情感分析模块")
    parser.add_argument("--audio", required=True, help="音频文件路径")
    parser.add_argument("--output", default=None, help="输出 JSON 文件路径")
    args = parser.parse_args()

    result = analyze_music(args.audio, args.output)

    if args.output is None:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()