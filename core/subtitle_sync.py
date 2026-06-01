#!/usr/bin/env python3
"""
字幕同步模块 — 将字幕对齐到语音 ASR 分段

抖音字幕特点：
- 无标点符号
- 语义断句（按词组，不硬切）
- 每条 4-8 字，适合短视频阅读

用法:
    python3 -m core.subtitle_sync --asr asr_result.json --output subtitles.json
"""

import argparse
import json
import re
import sys
from typing import Dict, List, Optional

from config import SUBTITLE_STYLES, FONT_PATH


# ── 抖音风格断句词库 ──
# 常见词组/短语，用于语义断句（优先保持这些词组完整）
WORD_GROUPS = [
    # 双字词组
    "慢慢", "静静", "轻轻", "温暖", "温柔", "阳光", "月光", "天空", "云朵",
    "城市", "街道", "风景", "自然", "呼吸", "心跳", "梦想", "希望", "力量",
    "此刻", "瞬间", "永远", "曾经", "未来", "过去", "现在", "开始", "结束",
    # 三字词组
    "闭上眼", "睁开眼", "不着急", "刚刚好", "值得被", "听风的", "落肩上",
    "轻声的", "问候的", "一切都", "每一步", "每一段", "每一天", "风的声音",
    # 四字词组
    "刚刚好的", "值得记住", "风的声音", "温柔的问候", "闭上眼睛",
    "阳光落在", "落在肩上", "肩上的光", "书写人生", "慢慢走着",
]

# 断句优先断开点（在此处断开更自然）
# 注意：这些是"断开后"的位置，即在这些字后面断开
BREAK_AFTER = ['的', '了', '着', '过', '吧', '啊', '呢', '吗', '好', '光']

# 抖音风格的完整短语（这些应该整体出现）
COMPLETE_PHRASES = [
    "闭上眼睛", "听风的声音", "慢慢走", "不着急",
    "阳光落在肩上", "温柔的问候", "此刻值得被记住",
    "一切都刚刚好", "每一步都在书写人生",
    "像一句轻声的问候",
]

# 动词（在这些前断开更自然）
VERBS = ['是', '有', '在', '来', '去', '走', '跑', '看', '听', '说', '想', '做', '像']

# 否定词（在这些前断开）
NEGATIVES = ['不', '没', '别']


