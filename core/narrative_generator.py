#!/usr/bin/env python3
"""
AI叙事脚本生成模块 — 根据音乐情感结构生成动态文案

根据 intro/verse/chorus/outro 结构，为每段生成匹配情感的文案：
- chorus (high energy) → 激烈、有力文案
- verse (medium energy) → 平稳、叙事文案
- intro/outro (low energy) → 引入、收束文案

用法:
    python3 -m core.narrative_generator --theme "东京夜行" --analysis analysis.json --output narrative.json

支持 Few-shot 风格迁移：
    通过 style_profile 参数传入参考文本的风格特征，实现风格迁移
"""

import argparse
import json
import sys
import urllib.request
from typing import Dict, List, Optional, Any

from config import DASHSCOPE_API_KEY
from core.logging_config import get_logger

logger = get_logger("narrative_generator")


# ── 叙事风格模板 ──

NARRATIVE_STYLES = {
    "热血": {
        "chorus": "爆发式短句，如：燃尽所有、绝不回头、撕裂夜空",
        "verse": "铺垫式描述，如：热血在燃烧、脚步不停歇",
        "intro": "引入氛围，如：夜幕降临、旅程开始",
        "outro": "收束沉淀，如：这就是我们的时刻",
    },
    "励志": {
        "chorus": "有力感悟，如：每一步都算数、人生没有白走的路",
        "verse": "温柔叙事，如：曾经迷茫、如今坚定",
        "intro": "启发开场，如：黎明前的黑暗",
        "outro": "沉淀收尾，如：奔赴下一场山海",
    },
    "治愈": {
        "chorus": "温暖高潮，如：找到内心的平静、此刻值得被记住",
        "verse": "舒缓叙事，如：慢慢走、不着急",
        "intro": "安静开场，如：闭上眼睛、听风的声音",
        "outro": "温柔收尾，如：一切都刚刚好",
    },
}


