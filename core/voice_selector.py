#!/usr/bin/env python3
"""
音色选择模块 — 根据文案自动推荐 TTS 音色

分析维度：
1. 情感基调（关键词匹配）
2. 内容类型（主题分类）
3. 语言判断（中英文占比）
4. 节奏强度（文案结构）

输出：
- 推荐音色配置
- MOSS-TTS 指令模板
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass


# ── 音色配置 ──

@dataclass
class VoiceProfile:
    """音色配置"""
    voice_id: str           # TTS 音色 ID
    gender: str             # 性别 (male/female)
    age: str                # 年龄段 (young/middle/senior)
    tone: str               # 语调风格
    language: str           # 语言 (zh/en)
    tts_instruction: str    # MOSS-TTS 指令
    description: str        # 中文描述


# ── 预设音色库 ──

VOICE_LIBRARY = {
    # 中文男声
    "zh_male_qingnian": VoiceProfile(
        voice_id="zh_male_qingnian",
        gender="male", age="young", tone="energetic",
        language="zh",
        tts_instruction="年轻男性声音，语调有力、充满激情，语速稍快",
        description="青年男声 - 热血活力"
    ),
    "zh_male_chengnian": VoiceProfile(
        voice_id="zh_male_chengnian",
        gender="male", age="middle", tone="firm",
        language="zh",
        tts_instruction="中年男性声音，语调稳重、深沉有力，语速适中",
        description="成年男声 - 稳重深沉"
    ),
    "zh_male_senior": VoiceProfile(
        voice_id="zh_male_senior",
        gender="male", age="senior", tone="wise",
        language="zh",
        tts_instruction="老年男性声音，语调慈祥、缓慢从容，语速较慢",
        description="老年男声 - 智慧从容"
    ),

    # 中文女声
    "zh_female_shaonian": VoiceProfile(
        voice_id="zh_female_shaonian",
        gender="female", age="young", tone="lively",
        language="zh",
        tts_instruction="年轻女性声音，语调活泼、清脆悦耳，语速稍快",
        description="少女声 - 活泼清脆"
    ),
    "zh_female_chengnian": VoiceProfile(
        voice_id="zh_female_chengnian",
        gender="female", age="middle", tone="warm",
        language="zh",
        tts_instruction="成年女性声音，语调温柔、舒缓治愈，语速适中",
        description="成年女声 - 温暖治愈"
    ),
    "zh_female_senior": VoiceProfile(
        voice_id="zh_female_senior",
        gender="female", age="senior", tone="kind",
        language="zh",
        tts_instruction="老年女性声音，语调慈祥、温和缓慢，语速较慢",
        description="老年女声 - 慈祥温和"
    ),

    # 英文音色
    "en_male_young": VoiceProfile(
        voice_id="en_male_young",
        gender="male", age="young", tone="energetic",
        language="en",
        tts_instruction="Young male voice, energetic and upbeat, moderate speed",
        description="English Young Male - Energetic"
    ),
    "en_female_young": VoiceProfile(
        voice_id="en_female_young",
        gender="female", age="young", tone="friendly",
        language="en",
        tts_instruction="Young female voice, friendly and clear, moderate speed",
        description="English Young Female - Friendly"
    ),
}


# ── 情感关键词词典 ──

EMOTION_KEYWORDS = {
    "energetic": [
        "奋斗", "拼搏", "热血", "梦想", "冲刺", "爆发", "挑战", "突破",
        "激情", "力量", "燃烧", "奔跑", "战斗", "胜利", "崛起", "逆袭"
    ],
    "calm": [
        "宁静", "治愈", "温柔", "安详", "静谧", "舒缓", "平和", "安心",
        "放松", "沉浸", "享受", "慢生活", "冥想", "疗愈", "温暖", "舒适"
    ],
    "serious": [
        "思考", "人生", "意义", "深度", "哲理", "沉淀", "智慧", "感悟",
        "岁月", "经历", "回忆", "故事", "传承", "历史", "经典", "永恒"
    ],
    "lively": [
        "美食", "旅行", "节日", "欢快", "精彩", "快乐", "开心", "有趣",
        "活泼", "俏皮", "可爱", "青春", "阳光", "活力", "新鲜", "创意"
    ],
    "sad": [
        "离别", "思念", "遗憾", "伤感", "孤独", "寂寞", "眼泪", "难过",
        "失落", "惆怅", "回忆", "曾经", "往事", "告别", "再见", "错过"
    ],
    "romantic": [
        "爱情", "浪漫", "甜蜜", "心动", "喜欢", "告白", "邂逅", "缘分",
        "陪伴", "守护", "温柔", "浪漫", "爱情", "心动", "约定", "承诺"
    ],
}


# ── 内容类型映射 ──

CONTENT_TYPE_MAP = {
    "business": ["商业", "创业", "公司", "企业", "投资", "经济", "市场", "战略"],
    "tech": ["科技", "AI", "人工智能", "创新", "数字", "智能", "未来", "技术"],
    "life": ["生活", "日常", "家庭", "亲情", "友情", "日常", "简单", "平凡"],
    "travel": ["旅行", "旅游", "风景", "城市", "景点", "探索", "世界", "远方"],
    "food": ["美食", "料理", "餐厅", "厨房", "味道", "佳肴", "烹饪", "食材"],
    "culture": ["文化", "艺术", "历史", "传统", "经典", "传承", "人文", "故事"],
}


# ── 风格预设 → 音色推荐 ──

STYLE_VOICE_MAP = {
    "热血": "zh_male_qingnian",
    "励志": "zh_male_chengnian",
    "治愈": "zh_female_chengnian",
    "文艺": "zh_female_shaonian",
    "欢快": "zh_female_shaonian",
    "深沉": "zh_male_senior",
    "浪漫": "zh_female_shaonian",
}


# ── MOSS-TTS 指令模板 ──

MOSS_TTS_TEMPLATES = {
    # 语速模板
    "speed_fast": "语速较快，节奏紧凑",
    "speed_normal": "语速适中，节奏平稳",
    "speed_slow": "语速缓慢，节奏从容",

    # 停顿模板
    "pause_short": "句间停顿较短，连贯流畅",
    "pause_normal": "句间停顿适中，自然过渡",
    "pause_long": "句间停顿较长，留有余味",

    # 情感模板
    "emotion_energetic": "充满激情，语气有力",
    "emotion_calm": "语气平和，舒缓放松",
    "emotion_warm": "语气温柔，温暖治愈",
    "emotion_serious": "语气沉稳，庄重有力",
    "emotion_lively": "语气活泼，俏皮可爱",

    # 综合模板（预设组合）
    "preset_energetic": "年轻声音，充满激情，语速稍快，句间停顿短，节奏紧凑有力",
    "preset_calm": "温柔声音，舒缓治愈，语速适中，句间停顿适中，平稳自然",
    "preset_storytelling": "稳重声音，讲故事风格，语速较慢，句间停顿长，留有余味",
    "preset_news": "专业播音腔，语速适中，句间停顿短，清晰有力",
    "preset_podcast": "轻松聊天风格，语速适中，句间停顿适中，自然亲切",
}


def select_voice(
    narrative: str,
    style: Optional[str] = None,
    music_analysis: Optional[Dict] = None,
) -> Dict:
    """根据文案自动推荐音色

    Args:
        narrative: 叙事文案
        style: 风格预设（可选）
        music_analysis: 音乐情感分析结果（可选）

    Returns:
        {
            "recommended_voice": VoiceProfile,
            "alternative_voices": List[VoiceProfile],
            "detected_emotion": str,
            "detected_content_type": str,
            "language": str,
            "templates": Dict[str, str],  # MOSS-TTS 指令模板
        }
    """
    # 1. 语言判断
    language = detect_language(narrative)

    # 2. 情感分析
    emotion = analyze_emotion(narrative)

    # 3. 内容类型判断
    content_type = analyze_content_type(narrative)

    # 4. 综合音乐情感（如果有）
    if music_analysis:
        music_emotion = music_analysis.get("recommended_style", "")
        if music_emotion in STYLE_VOICE_MAP:
            # 音乐情感权重较高
            emotion = music_emotion

    # 5. 选择推荐音色
    # 优先使用风格预设
    if style and style in STYLE_VOICE_MAP:
        recommended_voice_id = STYLE_VOICE_MAP[style]
    else:
        recommended_voice_id = map_emotion_to_voice(emotion, content_type, language)

    recommended_voice = VOICE_LIBRARY.get(recommended_voice_id)

    # 6. 获取备选音色
    alternative_voices = get_alternative_voices(emotion, language)

    # 7. 获取相关模板
    templates = get_relevant_templates(emotion)

    return {
        "recommended_voice": recommended_voice.__dict__ if recommended_voice else None,
        "alternative_voices": [v.__dict__ for v in alternative_voices],
        "detected_emotion": emotion,
        "detected_content_type": content_type,
        "language": language,
        "templates": templates,
    }


def detect_language(text: str) -> str:
    """检测文本语言"""
    # 统计中文字符
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    total_chars = len(text.replace(" ", ""))

    if total_chars == 0:
        return "zh"

    chinese_ratio = chinese_chars / total_chars

    if chinese_ratio > 0.7:
        return "zh"
    elif chinese_ratio < 0.3:
        return "en"
    else:
        return "zh"  # 混合默认中文


def analyze_emotion(text: str) -> str:
    """分析文本情感"""
    emotion_scores = {}

    for emotion, keywords in EMOTION_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword in text:
                score += text.count(keyword)
        emotion_scores[emotion] = score

    # 取最高分情感
    if emotion_scores:
        max_emotion = max(emotion_scores.keys(), key=lambda k: emotion_scores[k])
        if emotion_scores[max_emotion] > 0:
            return max_emotion

    # 默认
    return "calm"


def analyze_content_type(text: str) -> str:
    """分析内容类型"""
    type_scores = {}

    for content_type, keywords in CONTENT_TYPE_MAP.items():
        score = sum(1 for kw in keywords if kw in text)
        type_scores[content_type] = score

    if type_scores:
        max_type = max(type_scores.keys(), key=lambda k: type_scores[k])
        if type_scores[max_type] > 0:
            return max_type

    return "life"


def map_emotion_to_voice(emotion: str, content_type: str, language: str) -> str:
    """将情感映射到音色"""
    # 情感 → 性别/年龄段映射
    EMOTION_VOICE_MAP = {
        "energetic": {"gender": "male", "age": "young"},
        "calm": {"gender": "female", "age": "middle"},
        "serious": {"gender": "male", "age": "senior"},
        "lively": {"gender": "female", "age": "young"},
        "sad": {"gender": "female", "age": "middle"},
        "romantic": {"gender": "female", "age": "young"},
    }

    # 内容类型调整
    CONTENT_ADJUST = {
        "business": {"gender": "male", "age": "middle"},
        "tech": {"gender": "male", "age": "young"},
        "life": {"gender": "female", "age": "middle"},
        "travel": {"gender": "female", "age": "young"},
        "food": {"gender": "female", "age": "young"},
        "culture": {"gender": "male", "age": "senior"},
    }

    # 综合判断
    voice_attrs = EMOTION_VOICE_MAP.get(emotion, {"gender": "female", "age": "middle"})

    # 内容类型调整（权重 30%）
    content_attrs = CONTENT_ADJUST.get(content_type, {})

    # 合并（情感优先）
    if content_attrs:
        # 如果内容类型强烈，可调整
        if content_type in ["business", "tech"]:
            voice_attrs["gender"] = content_attrs.get("gender", voice_attrs["gender"])

    # 根据语言选择音色 ID
    if language == "en":
        if voice_attrs["gender"] == "male":
            return "en_male_young"
        else:
            return "en_female_young"

    # 中文音色
    gender = voice_attrs["gender"]
    age = voice_attrs["age"]

    voice_id_map = {
        ("male", "young"): "zh_male_qingnian",
        ("male", "middle"): "zh_male_chengnian",
        ("male", "senior"): "zh_male_senior",
        ("female", "young"): "zh_female_shaonian",
        ("female", "middle"): "zh_female_chengnian",
        ("female", "senior"): "zh_female_senior",
    }

    return voice_id_map.get((gender, age), "zh_female_chengnian")


def get_alternative_voices(emotion: str, language: str) -> List[VoiceProfile]:
    """获取备选音色"""
    # 同情感不同性别/年龄
    alternatives = []

    # 根据语言获取同语言的其他音色
    for voice_id, profile in VOICE_LIBRARY.items():
        if profile.language == language:
            # 排除自己
            if profile.tone != emotion and profile.age != "senior":
                alternatives.append(profile)

    # 返回前 3 个
    return alternatives[:3]


def get_relevant_templates(emotion: str) -> Dict[str, str]:
    """获取相关 MOSS-TTS 模板"""
    templates = {}

    # 语速模板（全部提供）
    templates.update({
        k: v for k, v in MOSS_TTS_TEMPLATES.items()
        if k.startswith("speed_")
    })

    # 停顿模板（全部提供）
    templates.update({
        k: v for k, v in MOSS_TTS_TEMPLATES.items()
        if k.startswith("pause_")
    })

    # 情感模板（根据情感推荐）
    emotion_template_map = {
        "energetic": "emotion_energetic",
        "calm": "emotion_calm",
        "serious": "emotion_serious",
        "lively": "emotion_lively",
        "sad": "emotion_calm",
        "romantic": "emotion_warm",
    }

    emotion_key = emotion_template_map.get(emotion, "emotion_calm")
    templates["recommended_emotion"] = MOSS_TTS_TEMPLATES[emotion_key]

    # 预设组合模板
    templates.update({
        k: v for k, v in MOSS_TTS_TEMPLATES.items()
        if k.startswith("preset_")
    })

    return templates


def generate_custom_instruction(
    voice_profile: VoiceProfile,
    speed_template: str = None,
    pause_template: str = None,
    emotion_template: str = None,
) -> str:
    """生成自定义 MOSS-TTS 指令

    Args:
        voice_profile: 音色配置
        speed_template: 语速模板 key
        pause_template: 停顿模板 key
        emotion_template: 情感模板 key

    Returns:
        组合后的自然语言指令
    """
    parts = [voice_profile.tts_instruction]

    if speed_template and speed_template in MOSS_TTS_TEMPLATES:
        parts.append(MOSS_TTS_TEMPLATES[speed_template])

    if pause_template and pause_template in MOSS_TTS_TEMPLATES:
        parts.append(MOSS_TTS_TEMPLATES[pause_template])

    if emotion_template and emotion_template in MOSS_TTS_TEMPLATES:
        parts.append(MOSS_TTS_TEMPLATES[emotion_template])

    return "，".join(parts)


# ── CLI 测试 ──

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="音色选择测试")
    parser.add_argument("--text", required=True, help="测试文案")
    parser.add_argument("--style", default=None, help="风格预设")
    args = parser.parse_args()

    result = select_voice(args.text, args.style)

    print(f"\n{'='*50}")
    print(f"  文案: {args.text[:50]}...")
    print(f"  检测语言: {result['language']}")
    print(f"  检测情感: {result['detected_emotion']}")
    print(f"  内容类型: {result['detected_content_type']}")
    print(f"{'='*50}\n")

    if result["recommended_voice"]:
        voice = result["recommended_voice"]
        print(f"推荐音色: {voice['voice_id']}")
        print(f"  描述: {voice['description']}")
        print(f"  指令: {voice['tts_instruction']}\n")

    print("备选音色:")
    for alt in result["alternative_voices"]:
        print(f"  - {alt['voice_id']}: {alt['description']}")

    print(f"\n可用模板:")
    for key, value in result["templates"].items():
        print(f"  {key}: {value}")