def sync_subtitles_from_asr(asr_result: Dict,
                            structure: List[Dict] = None,
                            max_chars: int = 8,
                            subtitle_style: str = None,
                            output_json: str = None) -> List[Dict]:
    """根据 ASR 结果生成字幕

    Args:
        asr_result: ASR 语音识别结果 {"segments": [...]}
        structure: 音乐结构（用于分配样式）
        max_chars: 每条字幕最大字数（短视频推荐 6-8 字）
        subtitle_style: 字幕样式名称（可选，手动指定）
        output_json: 输出 JSON 文件路径（可选）

    Returns:
        list: 字幕时间轴列表
    """
    print(f"[subtitle_sync] 基于 ASR 结果生成字幕")

    segments = asr_result.get("segments", [])

    if not segments:
        print("[Warning] ASR 无分段数据", file=sys.stderr)
        return []

    # ── Step 1: 预处理 - 合并相邻短片段 ──
    merged_segments = _merge_short_segments(segments, max_chars)
    print(f"  ASR 原始分段: {len(segments)} → 合并后: {len(merged_segments)}")

    subtitles = []
    current_id = 1

    for seg in merged_segments:
        text = seg.get("text", "").strip()
        # 去除标点符号（短视频字幕更清晰）
        text = _remove_punctuation(text)
        start = seg.get("start", 0)
        end = seg.get("end", 0)

        if not text:
            continue

        # ── 关键改动：直接使用 ASR 提供的精确时间戳 ──
        # 字幕提前显示（补偿视觉感知延迟，-0.3s 更符合短视频）
        start_adjusted = max(0, start - 0.3)
        # 字幕结束时间延长（+0.15s 防止过早消失）
        end_adjusted = end + 0.15

        # ASR 分段已经是自然的语音断句
        # 如果单段太长，进一步拆分
        if len(text) <= max_chars:
            # 确定样式：优先使用手动指定的样式
            style = subtitle_style or "impact"
            if style is None and structure:
                energy = _get_energy_at_time(start, structure)
                style = _get_subtitle_style_name(energy)

            sub = {
                "id": current_id,
                "text_zh": text,
                "text_en": "",
                "start": round(start_adjusted, 2),
                "end": round(end_adjusted, 2),
                "style": style,
                "asr_start": round(start, 2),  # 保留原始 ASR 时间戳
                "asr_end": round(end, 2),
            }
            subtitles.append(sub)
            current_id += 1
        else:
            # 长句拆分：按时间比例分配（使用调整后的时间范围）
            parts = _smart_split(text, max_chars)
            part_duration = (end_adjusted - start_adjusted) / len(parts)

            for i, part in enumerate(parts):
                # 确定样式
                style = subtitle_style or "impact"
                if style is None and structure:
                    energy = _get_energy_at_time(start + i * part_duration, structure)
                    style = _get_subtitle_style_name(energy)

                sub = {
                    "id": current_id,
                    "text_zh": part,
                    "text_en": "",
                    "start": round(start_adjusted + i * part_duration, 2),
                    "end": round(start_adjusted + (i + 1) * part_duration, 2),
                    "style": style,
                    "asr_start": round(start, 2),
                    "asr_end": round(end, 2),
                }
                subtitles.append(sub)
                current_id += 1

    # ── Step 2: 后处理 - 优化相邻字幕时间衔接 ──
    subtitles = _optimize_subtitle_timing(subtitles)

    print(f"  生成 {len(subtitles)} 条字幕（每条 ≤ {max_chars} 字）")

    if output_json:
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(subtitles, f, ensure_ascii=False, indent=2)
        print(f"  输出已保存: {output_json}")

    return subtitles


def _optimize_subtitle_timing(subtitles: List[Dict]) -> List[Dict]:
    """优化相邻字幕时间衔接，避免重叠和过大间隔

    Args:
        subtitles: 字幕列表

    Returns:
        list: 优化后的字幕列表
    """
    if len(subtitles) < 2:
        return subtitles

    for i in range(1, len(subtitles)):
        prev = subtitles[i - 1]
        curr = subtitles[i]

        # 如果前一条字幕结束时间超过当前开始时间，调整
        if prev["end"] > curr["start"]:
            # 前一条字幕提前结束，保留 0.05s 间隔
            prev["end"] = round(curr["start"] - 0.05, 2)
            if prev["end"] < prev["start"]:
                prev["end"] = round(prev["start"] + 0.5, 2)

    return subtitles


def _merge_short_segments(segments: List[Dict], max_chars: int = 8,
                          max_gap: float = 0.3) -> List[Dict]:
    """合并相邻短片段，避免词组被切开

    Args:
        segments: ASR 原始分段列表
        max_chars: 合并后最大字数
        max_gap: 最大时间间隔（秒），超过则不合并

    Returns:
        list: 合并后的分段列表
    """
    if not segments:
        return []

    merged = []
    current = None

    for seg in segments:
        text = seg.get("text", "").strip()
        if not text:
            continue

        start = seg.get("start", 0)
        end = seg.get("end", 0)

        if current is None:
            current = {"text": text, "start": start, "end": end}
            continue

        # 检查是否应该合并
        current_text = current["text"]
        current_len = len(current_text)
        new_len = len(text)
        gap = start - current["end"]

        should_merge = (
            gap < max_gap and  # 时间间隔很短
            current_len + new_len <= max_chars and  # 合并后不超过限制
            current_len < 5 and  # 当前片段较短（可能被切开）
            new_len < 5          # 新片段也较短
        )

        if should_merge:
            # 合并片段
            current["text"] = current_text + text
            current["end"] = end
        else:
            # 保存当前片段，开始新片段
            merged.append(current)
            current = {"text": text, "start": start, "end": end}

    # 保存最后一个片段
    if current:
        merged.append(current)

    return merged


