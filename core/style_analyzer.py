#!/usr/bin/env python3
"""
风格分析器 — 从参考文本提取风格特征用于 Few-shot 风格迁移

支持：
1. analyze_style — 分析参考文本的风格特征
2. apply_style — 将风格应用到新文本生成
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from core.logging_config import get_logger
from core.exceptions import StyleAnalysisError

logger = get_logger("style_analyzer")


@dataclass
class StyleProfile:
    """风格特征"""
    # 句式特征
    avg_sentence_length: float = 0.0  # 平均句长
    sentence_style: str = "balanced"  # short/balanced/long

    # 词汇特征
    vocab_richness: float = 0.0  # 词汇丰富度 (type-token ratio)
    emotional_words_ratio: float = 0.0  # 情感词比例
    rhetorical_devices: List[str] = field(default_factory=list)  # 修辞手法

    # 结构特征
    structure_pattern: str = "linear"  # linear/parallel/climactic
    paragraph_count: int = 0

    # 情感特征
    sentiment_intensity: float = 0.5  # 0-1 情感强度
    dominant_emotion: str = "neutral"  # 主要情感

    # 风格标签
    style_tags: List[str] = field(default_factory=list)  # 热血/励志/治愈/文艺/欢快

    # 示例句子
    example_sentences: List[str] = field(default_factory=list)  # 典型句式示例

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "avg_sentence_length": self.avg_sentence_length,
            "sentence_style": self.sentence_style,
            "vocab_richness": self.vocab_richness,
            "emotional_words_ratio": self.emotional_words_ratio,
            "rhetorical_devices": self.rhetorical_devices,
            "structure_pattern": self.structure_pattern,
            "paragraph_count": self.paragraph_count,
            "sentiment_intensity": self.sentiment_intensity,
            "dominant_emotion": self.dominant_emotion,
            "style_tags": self.style_tags,
            "example_sentences": self.example_sentences,
        }


# 情感词库
EMOTIONAL_WORDS = {
    "positive": ["梦想", "希望", "力量", "勇气", "光明", "温暖", "美好", "幸福",
                 "成功", "奋斗", "拼搏", "坚持", "热爱", "感动", "奇迹", "辉煌"],
    "negative": ["挫折", "困难", "痛苦", "迷茫", "失落", "孤独", "悲伤", "遗憾"],
    "intense": ["热血", "燃烧", "爆发", "激昂", "震撼", "极致", "无尽", "永恒"],
    "calm": ["宁静", "安详", "柔和", "淡然", "舒缓", "治愈", "温婉", "恬淡"],
}

# 修辞手法检测模式
RHETORICAL_PATTERNS = {
    "排比": r"(.{2,8})[，,；;]\1[，,；;]\1",
    "对偶": r"(.{2,6})[，,；;](.{2,6})",
    "比喻": r"像|仿佛|如同|好比|似",
    "拟人": r"风儿|阳光|时光|岁月|星辰|大海.*说|笑|唱|舞",
    "夸张": r"最|极致|无尽|永恒|绝对|超级|无比",
    "反问": r"难道|岂能|怎能|何尝|为什么",
}

# 风格特征映射
STYLE_FEATURES = {
    "热血": {
        "avg_sentence_length_range": (8, 15),
        "emotional_words_ratio_min": 0.15,
        "rhetorical_devices": ["排比", "夸张", "比喻"],
        "dominant_emotions": ["intense", "positive"],
    },
    "励志": {
        "avg_sentence_length_range": (10, 18),
        "emotional_words_ratio_min": 0.10,
        "rhetorical_devices": ["排比", "对偶", "比喻"],
        "dominant_emotions": ["positive"],
    },
    "治愈": {
        "avg_sentence_length_range": (12, 25),
        "emotional_words_ratio_min": 0.05,
        "rhetorical_devices": ["比喻", "拟人"],
        "dominant_emotions": ["calm", "positive"],
    },
    "文艺": {
        "avg_sentence_length_range": (15, 30),
        "emotional_words_ratio_min": 0.08,
        "rhetorical_devices": ["比喻", "拟人", "对偶"],
        "dominant_emotions": ["calm"],
    },
    "欢快": {
        "avg_sentence_length_range": (5, 12),
        "emotional_words_ratio_min": 0.12,
        "rhetorical_devices": ["比喻", "夸张"],
        "dominant_emotions": ["positive"],
    },
}


class StyleAnalyzer:
    """风格分析器"""

    def __init__(self):
        """初始化"""
        pass

    def analyze_style(self, reference_text: str, output_json: str = None) -> StyleProfile:
        """分析参考文本的风格特征

        Args:
            reference_text: 参考文本
            output_json: 输出 JSON 路径（可选）

        Returns:
            StyleProfile 风格特征对象
        """
        try:
            # 基础分析
            sentences = self._split_sentences(reference_text)
            words = self._extract_words(reference_text)

            # 计算各项特征
            avg_length = self._calc_avg_sentence_length(sentences)
            vocab_richness = self._calc_vocab_richness(words)
            emotional_ratio = self._calc_emotional_words_ratio(words)
            rhetorical = self._detect_rhetorical_devices(reference_text)
            structure = self._analyze_structure(reference_text)
            sentiment = self._analyze_sentiment(words)

            # 确定风格标签
            style_tags = self._determine_style_tags(
                avg_length, emotional_ratio, rhetorical, sentiment
            )

            # 提取典型句子
            examples = self._extract_example_sentences(sentences, style_tags)

            # 构建风格特征
            profile = StyleProfile(
                avg_sentence_length=avg_length,
                sentence_style=self._classify_sentence_length(avg_length),
                vocab_richness=vocab_richness,
                emotional_words_ratio=emotional_ratio,
                rhetorical_devices=rhetorical,
                structure_pattern=structure,
                paragraph_count=len(reference_text.split("\n\n")),
                sentiment_intensity=sentiment["intensity"],
                dominant_emotion=sentiment["dominant"],
                style_tags=style_tags,
                example_sentences=examples[:5],
            )

            # 保存结果
            if output_json:
                self._save_profile(profile, output_json)

            logger.info(f"风格分析完成: tags={style_tags}, avg_len={avg_length:.1f}")
            return profile

        except Exception as e:
            logger.error(f"风格分析失败: {e}")
            raise StyleAnalysisError(f"风格分析失败: {e}")

    def _split_sentences(self, text: str) -> List[str]:
        """分句"""
        # 按标点分句
        sentences = re.split(r"[。！？；；\n]+", text)
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 2]

    def _extract_words(self, text: str) -> List[str]:
        """提取词语（简化版，按字符）"""
        # 移除标点和空白
        clean_text = re.sub(r"[^\w]", "", text)
        return list(clean_text)

    def _calc_avg_sentence_length(self, sentences: List[str]) -> float:
        """计算平均句长"""
        if not sentences:
            return 0.0
        lengths = [len(s) for s in sentences]
        return sum(lengths) / len(lengths)

    def _classify_sentence_length(self, avg_length: float) -> str:
        """分类句式风格"""
        if avg_length < 10:
            return "short"
        elif avg_length > 20:
            return "long"
        else:
            return "balanced"

    def _calc_vocab_richness(self, words: List[str]) -> float:
        """计算词汇丰富度（Type-Token Ratio）"""
        if not words:
            return 0.0
        unique = len(set(words))
        total = len(words)
        return unique / total

    def _calc_emotional_words_ratio(self, words: List[str]) -> float:
        """计算情感词比例"""
        if not words:
            return 0.0

        emotional_count = 0
        all_emotional = []
        for category_words in EMOTIONAL_WORDS.values():
            all_emotional.extend(category_words)

        for word in words:
            # 检查是否包含情感词
            for ew in all_emotional:
                if ew in "".join(words):
                    emotional_count += 1
                    break

        # 简化计算：统计情感词出现次数
        text = "".join(words)
        for ew in all_emotional:
            if ew in text:
                emotional_count += text.count(ew)

        return min(emotional_count / max(len(words), 1), 1.0)

    def _detect_rhetorical_devices(self, text: str) -> List[str]:
        """检测修辞手法"""
        devices = []
        for device, pattern in RHETORICAL_PATTERNS.items():
            if re.search(pattern, text):
                devices.append(device)
        return devices

    def _analyze_structure(self, text: str) -> str:
        """分析文本结构"""
        paragraphs = text.split("\n\n")

        if len(paragraphs) <= 2:
            return "linear"

        # 检查是否有递进结构
        first_len = len(paragraphs[0]) if paragraphs else 0
        last_len = len(paragraphs[-1]) if paragraphs else 0

        if last_len > first_len * 1.5:
            return "climactic"

        # 检查是否有并列结构
        lengths = [len(p) for p in paragraphs]
        avg_len = sum(lengths) / len(lengths)
        variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)

        if variance < 100:
            return "parallel"

        return "linear"

    def _analyze_sentiment(self, words: List[str]) -> Dict[str, Any]:
        """分析情感"""
        text = "".join(words)

        # 计算各情感类别词频
        scores = {}
        for category, words_list in EMOTIONAL_WORDS.items():
            count = sum(1 for w in words_list if w in text)
            scores[category] = count

        # 确定主要情感
        if scores.get("intense", 0) > 0:
            dominant = "intense"
        elif scores.get("positive", 0) > scores.get("negative", 0):
            dominant = "positive"
        elif scores.get("calm", 0) > 0:
            dominant = "calm"
        elif scores.get("negative", 0) > 0:
            dominant = "negative"
        else:
            dominant = "neutral"

        # 计算情感强度
        total_emotional = sum(scores.values())
        intensity = min(total_emotional / 10, 1.0)

        return {"dominant": dominant, "intensity": intensity}

    def _determine_style_tags(
        self,
        avg_length: float,
        emotional_ratio: float,
        rhetorical: List[str],
        sentiment: Dict
    ) -> List[str]:
        """确定风格标签"""
        tags = []

        for style_name, features in STYLE_FEATURES.items():
            min_len, max_len = features["avg_sentence_length_range"]
            min_ratio = features["emotional_words_ratio_min"]
            required_rhetorical = features["rhetorical_devices"]
            required_emotions = features["dominant_emotions"]

            # 检查是否匹配
            length_match = min_len <= avg_length <= max_len
            ratio_match = emotional_ratio >= min_ratio
            rhetorical_match = any(r in required_rhetorical for r in rhetorical)
            emotion_match = sentiment["dominant"] in required_emotions

            # 至少满足3项才标记
            match_count = sum([length_match, ratio_match, rhetorical_match, emotion_match])
            if match_count >= 3:
                tags.append(style_name)

        # 如果没有匹配，根据情感推断
        if not tags:
            if sentiment["dominant"] == "intense":
                tags.append("热血")
            elif sentiment["dominant"] == "positive":
                tags.append("励志")
            elif sentiment["dominant"] == "calm":
                tags.append("治愈")
            else:
                tags.append("文艺")

        return tags

    def _extract_example_sentences(
        self,
        sentences: List[str],
        style_tags: List[str]
    ) -> List[str]:
        """提取典型句子"""
        examples = []

        # 优先选择包含修辞手法的句子
        for s in sentences:
            has_rhetorical = any(
                re.search(pattern, s)
                for pattern in RHETORICAL_PATTERNS.values()
            )
            if has_rhetorical:
                examples.append(s)

        # 补充长句或短句
        if len(examples) < 3:
            sorted_sentences = sorted(sentences, key=len, reverse=True)
            for s in sorted_sentences[:5]:
                if s not in examples:
                    examples.append(s)

        return examples

    def _save_profile(self, profile: StyleProfile, output_json: str):
        """保存风格特征到文件"""
        path = Path(output_json)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f, ensure_ascii=False, indent=2)

        logger.info(f"风格特征保存: {path}")

    def generate_style_prompt(self, profile: StyleProfile) -> str:
        """生成风格迁移提示词

        Args:
            profile: 风格特征

        Returns:
            风格迁移提示词
        """
        prompt_parts = [
            f"风格要求：{', '.join(profile.style_tags)}",
            f"句式风格：平均句长{profile.avg_sentence_length:.1f}字，"
            f"{'短句为主，节奏紧凑' if profile.sentence_style == 'short' else '长句为主，娓娓道来' if profile.sentence_style == 'long' else '长短结合，节奏均衡'}",
            f"修辞手法：{', '.join(profile.rhetorical_devices) if profile.rhetorical_devices else '自然朴实'}",
            f"情感基调：{profile.dominant_emotion}，强度{profile.sentiment_intensity:.1f}",
        ]

        if profile.example_sentences:
            prompt_parts.append(f"参考句式示例：\n{chr(10).join(f'- {s}' for s in profile.example_sentences[:3])}")

        return "\n".join(prompt_parts)


# 全局实例
_analyzer = None


def get_style_analyzer() -> StyleAnalyzer:
    """获取风格分析器实例"""
    global _analyzer
    if _analyzer is None:
        _analyzer = StyleAnalyzer()
    return _analyzer


def analyze_reference_style(text: str, output_json: str = None) -> StyleProfile:
    """分析参考文本风格（便捷函数）"""
    return get_style_analyzer().analyze_style(text, output_json)


def generate_style_transfer_prompt(profile: StyleProfile) -> str:
    """生成风格迁移提示词（便捷函数）"""
    return get_style_analyzer().generate_style_prompt(profile)