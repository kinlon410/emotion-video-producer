#!/usr/bin/env python3
"""
转场映射器模块 — 根据情感张力智能选择转场效果和时长

张力 → 转场映射：
- 高张力 (≥0.8) → pixelize, zoomin, spinzoom (0.12s)
- 中张力 (0.5-0.8) → wipeleft, circleopen, zoomin (0.20s)
- 低张力 (<0.5) → fade, dissolve, smoothup (0.35s)

智能选择策略：
- 根据情感类型（情绪标签）匹配转场风格
- 避免相邻片段使用相同转场
- 张力峰值自动切换高能量转场
- 首尾片段特殊处理

用法:
    python3 -m core.transition_mapper --analysis analysis.json --output transitions.json
"""

import argparse
import json
import random
from typing import Dict, List, Optional, Set

from config import TRANSITION_DURATIONS


# ── 能量级别映射 ──

ENERGY_TO_TRANSITION_KEY = {
    "high": "high_energy",
    "medium": "medium_energy",
    "low": "low_energy",
}


# ── 情感类型 → 转场风格映射 ──

EMOTION_TO_STYLE = {
    # 高能量/激烈情绪 → 快速冲击转场
    "energetic": "impact",
    "excited": "impact",
    "epic": "impact",
    "dramatic": "impact",
    "intense": "impact",
    "powerful": "impact",

    # 正向情绪 → 展开/揭示转场
    "happy": "reveal",
    "joyful": "reveal",
    "uplifting": "reveal",
    "hopeful": "reveal",
    "inspiring": "reveal",

    # 柔和情绪 → 渐变转场
    "calm": "smooth",
    "peaceful": "smooth",
    "relaxing": "smooth",
    "serene": "smooth",
    "gentle": "smooth",

    # 深沉情绪 → 暗色转场
    "sad": "dark",
    "melancholy": "dark",
    "nostalgic": "dark",
    "emotional": "dark",

    # 神秘情绪 → 特效转场
    "mysterious": "effect",
    "dreamy": "effect",
    "ethereal": "effect",

    # 城市夜景 → 动感转场
    "urban": "dynamic",
    "night": "dynamic",
    "city": "dynamic",
}


# ── FFmpeg xfade 转场效果（扩展版）──

XFADE_TRANSITIONS = {
    # 高能量 - 快速冲击转场
    "high_energy": [
        "pixelize",    # 像素化（冲击感）
        "zoomin",      # 快速放大
        "spinzoom",    # 旋转缩放
        "circleopen",  # 圆形展开
        "wipeleft",    # 左滑
        "coverleft",   # 左覆盖
        "distance",    # 距离过渡
        "diag1",       # 对角线
        "diag2",       # 反对角线
        "hblur",       # 横向模糊快速
        "slideup",     # 上滑快速
        "slidedown",   # 下滑快速
        "rectcrop",    # 方形裁切快速
    ],

    # 中能量 - 平滑过渡
    "medium_energy": [
        "circleopen",  # 圆形展开
        "wipeleft",    # 左滑
        "wipeup",      # 上滑
        "zoomin",      # 放大
        "revealleft",  # 左揭示
        "slidedown",   # 下滑
        "coverright",  # 右覆盖
        "rectcrop",    # 方形裁切
        "distance",    # 距离过渡
        "diag1",       # 对角线
        "squeezeV",    # 垂直挤压
        "squeezeH",    # 水平挤压
    ],

    # 低能量 - 柔和渐变
    "low_energy": [
        "fade",        # 渐隐
        "dissolve",    # 溶解
        "smoothup",    # 平滑上
        "smoothdown",  # 平滑下
        "fadeblack",   # 黑场渐隐
        "radial",      # 径向
        "hblur",       # 横向模糊
        "vblur",       # 垂直模糊
        "wipeup",      # 柔和上滑
        "circleclose", # 圆形闭合
        "dissolve",    # 溶解
    ],

    # 冲击风格（高能量情绪）
    "impact": [
        "pixelize",
        "spinzoom",
        "zoomin",
        "distance",
        "diag1",
        "diag2",
        "rectcrop",
    ],

    # 展开风格（正向情绪）
    "reveal": [
        "circleopen",
        "revealleft",
        "revealright",
        "wipeleft",
        "wipeup",
        "zoomin",
    ],

    # 柔和风格（柔和情绪）
    "smooth": [
        "fade",
        "dissolve",
        "smoothup",
        "smoothdown",
        "radial",
        "hblur",
        "vblur",
    ],

    # 暗色风格（深沉情绪）
    "dark": [
        "fadeblack",
        "fade",
        "dissolve",
        "vblur",
        "circleclose",
    ],

    # 特效风格（神秘情绪）
    "effect": [
        "pixelize",
        "spinzoom",
        "radial",
        "distance",
        "squeezeV",
        "squeezeH",
    ],

    # 动感风格（城市夜景）
    "dynamic": [
        "wipeleft",
        "wipeup",
        "slideup",
        "slidedown",
        "coverleft",
        "coverright",
        "diag1",
        "hblur",
    ],
}