def _smart_split(text: str, max_chars: int = 8) -> List[str]:
    """智能拆分长句 - 抖音风格语义断句

    算法：
    1. 先尝试识别完整短语边界
    2. 在短语边界附近找语气词结尾
    3. 在动词/否定词前断开
    4. 保证每条 4-8 字，最后一条至少 4 字

    Args:
        text: 已去除标点的文本
        max_chars: 每条最大字数（默认 8）

    Returns:
        list: 断句结果列表
    """
    text_len = len(text)

    if text_len <= max_chars:
        return [text]

    if text_len < 8:
        return [text]  # 不足 8 字不分割

    result = []
    pos = 0

    while pos < text_len:
        remaining = text_len - pos

        # 剩余不足 max_chars，直接取完
        if remaining <= max_chars and remaining >= 4:
            result.append(text[pos:])
            break

        # 如果剩余在 4-7 字之间，需要决定是合并还是独立
        if remaining < max_chars and remaining >= 4:
            # 检查是否可以合并到上一条
            if result and len(result[-1]) + remaining <= max_chars + 2:
                result[-1] = result[-1] + text[pos:]
            else:
                result.append(text[pos:])
            break

        # 剩余超过 max_chars，需要找断点
        best_end = _find_best_break(text, pos, max_chars, text_len)

        segment = text[pos:best_end]
        if len(segment) >= 4:
            result.append(segment)
        else:
            # 太短，合并到上一条
            if result:
                result[-1] = result[-1] + segment
            else:
                result.append(segment)

        pos = best_end

    # 最终检查：确保没有单独 1-3 字的
    final = []
    for s in result:
        if len(s) >= 4:
            final.append(s)
        elif final:
            final[-1] = final[-1] + s
        else:
            final.append(s)

    return final


def _find_best_break(text: str, pos: int, max_chars: int, text_len: int) -> int:
    """找到最佳断句点

    Args:
        text: 文本
        pos: 当前位置
        max_chars: 每条最大字数
        text_len: 文本总长度

    Returns:
        int: 最佳断点位置
    """
    min_end = pos + 4
    max_end = min(pos + max_chars, text_len)

    # 确保最后一条至少 4 字
    if text_len - max_end < 4 and text_len - max_end > 0:
        max_end = text_len - 4

    if max_end < min_end:
        return text_len  # 无法分割，取全部

    # 优先级 1: 检查完整短语是否在范围内
    for phrase in COMPLETE_PHRASES:
        phrase_len = len(phrase)
        # 检查当前位置开始是否有这个短语
        if pos + phrase_len <= max_end + 2:  # 稍微放宽范围
            if text[pos:pos + phrase_len] == phrase:
                if phrase_len >= 4 and phrase_len <= max_chars:
                    return pos + phrase_len

    # 优先级 2: 在语气词后断开（从后往前找）
    for end in range(max_end, min_end - 1, -1):
        if end <= text_len:
            last_char = text[end - 1]
            if last_char in BREAK_AFTER:
                # 检查断开后剩余是否足够
                if text_len - end >= 4 or text_len - end == 0:
                    return end

    # 优先级 3: 在动词前断开
    for end in range(min_end, max_end):
        if end < text_len:
            next_char = text[end]
            if next_char in VERBS:
                # 在动词前断开
                if end >= pos + 4 and text_len - end >= 4:
                    return end

    # 优先级 4: 在否定词前断开
    for end in range(min_end, max_end):
        if end < text_len:
            next_char = text[end]
            if next_char in NEGATIVES:
                if end >= pos + 4 and text_len - end >= 4:
                    return end

    # 优先级 5: 在词组边界
    for word in WORD_GROUPS:
        word_len = len(word)
        if pos + word_len <= max_end:
            if text[pos:pos + word_len] == word:
                return pos + word_len

    # 最后：在 max_end 断开（但要确保剩余足够）
    if text_len - max_end < 4:
        return text_len - 4 if text_len - 4 >= pos + 4 else text_len

    return max_end


