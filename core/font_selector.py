#!/usr/bin/env python3
"""
字体选择器 — 风格匹配推荐

支持：
1. 按 class/lang 搜索
2. 按 style 预设推荐
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

from core.logging_config import get_logger

logger = get_logger("font_selector")


class FontSelector:
    """字体选择器"""

    def __init__(self, meta_path: str = None):
        """初始化字体选择器

        Args:
            meta_path: font_info.json 文件路径
        """
        if meta_path is None:
            meta_path = str(Path(__file__).parent.parent / "resource/fonts/font_info.json")

        self.meta_path = meta_path
        self.fonts = self._load_meta()

    def _load_meta(self) -> List[Dict[str, Any]]:
        """加载字体元数据"""
        if os.path.exists(self.meta_path):
            with open(self.meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("fonts", [])
        return []

    def search(
        self,
        font_class: str = None,
        lang: str = None
    ) -> List[Dict[str, Any]]:
        """搜索字体

        Args:
            font_class: 字体分类 (Creative, Handwriting, Calligraphy, Basic)
            lang: 语言 (zh, en)

        Returns:
            匹配的字体列表
        """
        results = []

        for font in self.fonts:
            tags = font.get("tags", {})

            # class 匹配
            if font_class:
                track_class = tags.get("class", "")
                if font_class != track_class:
                    continue

            # lang 匹配
            if lang:
                track_lang = tags.get("lang", "")
                if lang != track_lang:
                    continue

            results.append(font)

        return results

    def recommend(
        self,
        style: str = None,
        lang: str = "zh"
    ) -> Dict[str, Any]:
        """根据风格推荐字体

        Args:
            style: 风格预设 (热血, 劝志, 治愈, 文艺, 欢快)
            lang: 语言

        Returns:
            推荐的字体信息
        """
        # 风格 → class 映射
        style_class_map = {
            "热血": "Creative",
            "励志": "Basic",
            "治愈": "Basic",
            "文艺": "Calligraphy",
            "欢快": "Creative",
        }

        font_class = style_class_map.get(style, "Basic")

        matches = self.search(font_class=font_class, lang=lang)

        if matches:
            return matches[0]

        # Fallback: 返回默认字体
        return self.get_default_font(lang)

    def get_default_font(self, lang: str = "zh") -> Dict[str, Any]:
        """获取默认字体

        Args:
            lang: 语言

        Returns:
            默认字体信息
        """
        matches = self.search(font_class="Basic", lang=lang)
        if matches:
            return matches[0]

        # 系统字体 fallback
        return {
            "id": "system_default",
            "name": "System Font",
            "file": "/System/Library/Fonts/PingFang.ttc" if lang == "zh" else "/System/Library/Fonts/Helvetica.ttc",
            "description": "系统默认字体",
            "tags": {"class": "Basic", "lang": lang},
            "styles": ["Regular", "Bold"]
        }

    def get_font_path(self, font_id: str) -> Optional[str]:
        """获取字体文件路径

        Args:
            font_id: 字体 ID

        Returns:
            文件路径
        """
        for font in self.fonts:
            if font["id"] == font_id:
                return font.get("file", "")
        return None


# 全局选择器实例
_selector = None


def get_font_selector() -> FontSelector:
    """获取字体选择器实例"""
    global _selector
    if _selector is None:
        _selector = FontSelector()
    return _selector


def recommend_font(style: str = None, lang: str = "zh") -> Dict[str, Any]:
    """推荐字体（便捷函数）"""
    return get_font_selector().recommend(style, lang)