def map_transitions(analysis: Dict, segments: Optional[List[Dict]] = None,
                    output_json: str = None,
                    transition_intensity: str = "normal") -> List[Dict]:
    """根据情感分析智能映射转场效果

    Args:
        analysis: 音乐情感分析结果
        segments: 视觉片段列表（可选，用于对齐时间）
        output_json: 输出 JSON 文件路径（可选）
        transition_intensity: 转场强度 (normal/fast/cinematic)
            - normal: 标准转场时长
            - fast: 快切模式，高能量 0.08-0.15s
            - cinematic: 电影感，更长更平滑的转场

    Returns:
        list: 转场配置列表
    """
    print(f"[transition_mapper] 智能映射转场效果")

    structure = analysis.get("structure", [])
    tension_peaks = analysis.get("tension_peaks", [])
    emotion_curve = analysis.get("emotion_curve", [])
    recommended_style = analysis.get("recommended_style", "")

    # 如果有 segments，使用其时间
    if segments:
        seg_times = [(s["start"], s["end"], s.get("energy", "medium"), s.get("emotion", "")) for s in segments]
    else:
        # 使用 structure，并尝试获取情感标签
        seg_times = []
        for s in structure:
            emotion = s.get("emotion", s.get("label", ""))
            seg_times.append((s["start"], s["end"], s["energy"], emotion))

    # 确保至少有片段
    if not seg_times:
        duration = analysis.get("duration", 20)
        seg_times = [(0, duration, "medium", "")]

    transitions = []
    used_transitions: Set[str] = set()  # 避免相邻重复

    for i, (start, end, energy, emotion) in enumerate(seg_times):
        # 智能选择转场
        trans_name = _smart_select_transition(
            i, energy, emotion, tension_peaks, start,
            used_transitions, recommended_style
        )

        # 更新已用转场集合（只保留最近3个）
        used_transitions.add(trans_name)
        if len(used_transitions) > 3:
            used_transitions = set(list(used_transitions)[-3:])

        # 根据能量选择转场时长
        base_duration = TRANSITION_DURATIONS.get(energy, 0.20)

        # 根据转场强度调整时长
        if transition_intensity == "fast":
            # 快切模式：高能量更短，低能量保持平滑
            if energy == "high":
                trans_duration = 0.08 + random.uniform(0, 0.07)  # 0.08-0.15s
            elif energy == "medium":
                trans_duration = 0.15  # 中等快切
            else:
                trans_duration = 0.25  # 低能量保持平滑
        elif transition_intensity == "cinematic":
            # 电影感：所有转场更长更平滑
            trans_duration = base_duration * 1.5
        else:
            trans_duration = base_duration

        # 第一个片段入场，最后一个片段出场
        if i == 0:
            trans_in = "cut"
        else:
            trans_in = transitions[i - 1]["transition_out"]

        if i == len(seg_times) - 1:
            trans_out = "fade_out"
        else:
            trans_out = trans_name

        transitions.append({
            "segment_index": i,
            "start": start,
            "end": end,
            "energy": energy,
            "emotion": emotion,
            "transition_in": trans_in,
            "transition_out": trans_out,
            "transition_duration": trans_duration,
        })

    print(f"  映射 {len(transitions)} 个转场（智能选择）")

    # 保存 JSON
    if output_json:
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(transitions, f, ensure_ascii=False, indent=2)
        print(f"  输出已保存: {output_json}")

    return transitions


def _smart_select_transition(
    segment_index: int,
    energy: str,
    emotion: str,
    tension_peaks: List[float],
    start: float,
    used_transitions: Set[str],
    recommended_style: str
) -> str:
    """智能选择转场效果

    优先级：
    1. 张力峰值 → 高能量转场
    2. 情感类型 → 风格匹配转场
    3. 能量级别 → 对应能量转场
    4. 避免相邻重复
    """

    # 1. 张力峰值检测
    if tension_peaks:
        peak_near = any(abs(p - start) < 1.5 for p in tension_peaks)
        if peak_near:
            trans_list = XFADE_TRANSITIONS.get("impact", XFADE_TRANSITIONS["high_energy"])
            # 过滤已用转场
            available = [t for t in trans_list if t not in used_transitions]
            if available:
                return random.choice(available)
            return random.choice(trans_list)

    # 2. 情感类型匹配
    if emotion:
        style = EMOTION_TO_STYLE.get(emotion.lower(), None)
        if style:
            trans_list = XFADE_TRANSITIONS.get(style, None)
            if trans_list:
                available = [t for t in trans_list if t not in used_transitions]
                if available:
                    return random.choice(available)

    # 3. 推荐风格匹配
    if recommended_style:
        style = EMOTION_TO_STYLE.get(recommended_style.lower(), None)
        if style:
            trans_list = XFADE_TRANSITIONS.get(style, None)
            if trans_list:
                available = [t for t in trans_list if t not in used_transitions]
                if available:
                    return random.choice(available)

    # 4. 能量级别匹配
    trans_key = ENERGY_TO_TRANSITION_KEY.get(energy, "medium_energy")
    trans_list = XFADE_TRANSITIONS.get(trans_key, XFADE_TRANSITIONS["medium_energy"])

    # 过滤已用转场
    available = [t for t in trans_list if t not in used_transitions]
    if available:
        return random.choice(available)

    return random.choice(trans_list)


def main():
    parser = argparse.ArgumentParser(description="转场映射器模块")
    parser.add_argument("--analysis", required=True, help="音乐情感分析 JSON")
    parser.add_argument("--segments", default=None, help="视觉片段 JSON")
    parser.add_argument("--output", default=None, help="输出 JSON 文件路径")
    args = parser.parse_args()

    with open(args.analysis, "r", encoding="utf-8") as f:
        analysis = json.load(f)

    segments = None
    if args.segments:
        with open(args.segments, "r", encoding="utf-8") as f:
            segments = json.load(f)

    transitions = map_transitions(analysis, segments, args.output)

    if args.output is None:
        print(json.dumps(transitions, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()