def _semantic_split(text: str, max_chars: int = 8) -> List[str]:
    """语义断句 - 调用 smart_split"""
    return _smart_split(text, max_chars)


def _find_all_break_points(text: str, max_chars: int = 8) -> List[int]:
    """找到所有可能的断句点 - 用于智能分割"""
    break_points = []
    text_len = len(text)

    # 找语气词结尾位置
    for i in range(4, min(text_len, max_chars + 2)):
        if i < text_len and text[i-1] in BREAK_AFTER:
            break_points.append(i)

    # 找词组边界
    for word in WORD_GROUPS:
        pos = text.find(word)
        while pos != -1:
            end_pos = pos + len(word)
            if 4 <= end_pos <= max_chars:
                break_points.append(end_pos)
            pos = text.find(word, pos + 1)

    return sorted(set(break_points))


def _uniform_split(text: str, max_chars: int = 8) -> List[str]:
    """均匀分割（无法语义断句时的备选）"""
    result = []
    text_len = len(text)

    for i in range(0, text_len, max_chars):
        segment = text[i:min(i + max_chars, text_len)]
        if segment and len(segment) >= 3:
            result.append(segment)

    return result


def sync_subtitles_to_narration(narrative: Dict, narration_duration: float,
                                structure: List[Dict] = None,
                                output_json: str = None) -> List[Dict]:
    """将字幕同步到 TTS 语音时长

    优先使用 AI 生成的 subtitle_segments（抖音风格断句）
    如果没有，则用算法后处理断句

    Args:
        narrative: 叙事脚本结果
        narration_duration: TTS 语音实际时长（秒）
        structure: 音乐结构（用于分配样式）
        output_json: 输出 JSON 文件路径（可选）

    Returns:
        list: 字幕时间轴列表
    """
    print(f"[subtitle_sync] 同步字幕到语音时长 ({narration_duration}s)")

    # 优先使用 AI 生成的字幕断句
    ai_subtitles = narrative.get("subtitle_segments", [])

    if ai_subtitles:
        print(f"  使用 AI 断句: {len(ai_subtitles)} 条")
        return _sync_ai_subtitles(ai_subtitles, narration_duration, structure, output_json)

    # AI 未生成断句，使用算法后处理
    narration_script = narrative.get("narration_script", "")

    if not narration_script:
        return []

    print(f"  AI 未断句，使用算法后处理")

    # 拆分为短句（短视频友好）
    sentences = _split_text(narration_script, max_chars=8)

    if not sentences:
        return []

    buffer_start = 0.5
    buffer_end = 0.5
    usable_duration = narration_duration - buffer_start - buffer_end

    per_sentence = usable_duration / len(sentences)

    subtitles = []
    current_id = 1

    for i, sent in enumerate(sentences):
        start = buffer_start + i * per_sentence
        end = buffer_start + (i + 1) * per_sentence

        if i == len(sentences) - 1:
            end = narration_duration - buffer_end

        sub = {
            "id": current_id,
            "text_zh": sent,
            "text_en": "",
            "start": round(start, 2),
            "end": round(end, 2),
            "style": "impact",
        }

        if structure:
            energy = _get_energy_at_time(start, structure)
            sub["style"] = _get_subtitle_style_name(energy)

        subtitles.append(sub)
        current_id += 1

    print(f"  生成 {len(subtitles)} 条字幕")

    if output_json:
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(subtitles, f, ensure_ascii=False, indent=2)
        print(f"  输出已保存: {output_json}")

    return subtitles


