#!/usr/bin/env python3
"""
多语言叙事 — 支持中英文叙事生成，自动翻译字幕

支持：
1. generate_multilingual_narrative — 生成多语言叙事
2. translate_subtitle — 翻译字幕
3. detect_language — 检测语言
"""

import json
import urllib.request
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from config import DASHSCOPE_API_KEY
from core.logging_config import get_logger
from core.exceptions import TranslationError

logger = get_logger("multilingual_narrative")


@dataclass
class MultilingualNarrative:
    """多语言叙事"""
    title_zh: str = ""
    title_en: str = ""

    narration_zh: str = ""
    narration_en: str = ""

    subtitles: List[Dict[str, Any]] = field(default_factory=list)

    language: str = "zh"  # 主要语言

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title_zh": self.title_zh,
            "title_en": self.title_en,
            "narration_zh": self.narration_zh,
            "narration_en": self.narration_en,
            "subtitles": self.subtitles,
            "language": self.language,
        }


# 语言代码映射
LANGUAGE_MAP = {
    "zh": "Chinese",
    "en": "English",
    "ja": "Japanese",
    "ko": "Korean",
}


class MultilingualNarrativeGenerator:
    """多语言叙事生成器"""

    def __init__(self):
        """初始化"""
        pass

    def generate_multilingual_narrative(
        self,
        theme: str,
        analysis: Dict[str, Any],
        style: str = None,
        languages: List[str] = ["zh", "en"],
        output_json: str = None
    ) -> MultilingualNarrative:
        """生成多语言叙事

        Args:
            theme: 视频主题
            analysis: 音乐分析结果
            style: 风格预设
            languages: 语言列表
            output_json: 输出 JSON 路径（可选）

        Returns:
            MultilingualNarrative 多语言叙事对象
        """
        narrative = MultilingualNarrative()

        # 先生成中文叙事
        from core.narrative_generator import generate_narrative

        zh_result = generate_narrative(theme, analysis, style, None)

        narrative.title_zh = zh_result.get("title_text", theme[:8])
        narrative.narration_zh = zh_result.get("narration_script", "")
        narrative.language = languages[0]

        # 生成英文版本
        if "en" in languages:
            en_result = self._generate_english_version(theme, analysis, style, zh_result)

            narrative.title_en = en_result.get("title_text", "")
            narrative.narration_en = en_result.get("narration_script", "")

        # 生成双语字幕
        narrative.subtitles = self._generate_bilingual_subtitles(
            zh_result, narrative.narration_en, analysis
        )

        # 保存结果
        if output_json:
            with open(output_json, "w", encoding="utf-8") as f:
                json.dump(narrative.to_dict(), f, ensure_ascii=False, indent=2)

        logger.info(f"多语言叙事生成: languages={languages}")
        return narrative

    def _generate_english_version(
        self,
        theme: str,
        analysis: Dict[str, Any],
        style: str,
        zh_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成英文版本

        Args:
            theme: 视频主题
            analysis: 音乐分析结果
            style: 风格预设
            zh_result: 中文叙事结果

        Returns:
            英文叙事结果
        """
        if not DASHSCOPE_API_KEY:
            # 使用翻译
            return self._translate_narrative(zh_result, "zh", "en")

        # 调用 AI 生成英文叙事
        try:
            return self._call_ai_english_narrative(theme, analysis, style, zh_result)
        except Exception as e:
            logger.warning(f"英文叙事生成失败: {e}，使用翻译")
            return self._translate_narrative(zh_result, "zh", "en")

    def _call_ai_english_narrative(
        self,
        theme: str,
        analysis: Dict[str, Any],
        style: str,
        zh_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """调用 AI 生成英文叙事"""
        duration = analysis.get("duration", 20)

        system_prompt = f"""You are a multilingual video narrative generator.

Generate an English narrative for a short video based on the theme and music structure.

Chinese version for reference:
- Title: {zh_result.get('title_text', '')}
- Narration: {zh_result.get('narration_script', '')}

Style: {style or '励志'}

Output JSON format:
- title_text: Short English title (4-8 words)
- narration_script: Full English narration (20-40 words)
- english_text: A single sentence summary (10-25 words)"""

        user_message = f"Theme: {theme}\nDuration: {duration}s\nGenerate English narrative"

        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

        payload = json.dumps({
            "model": "qwen-plus",
            "max_tokens": 400,
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

        response = urllib.request.urlopen(req, timeout=30)
        result_data = json.loads(response.read().decode("utf-8"))

        full_text = result_data["choices"][0].get("message", {}).get("content", "")

        # 提取 JSON
        json_start = full_text.find("{")
        json_end = full_text.rfind("}") + 1

        if json_start >= 0 and json_end > json_start:
            return json.loads(full_text[json_start:json_end])

        return {}

    def _translate_narrative(
        self,
        zh_result: Dict[str, Any],
        from_lang: str,
        to_lang: str
    ) -> Dict[str, Any]:
        """翻译叙事

        Args:
            zh_result: 中文叙事结果
            from_lang: 源语言
            to_lang: 目标语言

        Returns:
            翻译后的叙事结果
        """
        title_zh = zh_result.get("title_text", "")
        narration_zh = zh_result.get("narration_script", "")

        title_en = self._translate_text(title_zh, from_lang, to_lang)
        narration_en = self._translate_text(narration_zh, from_lang, to_lang)

        return {
            "title_text": title_en,
            "narration_script": narration_en,
            "english_text": narration_en[:50] + "...",
        }

    def _translate_text(
        self,
        text: str,
        from_lang: str,
        to_lang: str
    ) -> str:
        """翻译文本

        Args:
            text: 要翻译的文本
            from_lang: 源语言
            to_lang: 目标语言

        Returns:
            翻译后的文本
        """
        if not text:
            return ""

        if not DASHSCOPE_API_KEY:
            logger.warning("无翻译 API，返回原文")
            return text

        try:
            url = "https://dashscope.aliyuncs.com/api/v1/services/ai-translation/text-translate"

            payload = json.dumps({
                "model": "qwen-translate",
                "input": {
                    "text": text,
                    "source_language": LANGUAGE_MAP.get(from_lang, "Chinese"),
                    "target_language": LANGUAGE_MAP.get(to_lang, "English"),
                }
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

            response = urllib.request.urlopen(req, timeout=30)
            result_data = json.loads(response.read().decode("utf-8"))

            return result_data.get("output", {}).get("translated_text", text)

        except Exception as e:
            logger.error(f"翻译失败: {e}")
            return text

    def _generate_bilingual_subtitles(
        self,
        zh_result: Dict[str, Any],
        narration_en: str,
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成双语字幕

        Args:
            zh_result: 中文叙事结果
            narration_en: 英文叙事
            analysis: 音乐分析结果

        Returns:
            双语字幕列表
        """
        subtitles = []

        zh_subtitles = zh_result.get("subtitle_segments", [])

        for zh_sub in zh_subtitles:
            text_zh = zh_sub.get("text_zh", "")

            # 翻译字幕
            text_en = self._translate_text(text_zh, "zh", "en")

            subtitle = {
                "id": zh_sub.get("id", ""),
                "text_zh": text_zh,
                "text_en": text_en,
                "start": zh_sub.get("start", 0),
                "end": zh_sub.get("end", 0),
            }

            subtitles.append(subtitle)

        return subtitles

    def translate_subtitle(
        self,
        subtitles: List[Dict[str, Any]],
        from_lang: str,
        to_lang: str
    ) -> List[Dict[str, Any]]:
        """翻译字幕列表

        Args:
            subtitles: 字幕列表
            from_lang: 源语言
            to_lang: 目标语言

        Returns:
            翻译后的字幕列表
        """
        translated = []

        for sub in subtitles:
            text_from = sub.get("text_zh", sub.get("text_en", ""))
            text_to = self._translate_text(text_from, from_lang, to_lang)

            translated_sub = {
                "id": sub.get("id", ""),
                "text_zh": text_from if from_lang == "zh" else text_to,
                "text_en": text_to if to_lang == "en" else text_from,
                "start": sub.get("start", 0),
                "end": sub.get("end", 0),
            }

            translated.append(translated_sub)

        return translated


# 全局实例
_generator = None


def get_multilingual_generator() -> MultilingualNarrativeGenerator:
    """获取多语言生成器实例"""
    global _generator
    if _generator is None:
        _generator = MultilingualNarrativeGenerator()
    return _generator


def generate_multilingual_narrative(
    theme: str,
    analysis: Dict[str, Any],
    style: str = None,
    languages: List[str] = ["zh", "en"],
    output_json: str = None
) -> MultilingualNarrative:
    """生成多语言叙事（便捷函数）"""
    return get_multilingual_generator().generate_multilingual_narrative(
        theme, analysis, style, languages, output_json
    )


def translate_subtitle(
    subtitles: List[Dict[str, Any]],
    from_lang: str,
    to_lang: str
) -> List[Dict[str, Any]]:
    """翻译字幕（便捷函数）"""
    return get_multilingual_generator().translate_subtitle(subtitles, from_lang, to_lang)