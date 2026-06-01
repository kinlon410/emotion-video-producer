#!/usr/bin/env python3
"""
Skill 序列化器 — 保存生产流程为可复用模板

支持：
1. serialize_workflow — 导出 Session workflow 为 Skill JSON
2. load_skill — 加载 Skill 并应用到新 Session
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from agent.schemas import SkillDefinition, SessionState
from agent.session_store import get_session_store, SessionStore
from core.logging_config import get_logger
from core.exceptions import SkillNotFoundError, SkillValidationError

logger = get_logger("skill_serializer")


SKILLS_DIR = Path(__file__).parent.parent / "skills/library"


class SkillSerializer:
    """Skill 序列化器"""

    def __init__(self, skills_dir: str = None):
        """初始化

        Args:
            skills_dir: Skills 存储目录
        """
        self.skills_dir = Path(skills_dir) if skills_dir else SKILLS_DIR
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def serialize_workflow(
        self,
        session_id: str,
        name: str,
        description: str = None
    ) -> SkillDefinition:
        """将 Session workflow 序列化为 Skill

        Args:
            session_id: Session ID
            name: Skill 名称
            description: Skill 描述

        Returns:
            SkillDefinition 对象
        """
        store = get_session_store()
        state = store.get_session(session_id)

        # 提取关键配置
        skill = SkillDefinition(
            name=name,
            description=description or f"从 {state.theme} 生成的风格模板",
            style=state.style,
            visual_keywords=self._extract_visual_keywords(state),
            transition_params=self._extract_transition_params(state),
            subtitle_style=self._extract_subtitle_style(state),
            music_tags=self._extract_music_tags(state),
            created_at=datetime.utcnow().isoformat(),
        )

        # 保存到文件
        self._save_skill(skill)

        logger.info(f"Skill 序列化完成: {name}")
        return skill

    def _extract_visual_keywords(self, state: SessionState) -> List[str]:
        """提取视觉关键词"""
        keywords = []
        if state.visuals:
            for v in state.visuals:
                keyword = v.get("keyword", "")
                if keyword and keyword not in keywords:
                    keywords.append(keyword)
        return keywords[:10]  # 最多 10 个

    def _extract_transition_params(self, state: SessionState) -> Dict[str, Any]:
        """提取转场参数"""
        if state.transitions:
            # 计算平均转场时长
            durations = [t.get("duration", 0) for t in state.transitions]
            avg_duration = sum(durations) / len(durations) if durations else 0.2

            return {
                "avg_duration": round(avg_duration, 2),
                "transition_type": state.transitions[0].get("type", "xfade"),
            }
        return {}

    def _extract_subtitle_style(self, state: SessionState) -> Dict[str, Any]:
        """提取字幕样式"""
        # 根据 style 推断字幕样式
        style_map = {
            "热血": {"fontsize": 52, "fontcolor": "white", "borderw": 3, "bold": True},
            "励志": {"fontsize": 42, "fontcolor": "white", "borderw": 2, "bold": False},
            "治愈": {"fontsize": 36, "fontcolor": "white@0.85", "borderw": 0, "bold": False},
            "文艺": {"fontsize": 42, "fontcolor": "white@0.9", "borderw": 1, "bold": False},
            "欢快": {"fontsize": 48, "fontcolor": "cyan", "borderw": 2, "bold": False},
        }
        return style_map.get(state.style or "励志", style_map["励志"])

    def _extract_music_tags(self, state: SessionState) -> List[str]:
        """提取音乐标签"""
        # 根据 style 推断音乐标签
        tag_map = {
            "热血": ["Dynamic", "Excited", "Electronic"],
            "励志": ["Inspirational", "Dynamic", "Pop"],
            "治愈": ["Calm", "Healing", "Classical"],
            "文艺": ["Calm", "Inspirational", "Chinese Style"],
            "欢快": ["Happy", "Chill", "Pop"],
        }
        return tag_map.get(state.style or "励志", tag_map["励志"])

    def _save_skill(self, skill: SkillDefinition):
        """保存 Skill 到文件"""
        file_name = f"{skill.name.replace(' ', '_')}.skill.json"
        file_path = self.skills_dir / file_name

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(skill.dict(), f, ensure_ascii=False, indent=2)

        logger.info(f"Skill 保存: {file_path}")

    def load_skill(self, name: str) -> SkillDefinition:
        """加载 Skill

        Args:
            name: Skill 名称

        Returns:
            SkillDefinition 对象

        Raises:
            SkillNotFoundError: Skill 不存在
        """
        file_name = f"{name.replace(' ', '_')}.skill.json"
        file_path = self.skills_dir / file_name

        if not file_path.exists():
            raise SkillNotFoundError(f"Skill 不存在: {name}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return SkillDefinition(**data)

    def list_skills(self) -> List[Dict[str, Any]]:
        """列出所有 Skills

        Returns:
            Skills 列表
        """
        skills = []
        for file_path in self.skills_dir.glob("*.skill.json"):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                skills.append({
                    "name": data.get("name", ""),
                    "description": data.get("description", ""),
                    "style": data.get("style", ""),
                    "created_at": data.get("created_at", ""),
                })
        return skills

    def apply_skill_to_session(
        self,
        skill_name: str,
        session_id: str
    ) -> SessionState:
        """将 Skill 应用到 Session

        Args:
            skill_name: Skill 名称
            session_id: Session ID

        Returns:
            更新后的 SessionState
        """
        skill = self.load_skill(skill_name)
        store = get_session_store()

        # 更新 Session
        updates = {
            "style": skill.style,
        }

        state = store.update_session(session_id, updates)

        logger.info(f"Skill 应用: {skill_name} → session={session_id}")
        return state


# 全局序列化器实例
_serializer = None


def get_skill_serializer() -> SkillSerializer:
    """获取 Skill 序列化器实例"""
    global _serializer
    if _serializer is None:
        _serializer = SkillSerializer()
    return _serializer


def save_workflow_as_skill(session_id: str, name: str, description: str = None) -> SkillDefinition:
    """保存 workflow 为 Skill（便捷函数）"""
    return get_skill_serializer().serialize_workflow(session_id, name, description)


def load_skill(name: str) -> SkillDefinition:
    """加载 Skill（便捷函数）"""
    return get_skill_serializer().load_skill(name)


def list_skills() -> List[Dict[str, Any]]:
    """列出所有 Skills（便捷函数）"""
    return get_skill_serializer().list_skills()