def _sync_ai_subtitles(ai_subtitles: List[Dict], narration_duration: float,
                       structure: List[Dict] = None,
                       output_json: str = None) -> List[Dict]:
    """同步 AI 生成的字幕断句到语音时长

    Args:
        ai_subtitles: AI 生成的字幕列表（每项包含 text_zh）
        narration_duration: 语音时长
        structure: 音乐结构
        output_json: 输出路径

    Returns:
        list: 调整时间后的字幕列表
    """
    buffer_start = 0.5
    buffer_end = 0.5
    usable_duration = narration_duration - buffer_start - buffer_end

    subtitles = []

    for i, ai_sub in enumerate(ai_subtitles):
        text_zh = ai_sub.get("text_zh", "")

        # 去除标点（确保无标点）
        text_zh = _remove_punctuation(text_zh)

        if not text_zh:
            continue

        # 计算时间
        per_item = usable_duration / len(ai_subtitles)
        start = buffer_start + i * per_item
        end = buffer_start + (i + 1) * per_item

        if i == len(ai_subtitles) - 1:
            end = narration_duration - buffer_end

        sub = {
            "id": i + 1,
            "text_zh": text_zh,
            "text_en": ai_sub.get("text_en", ""),
            "start": round(start, 2),
            "end": round(end, 2),
            "style": "impact",
        }

        if structure:
            energy = _get_energy_at_time(start, structure)
            sub["style"] = _get_subtitle_style_name(energy)

        subtitles.append(sub)

    print(f"  AI 断句已同步: {len(subtitles)} 条")

    if output_json:
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(subtitles, f, ensure_ascii=False, indent=2)
        print(f"  输出已保存: {output_json}")

    return subtitles


# ── 旧版函数（兼容）──

def sync_subtitles(analysis: Dict, narrative: Dict,
                   output_json: str = None) -> List[Dict]:
    """将字幕同步到音乐情感（旧版，无 TTS 时使用）"""

    print(f"[subtitle_sync] 同步字幕到情感曲线")

    tension_peaks = analysis.get("tension_peaks", [])
    structure = analysis.get("structure", [])
    duration = analysis.get("duration", 20)

    subtitle_segments = narrative.get("subtitle_segments", [])
    segment_narrations = narrative.get("segment_narrations", [])

    if subtitle_segments:
        subtitles = _align_to_peaks(subtitle_segments, tension_peaks, duration)
    elif segment_narrations:
        subtitles = _generate_from_segments(segment_narrations, tension_peaks, duration)
    else:
        narration_script = narrative.get("narration_script", "")
        subtitles = _generate_from_text(narration_script, tension_peaks, duration)

    for sub in subtitles:
        sub_time = sub["start"]
        energy = _get_energy_at_time(sub_time, structure)
        sub["style"] = _get_subtitle_style(energy)

    print(f"  生成 {len(subtitles)} 条字幕")

    if output_json:
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(subtitles, f, ensure_ascii=False, indent=2)
        print(f"  输出已保存: {output_json}")

    return subtitles


def _align_to_peaks(subtitles: List[Dict], peaks: List[float], duration: float) -> List[Dict]:
    """将现有字幕对齐到张力峰值"""

    for sub in subtitles:
        sub["text_zh"] = _remove_punctuation(sub.get("text_zh", ""))
        sub["text_en"] = _remove_punctuation(sub.get("text_en", ""))

    if peaks and subtitles:
        first_peak = peaks[0]
        subtitles[0]["start"] = max(0.5, first_peak - 1.0)
        subtitles[0]["end"] = subtitles[0]["start"] + 3.0

    if subtitles:
        last_sub = subtitles[-1]
        last_sub["end"] = min(last_sub["end"], duration - 0.5)

    return subtitles


def _generate_from_segments(segment_narrations: List[Dict], peaks: List[float],
                             duration: float) -> List[Dict]:
    """从段落叙事生成字幕"""

    subtitles = []
    current_id = 1

    for seg in segment_narrations:
        text = seg.get("text", "")
        start = seg.get("start", 0)
        end = seg.get("end", 0)

        if not text:
            continue

        sentences = _split_text(text, max_chars=8)

        seg_duration = end - start
        per_sentence = seg_duration / max(len(sentences), 1)

        for i, sent in enumerate(sentences):
            subtitles.append({
                "id": f"L{current_id}",
                "text_zh": sent,
                "text_en": "",
                "start": round(start + i * per_sentence, 2),
                "end": round(start + (i + 1) * per_sentence, 2),
                "style": "impact",
            })
            current_id += 1

    return subtitles


