#!/usr/bin/env python3
"""
智能推荐引擎 — 自动推荐最佳配置组合

支持：
1. analyze_theme — 分析主题关键词，推荐风格
2. recommend_config — 根据音乐+主题推荐完整配置
3. learn_from_feedback — 从用户反馈学习优化推荐
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from core.logging_config import get_logger
from core.music_selector import get_music_selector
from core.font_selector import get_font_selector

logger = get_logger("smart_recommender")


@dataclass
class RecommendedConfig:
    """推荐配置"""
    style: str = "励志"
    style_reason: str = ""

    # 字体推荐
    font_family: str = "思源黑体"
    font_size: int = 42
    font_color: str = "white"
    font_reason: str = ""

    # 转场推荐
    transition_type: str = "xfade"
    avg_transition_duration: float = 0.18
    transition_reason: str = ""

    # 音乐推荐
    music_tags: List[str] = field(default_factory=list)
    music_reason: str = ""

    # 素材关键词推荐
    visual_keywords: List[str] = field(default_factory=list)
    visual_reason: str = ""

    # 整体推荐理由
    overall_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "style": self.style,
            "style_reason": self.style_reason,
            "font": {
                "family": self.font_family,
                "size": self.font_size,
                "color": self.font_color,
                "reason": self.font_reason,
            },
            "transition": {
                "type": self.transition_type,
                "avg_duration": self.avg_transition_duration,
                "reason": self.transition_reason,
            },
            "music_tags": self.music_tags,
            "music_reason": self.music_reason,
            "visual_keywords": self.visual_keywords,
            "visual_reason": self.visual_reason,
            "overall_reason": self.overall_reason,
        }


# 主题关键词 → 风格映射
THEME_STYLE_MAP = {
    # 热血类
    "热血": ["热血", "拼搏", "奋斗", "战斗", "激情", "梦想", "冲刺", "挑战", "突破", "超越"],
    # 励志类
    "励志": ["人生", "旅程", "成长", "坚持", "努力", "奋斗", "成功", "未来", "希望", "勇气"],
    # 治愈类
    "治愈": ["温柔", "宁静", "安静", "舒适", "放松", "治愈", "暖心", "美好", "阳光", "微笑"],
    # 文艺类
    "文艺": ["诗意", "意境", "文艺", "艺术", "美学", "浪漫", "唯美", "优雅", "古典", "东方"],
    # 欢快类
    "欢快": ["快乐", "欢快", "节日", "美食", "旅行", "派对", "庆祝", "欢乐", "开心", "笑容"],
}

# 音乐特征 → 风格适配
MUSIC_STYLE_MAP = {
    "high_energy": {  # BPM > 120, 高能量
        "style": "热血",
        "transition_duration": 0.12,
        "font_size": 52,
        "music_tags": ["Dynamic", "Excited", "Electronic"],
    },
    "medium_energy": {  # BPM 80-120, 中等能量
        "style": "励志",
        "transition_duration": 0.18,
        "font_size": 42,
        "music_tags": ["Inspirational", "Dynamic", "Pop"],
    },
    "low_energy": {  # BPM < 80, 低能量
        "style": "治愈",
        "transition_duration": 0.35,
        "font_size": 36,
        "music_tags": ["Calm", "Healing", "Classical"],
    },
}

# 场景 → 视觉关键词
SCENE_VISUAL_MAP = {
    "城市": ["城市夜景", "都市建筑", "街道", "霓虹灯", "车流"],
    "自然": ["风景", "自然", "山水", "森林", "海洋", "日落"],
    "人物": ["人群", "人物", "笑脸", "团队", "运动"],
    "抽象": ["抽象", "光影", "渐变", "粒子", "几何"],
}


class SmartRecommender:
    """智能推荐引擎"""

    def __init__(self):
        """初始化"""
        self.music_selector = get_music_selector()
        self.font_selector = get_font_selector()
        self.feedback_history: List[Dict] = []  # 用户反馈历史

    def analyze_theme(self, theme: str) -> Tuple[str, str]:
        """分析主题关键词，推荐风格

        Args:
            theme: 视频主题

        Returns:
            (推荐风格, 推荐理由)
        """
        theme_lower = theme.lower()

        # 关键词匹配
        for style, keywords in THEME_STYLE_MAP.items():
            for kw in keywords:
                if kw in theme_lower:
                    return style, f"主题包含关键词 '{kw}'，推荐 {style} 风格"

        # 默认：根据长度判断
        if len(theme) <= 4:
            return "热血", "短主题适合热血风格"
        elif len(theme) <= 8:
            return "励志", "中等长度主题适合励志风格"
        else:
            return "文艺", "长主题适合文艺风格"

    def analyze_music_features(
        self,
        bpm: float = None,
        energy_avg: float = None,
        tension_peaks: List[float] = None
    ) -> Tuple[str, float, List[str]]:
        """分析音乐特征，推荐配置

        Args:
            bpm: BPM 值
            energy_avg: 平均能量值
            tension_peaks: 张力峰值列表

        Returns:
            (推荐风格, 转场时长, 音乐标签)
        """
        # 确定能量等级
        energy_level = "medium_energy"

        if bpm:
            if bpm > 120:
                energy_level = "high_energy"
            elif bpm < 80:
                energy_level = "low_energy"

        if energy_avg:
            if energy_avg > 0.7:
                energy_level = "high_energy"
            elif energy_avg < 0.3:
                energy_level = "low_energy"

        config = MUSIC_STYLE_MAP[energy_level]
        return config["style"], config["transition_duration"], config["music_tags"]

    def recommend_config(
        self,
        theme: str,
        music_analysis: Dict[str, Any] = None,
        user_history: List[Dict] = None
    ) -> RecommendedConfig:
        """推荐完整配置

        Args:
            theme: 视频主题
            music_analysis: 音乐分析结果（可选）
            user_history: 用户历史偏好（可选）

        Returns:
            RecommendedConfig 推荐配置
        """
        config = RecommendedConfig()

        # 1. 分析主题 → 风格
        style, style_reason = self.analyze_theme(theme)
        config.style = style
        config.style_reason = style_reason

        # 2. 分析音乐 → 转场 + 音乐标签
        if music_analysis:
            bpm = music_analysis.get("bpm")
            energy_avg = music_analysis.get("energy_avg", music_analysis.get("energy_curve", {}).get("avg"))
            tension_peaks = music_analysis.get("tension_peaks", [])

            music_style, transition_dur, music_tags = self.analyze_music_features(
                bpm, energy_avg, tension_peaks
            )

            # 如果音乐风格与主题风格冲突，取折中
            if music_style != style:
                # 简单策略：能量主导
                if music_analysis.get("energy_avg", 0) > 0.5:
                    style = music_style
                    config.style = style
                    config.style_reason = f"音乐能量较高，调整为 {style} 风格"

            config.avg_transition_duration = transition_dur
            config.music_tags = music_tags
            config.music_reason = f"BPM={bpm}, 能量={energy_avg:.2f}，推荐 {music_style} 风格配置"

        # 3. 风格 → 字体推荐
        font_recommend = self.font_selector.recommend(style)
        if font_recommend:
            best_font = font_recommend[0]
            config.font_family = best_font.get("family", "思源黑体")
            config.font_size = best_font.get("default_size", 42)
            config.font_reason = f"{style} 风格推荐 {config.font_family} 字体"

        # 4. 风格 → 转场类型
        if style in ["热血", "欢快"]:
            config.transition_type = "xfade"
        elif style in ["治愈", "文艺"]:
            config.transition_type = "fade"
        else:
            config.transition_type = "xfade"
        config.transition_reason = f"{style} 风格推荐 {config.transition_type} 转场"

        # 5. 主题 → 视觉关键词
        config.visual_keywords = self._extract_visual_keywords(theme, style)
        config.visual_reason = f"根据主题 '{theme}' 提取视觉关键词"

        # 6. 整体推荐理由
        config.overall_reason = (
            f"主题 '{theme}' 推荐 {style} 风格，"
            f"使用 {config.font_family} 字体，"
            f"转场时长 {config.avg_transition_duration}s，"
            f"匹配音乐特征 {config.music_tags}"
        )

        logger.info(f"推荐配置: style={style}, font={config.font_family}")
        return config

    def _extract_visual_keywords(self, theme: str, style: str) -> List[str]:
        """提取视觉关键词"""
        keywords = []

        # 场景匹配
        for scene, scene_keywords in SCENE_VISUAL_MAP.items():
            if scene in theme.lower():
                keywords.extend(scene_keywords[:3])

        # 风格补充
        if style == "热血":
            keywords.extend(["运动", "人群", "速度"])
        elif style == "治愈":
            keywords.extend(["自然", "风景", "阳光"])
        elif style == "文艺":
            keywords.extend(["意境", "光影", "唯美"])

        # 去重，最多 10 个
        unique_keywords = list(set(keywords))[:10]
        return unique_keywords

    def learn_from_feedback(
        self,
        session_id: str,
        config: Dict[str, Any],
        rating: int,  # 1-5
        comments: str = None
    ):
        """从用户反馈学习

        Args:
            session_id: Session ID
            config: 用户使用的配置
            rating: 用户评分 (1-5)
            comments: 用户评论
        """
        feedback = {
            "session_id": session_id,
            "config": config,
            "rating": rating,
            "comments": comments,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self.feedback_history.append(feedback)

        # 如果评分 >= 4，保存为 Skill
        if rating >= 4:
            from skills.serializer import save_workflow_as_skill
            skill_name = f"auto_recommended_{session_id[:8]}"
            save_workflow_as_skill(session_id, skill_name, f"用户高分推荐配置 (rating={rating})")

        logger.info(f"记录反馈: session={session_id}, rating={rating}")

    def get_popular_configs(self, min_rating: int = 4) -> List[Dict]:
        """获取热门配置

        Args:
            min_rating: 最低评分阈值

        Returns:
            热门配置列表
        """
        popular = []
        for fb in self.feedback_history:
            if fb["rating"] >= min_rating:
                popular.append({
                    "config": fb["config"],
                    "rating": fb["rating"],
                    "comments": fb["comments"],
                })

        # 按评分排序
        popular.sort(key=lambda x: x["rating"], reverse=True)
        return popular[:10]


# 全局实例
_recommender = None


def get_smart_recommender() -> SmartRecommender:
    """获取推荐引擎实例"""
    global _recommender
    if _recommender is None:
        _recommender = SmartRecommender()
    return _recommender


def recommend_config(theme: str, music_analysis: Dict = None) -> RecommendedConfig:
    """推荐配置（便捷函数）"""
    return get_smart_recommender().recommend_config(theme, music_analysis)