#!/usr/bin/env python3
"""
音乐选择器 — 语义标签匹配推荐

支持：
1. 按 mood/scene/genre 搜索
2. 按 BPM 范围筛选
3. 按 duration 筛选
"""

import json
import os
import random
from pathlib import Path
from typing import Dict, List, Optional, Any

from core.logging_config import get_logger
from config import ANALYSIS_SAMPLE_RATE

logger = get_logger("music_selector")


class MusicSelector:
    """音乐选择器"""

    def __init__(self, meta_path: str = None):
        """初始化音乐选择器

        Args:
            meta_path: meta.json 文件路径
        """
        if meta_path is None:
            meta_path = str(Path(__file__).parent.parent / "resource/bgms/meta.json")

        self.meta_path = meta_path
        self.tracks = self._load_meta()

    def _load_meta(self) -> List[Dict[str, Any]]:
        """加载音乐元数据"""
        if os.path.exists(self.meta_path):
            with open(self.meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("tracks", [])
        return []

    def search(
        self,
        mood: str = None,
        scene: str = None,
        genre: str = None,
        bpm_min: int = None,
        bpm_max: int = None,
        duration_min: float = None,
        duration_max: float = None
    ) -> List[Dict[str, Any]]:
        """搜索音乐

        Args:
            mood: 情绪标签 (Dynamic, Chill, Happy, Sorrow, Romantic, Calm, Excited, Healing, Inspirational)
            scene: 场景标签 (Vlog, Travel, Relaxing, Emotion, Transition, Outdoor, Cafe, Evening, Scenery, Food, Date, Club)
            genre: 曲风标签 (Pop, BGM, Electronic, R&B/Soul, Hip Hop/Rap, Rock, Jazz, Folk, Classical, Chinese Style)
            bpm_min: 最小 BPM
            bpm_max: 最大 BPM
            duration_min: 最小时长
            duration_max: 最大时长

        Returns:
            匹配的音乐列表
        """
        results = []

        for track in self.tracks:
            tags = track.get("tags", {})

            # mood 匹配
            if mood:
                track_moods = tags.get("mood", [])
                if mood not in track_moods:
                    continue

            # scene 匹配
            if scene:
                track_scenes = tags.get("scene", [])
                if scene not in track_scenes:
                    continue

            # genre 匹配
            if genre:
                track_genres = tags.get("genre", [])
                if genre not in track_genres:
                    continue

            # BPM 范围
            if bpm_min or bpm_max:
                track_bpm = track.get("bpm", 0)
                if bpm_min and track_bpm < bpm_min:
                    continue
                if bpm_max and track_bpm > bpm_max:
                    continue

            # duration 范围
            if duration_min or duration_max:
                track_duration = track.get("duration", 0)
                if duration_min and track_duration < duration_min:
                    continue
                if duration_max and track_duration > duration_max:
                    continue

            results.append(track)

        return results

    def recommend(
        self,
        style: str = None,
        analysis: Dict[str, Any] = None,
        count: int = 3
    ) -> List[Dict[str, Any]]:
        """根据风格/分析结果推荐音乐

        Args:
            style: 风格预设 (热血, 励志, 治愈, 文艺, 欢快)
            analysis: 音乐分析结果（可选）
            count: 推荐数量

        Returns:
            推荐的音乐列表
        """
        # 风格 → mood 映射
        style_mood_map = {
            "热血": ["Dynamic", "Excited"],
            "励志": ["Inspirational", "Dynamic"],
            "治愈": ["Calm", "Healing"],
            "文艺": ["Calm", "Inspirational"],
            "欢快": ["Happy", "Chill"],
        }

        # 风格 → BPM 范围映射
        style_bpm_map = {
            "热血": (120, 150),
            "励志": (100, 130),
            "治愈": (60, 90),
            "文艺": (70, 100),
            "欢快": (90, 120),
        }

        moods = style_mood_map.get(style, ["Dynamic"])
        bpm_range = style_bpm_map.get(style, (80, 120))

        # 搜索匹配的音乐
        all_matches = []
        for mood in moods:
            matches = self.search(
                mood=mood,
                bpm_min=bpm_range[0],
                bpm_max=bpm_range[1]
            )
            all_matches.extend(matches)

        # 去重
        unique_matches = []
        seen_ids = set()
        for track in all_matches:
            if track["id"] not in seen_ids:
                unique_matches.append(track)
                seen_ids.add(track["id"])

        # 如果不足，返回所有可用音乐
        if len(unique_matches) < count:
            unique_matches = self.tracks

        # 随机选择
        if len(unique_matches) > count:
            return random.sample(unique_matches, count)
        return unique_matches[:count]

    def get_track_path(self, track_id: str) -> Optional[str]:
        """获取音乐文件路径

        Args:
            track_id: 音乐 ID

        Returns:
            文件路径，不存在返回 None
        """
        for track in self.tracks:
            if track["id"] == track_id:
                file_name = track.get("file", "")
                base_dir = Path(self.meta_path).parent
                return str(base_dir / file_name)
        return None

    def get_track_by_id(self, track_id: str) -> Optional[Dict[str, Any]]:
        """获取音乐信息

        Args:
            track_id: 音乐 ID

        Returns:
            音乐信息字典
        """
        for track in self.tracks:
            if track["id"] == track_id:
                return track
        return None


# 全局选择器实例
_selector = None


def get_music_selector() -> MusicSelector:
    """获取音乐选择器实例"""
    global _selector
    if _selector is None:
        _selector = MusicSelector()
    return _selector


def recommend_music(style: str = None, analysis: Dict[str, Any] = None, count: int = 3) -> List[Dict[str, Any]]:
    """推荐音乐（便捷函数）

    Args:
        style: 风格预设
        analysis: 音乐分析结果
        count: 推荐数量

    Returns:
        推荐的音乐列表
    """
    return get_music_selector().recommend(style, analysis, count)


def search_music(mood: str = None, scene: str = None, genre: str = None,
                 bpm_min: int = None, bpm_max: int = None,
                 duration_min: float = None, duration_max: float = None) -> List[Dict[str, Any]]:
    """搜索音乐（便捷函数）

    Args:
        mood: 情绪标签
        scene: 场景标签
        genre: 曲风标签
        bpm_min: 最小 BPM
        bpm_max: 最大 BPM
        duration_min: 最小时长
        duration_max: 最大时长

    Returns:
        匹配的音乐列表
    """
    return get_music_selector().search(mood, scene, genre, bpm_min, bpm_max, duration_min, duration_max)