def generate_narrative(theme: str, analysis: Dict, style: Optional[str] = None,
                       output_json: Optional[str] = None,
                       style_profile: Optional[Dict[str, Any]] = None) -> Dict:
    """根据音乐情感分析生成叙事脚本

    Args:
        theme: 视频主题
        analysis: 音乐情感分析结果
        style: 指定风格（可选，默认使用 analysis 的 recommended_style）
        output_json: 输出 JSON 文件路径（可选）
        style_profile: 风格特征（可选，用于 Few-shot 风格迁移）

    Returns:
        dict: 叙事脚本结果
    """
    if not DASHSCOPE_API_KEY:
        logger.error("DASHSCOPE_API_KEY 未设置")
        return _fallback_narrative(theme, analysis)

    # 使用推荐风格
    if style is None:
        style = analysis.get("recommended_style", "励志")

    # 如果有风格特征，优先使用其风格标签
    if style_profile and style_profile.get("style_tags"):
        style = style_profile["style_tags"][0]

    logger.info(f"生成叙事脚本: theme={theme}, style={style}")

    try:
        # 构建结构描述
        structure_desc = _build_structure_prompt(analysis)

        # 调用 AI 生成（包含风格迁移）
        result = _call_ai_narrative(theme, style, structure_desc, analysis["duration"], style_profile)

        if result is None:
            return _fallback_narrative(theme, analysis)

        # 保存 JSON
        if output_json:
            with open(output_json, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info(f"输出已保存: {output_json}")

        return result

    except Exception as e:
        logger.error(f"叙事生成失败: {e}")
        return _fallback_narrative(theme, analysis, error=str(e))


def _build_structure_prompt(analysis: Dict) -> str:
    """构建音乐结构描述用于 AI prompt"""

    structure = analysis.get("structure", [])
    tension_peaks = analysis.get("tension_peaks", [])

    lines = []
    for seg in structure:
        lines.append(f"- {seg['type']} ({seg['start']}-{seg['end']}s, energy: {seg['energy']})")

    if tension_peaks:
        lines.append(f"\n张力峰值时间点: {', '.join(str(t) + 's' for t in tension_peaks)}")

    return "\n".join(lines)


def _call_ai_narrative(theme: str, style: str, structure_desc: str,
                       duration: float,
                       style_profile: Optional[Dict[str, Any]] = None) -> Optional[Dict]:
    """调用阿里百炼 AI 生成叙事脚本

    Args:
        theme: 视频主题
        style: 风格预设
        structure_desc: 音乐结构描述
        duration: 视频时长
        style_profile: 风格特征（可选）

    Returns:
        生成的叙事脚本，失败返回 None
    """
    style_template = NARRATIVE_STYLES.get(style, NARRATIVE_STYLES["励志"])

    # 基础风格提示
    style_prompt_parts = [
        f"风格要求 ({style})：",
        f"- chorus 段文案: {style_template['chorus']}",
        f"- verse 段文案: {style_template['verse']}",
        f"- intro 段文案: {style_template['intro']}",
        f"- outro 段文案: {style_template['outro']}",
    ]

    # 风格迁移提示（如果有）
    if style_profile:
        transfer_prompt = _build_style_transfer_prompt(style_profile)
        style_prompt_parts.append("\n参考风格特征（Few-shot 风格迁移）：")
        style_prompt_parts.append(transfer_prompt)

    style_prompt = "\n".join(style_prompt_parts)

    system_prompt = f"""你是 CutClaw 情感驱动视频文案生成器。

根据用户提供的视频主题和音乐情感结构，生成适合短视频传播的中英双语文案。

音乐结构信息：
{structure_desc}

{style_prompt}

请以 JSON 格式输出，包含以下字段：
- title_text: 4-8字标题（无标点）
- narration_script: 完整旁白文案（根据音乐结构分段，共约20-40字，无标点符号）
- english_text: 英文翻译（10-25词）
- segment_narrations: 数组，每项包含 segment_type, text, start, end
- subtitle_segments: 抖音风格字幕数组，每项包含 id, text_zh（4-8字，无标点，语义完整断句）, start, end

抖音字幕断句规则：
1. 每条字幕 4-8 字
2. 无标点符号（逗号、句号、感叹号等全部去掉）
3. 语义完整断句（如"闭上眼睛"不要拆成"闭上眼"+"睛"）
4. 在语气词后断开（的、了、着等）
5. 保持词组完整（如"听风的声音"作为整体）"""

    user_message = f"主题：{theme}\n时长：{duration}s\n请生成情感对齐的叙事脚本"

    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

    payload = json.dumps({
        "model": "qwen-plus",
        "max_tokens": 800,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
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

        # 提取 JSON
        json_start = full_text.find("{")
        json_end = full_text.rfind("}") + 1

        if json_start >= 0 and json_end > json_start:
            json_str = full_text[json_start:json_end]

            # 尝试直接解析
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON 解析失败，尝试修复: {e}")

                # 尝试修复常见问题
                # 1. 缺少引号
                # 2. 多余的逗号
                # 3. 不完整的 JSON

                # 使用正则提取关键字段
                return _extract_narrative_from_text(full_text)

    except Exception as e:
        logger.error(f"AI 调用失败: {e}")

    return None


def _extract_narrative_from_text(text: str) -> Optional[Dict]:
    """从 AI 返回文本中提取关键信息（JSON 解析失败时的备选）

    Args:
        text: AI 返回的完整文本

    Returns:
        dict: 提取的叙事脚本
    """
    import re

    result = {
        "title_text": "",
        "narration_script": "",
        "english_text": "",
        "segment_narrations": [],
        "subtitle_segments": [],
    }

    # 提取标题
    title_match = re.search(r'title_text["\s:]+(["\']?)([^"\'\n,}]+)', text)
    if title_match:
        result["title_text"] = title_match.group(2).strip()[:8]

    # 提取旁白文案
    narration_match = re.search(r'narration_script["\s:]+(["\']?)([^"\'\n]+)', text)
    if narration_match:
        result["narration_script"] = narration_match.group(2).strip()

    # 如果没有找到，尝试从文本中提取有意义的句子
    if not result["narration_script"]:
        # 找中文句子（抖音风格文案）
        chinese_sentences = re.findall(r'[闭上听慢每走此刻旅程故事人生脚步][^\n]{4,30}', text)
        if chinese_sentences:
            result["narration_script"] = " ".join(chinese_sentences[:6])

    # 提取英文翻译
    english_match = re.search(r'english_text["\s:]+(["\']?)([^"\'\n]+)', text)
    if english_match:
        result["english_text"] = english_match.group(2).strip()

    # 提取字幕片段
    subtitle_matches = re.findall(r'text_zh["\s:]+(["\']?)([^"\'\n,}]+)', text)
    for i, match in enumerate(subtitle_matches, 1):
        sub_text = match[1].strip()
        if sub_text and len(sub_text) >= 4:
            result["subtitle_segments"].append({
                "id": i,
                "text_zh": sub_text,
                "text_en": "",
                "start": 1.0 + i * 2.5,
                "end": 3.5 + i * 2.5,
            })

    # 如果没有提取到字幕，从旁白生成
    if not result["subtitle_segments"] and result["narration_script"]:
        # 按空格/逗号/句号分割
        parts = re.split(r'[，。！？\s]+', result["narration_script"])
        parts = [p.strip() for p in parts if p.strip() and len(p.strip()) >= 4]

        for i, part in enumerate(parts[:10], 1):
            result["subtitle_segments"].append({
                "id": i,
                "text_zh": part,
                "text_en": "",
                "start": 1.0 + i * 2.5,
                "end": 3.5 + i * 2.5,
            })

    # 验证基本字段
    if result["title_text"] or result["narration_script"]:
        logger.info(f"从文本提取叙事脚本: title={result['title_text']}, subs={len(result['subtitle_segments'])}条")
        return result

    return None


def _build_style_transfer_prompt(style_profile: Dict[str, Any]) -> str:
    """构建风格迁移提示词

    Args:
        style_profile: 风格特征字典

    Returns:
        风格迁移提示词
    """
    parts = []

    # 句式特征
    avg_len = style_profile.get("avg_sentence_length", 15)
    sentence_style = style_profile.get("sentence_style", "balanced")
    if sentence_style == "short":
        parts.append(f"句式风格：短句为主（平均{avg_len:.0f}字），节奏紧凑有力")
    elif sentence_style == "long":
        parts.append(f"句式风格：长句为主（平均{avg_len:.0f}字），娓娓道来，情感绵延")
    else:
        parts.append(f"句式风格：长短结合（平均{avg_len:.0f}字），节奏均衡")

    # 修辞手法
    rhetorical = style_profile.get("rhetorical_devices", [])
    if rhetorical:
        parts.append(f"修辞手法：{', '.join(rhetorical)}，请在文案中适度运用")

    # 情感特征
    sentiment_intensity = style_profile.get("sentiment_intensity", 0.5)
    dominant_emotion = style_profile.get("dominant_emotion", "neutral")
    parts.append(f"情感基调：{dominant_emotion}，强度{sentiment_intensity:.1f}")

    # 典型句式示例
    examples = style_profile.get("example_sentences", [])
    if examples:
        parts.append("\n参考句式示例（学习其表达方式）：")
        for ex in examples[:3]:
            parts.append(f"  - {ex}")

    return "\n".join(parts)


def _fallback_narrative(theme: str, analysis: Dict, error: str = "") -> Dict:
    """备用叙事脚本 - 抖音风格无标点断句"""

    duration = analysis.get("duration", 20)
    structure = analysis.get("structure", [])

    # 多样化默认文案（抖音风格，无标点）
    intro_texts = ["旅程从这里开始", "故事的起点", "一切刚刚开始"]
    verse_texts = ["每一步都在书写人生", "走过风雨迎来阳光", "脚步不停歇", "向前走不回头"]
    chorus_texts = ["此刻就是最好的时刻", "找到内心的平静", "一切都刚刚好"]
    outro_texts = ["旅程继续未来可期", "明天更值得期待", "下一站更精彩"]

    # 按类型选择文案（避免重复）
    used_texts = {"intro": [], "verse": [], "chorus": [], "outro": []}

    segment_narrations = []
    narration_parts = []

    for seg in structure:
        seg_type = seg["type"]

        # 选择未使用的文案
        text_pool = {
            "intro": intro_texts,
            "verse": verse_texts,
            "chorus": chorus_texts,
            "outro": outro_texts,
        }.get(seg_type, verse_texts)

        available = [t for t in text_pool if t not in used_texts[seg_type]]
        if not available:
            available = text_pool  # 用完了就重新用

        text = available[0] if available else "每一步都在书写人生"
        used_texts[seg_type].append(text)

        segment_narrations.append({
            "segment_type": seg_type,
            "text": text,
            "start": seg["start"],
            "end": seg["end"],
        })
        narration_parts.append(text)

    # 抖音风格字幕断句（每条 4-8 字）
    subtitle_segments = []
    current_time = 1.0
    subtitle_id = 1

    for text in narration_parts:
        # 拆分成抖音风格短句
        chunks = _douyin_split(text, max_chars=8)
        for chunk in chunks:
            subtitle_segments.append({
                "id": subtitle_id,
                "text_zh": chunk,
                "text_en": "",
                "start": current_time,
                "end": current_time + 2.5,
            })
            subtitle_id += 1
            current_time += 3.0

    return {
        "title_text": theme[:8],
        "narration_script": " ".join(narration_parts),  # 用空格连接
        "english_text": f"A journey about {theme}",
        "segment_narrations": segment_narrations,
        "subtitle_segments": subtitle_segments,
        "error": error,
        "fallback": True,
    }


def _douyin_split(text: str, max_chars: int = 8) -> List[str]:
    """抖音风格断句 - 无标点，语义完整

    Args:
        text: 文案文本
        max_chars: 每条最大字数

    Returns:
        list: 断句后的列表
    """
    # 如果文本短，直接返回
    if len(text) <= max_chars:
        return [text]

    # 在语气词后断开
    break_chars = ['的', '了', '着', '过', '好']

    result = []
    pos = 0

    while pos < len(text):
        remaining = len(text) - pos

        if remaining <= max_chars:
            result.append(text[pos:])
            break

        # 找断点
        best_end = min(pos + max_chars, len(text))

        # 优先在语气词后断开
        for end in range(pos + 4, min(pos + max_chars, len(text)) + 1):
            if text[end - 1] in break_chars:
                best_end = end
                break

        result.append(text[pos:best_end])
        pos = best_end

    return result


def main():
    parser = argparse.ArgumentParser(description="AI叙事脚本生成模块")
    parser.add_argument("--theme", required=True, help="视频主题")
    parser.add_argument("--analysis", required=True, help="音乐情感分析 JSON")
    parser.add_argument("--style", default=None, help="指定风格")
    parser.add_argument("--style-profile", default=None, help="风格特征 JSON（用于 Few-shot 风格迁移）")
    parser.add_argument("--output", default=None, help="输出 JSON 文件路径")
    args = parser.parse_args()

    # 加载分析结果
    with open(args.analysis, "r", encoding="utf-8") as f:
        analysis = json.load(f)

    # 加载风格特征（如果有）
    style_profile = None
    if args.style_profile:
        with open(args.style_profile, "r", encoding="utf-8") as f:
            style_profile = json.load(f)

    result = generate_narrative(args.theme, analysis, args.style, args.output, style_profile)

    if args.output is None:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()