def _generate_from_text(text: str, peaks: List[float], duration: float) -> List[Dict]:
    """从完整文案生成字幕"""

    sentences = _split_text(text, max_chars=8)

    if not sentences:
        return []

    usable_duration = duration - 1.0
    per_sentence = usable_duration / len(sentences)

    subtitles = []

    start_offset = 0.5
    if peaks:
        start_offset = max(0.5, peaks[0] - 1.0)

    for i, sent in enumerate(sentences):
        subtitles.append({
            "id": f"L{i + 1}",
            "text_zh": sent,
            "text_en": "",
            "start": round(start_offset + i * per_sentence, 2),
            "end": round(start_offset + (i + 1) * per_sentence, 2),
            "style": "impact",
        })

    return subtitles


def _split_text(text: str, max_chars: int = 8) -> List[str]:
    """将文本拆分为短句 - 抖音风格

    特点：
    - 无标点符号
    - 语义断句优先
    - 每条 4-8 字
    """
    # 去除标点符号
    text = _remove_punctuation(text)

    if not text:
        return []

    # 如果文本较短，直接返回
    if len(text) <= max_chars:
        return [text]

    # 先尝试按自然分隔符拆分（如果有）
    # 注意：已去除标点，所以这里主要处理原始换行等
    parts = re.split(r'\n+', text)
    parts = [p.strip() for p in parts if p.strip()]

    if len(parts) > 1:
        # 有自然分段，处理每段
        result = []
        for part in parts:
            if len(part) <= max_chars:
                result.append(part)
            else:
                # 长段用智能断句
                result.extend(_smart_split(part, max_chars))
        return result

    # 无自然分段，使用智能断句
    return _smart_split(text, max_chars)


def _remove_punctuation(text: str) -> str:
    """去掉标点符号"""
    return re.sub(r'[，。！？；：、,\.!?\;:\'"【】《》（）\(\)\[\]{}「」『』]', '', text)


def _get_energy_at_time(time: float, structure: List[Dict]) -> str:
    """获取指定时间点的能量级别"""

    for seg in structure:
        if seg["start"] <= time < seg["end"]:
            return seg.get("energy", "medium")

    return "medium"


def _get_subtitle_style(energy: str) -> Dict:
    """根据能量获取字幕样式"""

    style_map = {
        "high": SUBTITLE_STYLES["impact"],
        "medium": SUBTITLE_STYLES["minimal"],
        "low": SUBTITLE_STYLES["minimal"],
    }

    return style_map.get(energy, SUBTITLE_STYLES["minimal"])


def _get_subtitle_style_name(energy: str) -> str:
    """根据能量获取字幕样式名称"""

    style_map = {
        "high": "impact",
        "medium": "minimal",
        "low": "minimal",
    }

    return style_map.get(energy, "minimal")


def main():
    parser = argparse.ArgumentParser(description="字幕同步模块")
    parser.add_argument("--asr", help="ASR 识别结果 JSON")
    parser.add_argument("--analysis", help="音乐情感分析 JSON（旧版）")
    parser.add_argument("--narrative", help="叙事脚本 JSON（旧版）")
    parser.add_argument("--output", default=None, help="输出 JSON 文件路径")
    parser.add_argument("--max-chars", type=int, default=8, help="每条字幕最大字数")
    args = parser.parse_args()

    if args.asr:
        with open(args.asr, "r", encoding="utf-8") as f:
            asr_result = json.load(f)
        subtitles = sync_subtitles_from_asr(asr_result, max_chars=args.max_chars)
    elif args.analysis and args.narrative:
        with open(args.analysis, "r", encoding="utf-8") as f:
            analysis = json.load(f)
        with open(args.narrative, "r", encoding="utf-8") as f:
            narrative = json.load(f)
        subtitles = sync_subtitles(analysis, narrative, args.output)
    else:
        print("[Error] 需要提供 --asr 或 --analysis/--narrative", file=sys.stderr)
        return

    if args.output is None:
        print(json.dumps(subtitles, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()