#!/usr/bin/env python3
"""
测试模板管理模块
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.schemas import SessionState
from core.template_manager import TemplateManager


class FakeSessionStore:
    """用于验证模板写入 session 的假存储"""

    def __init__(self):
        self.updated_session_id = None
        self.updates = None

    def update_session(self, session_id, updates):
        self.updated_session_id = session_id
        self.updates = updates
        return SessionState(
            session_id=session_id,
            theme="测试主题",
            bgm_path="/tmp/test.mp3",
            style=updates.get("style"),
            visual_keywords=updates.get("visual_keywords"),
            transition_params=updates.get("transition_params"),
            subtitle_style=updates.get("subtitle_style"),
            music_tags=updates.get("music_tags"),
            current_step=0,
            completed_steps=[],
            work_dir="/tmp/workdir",
            created_at="2026-06-02T00:00:00",
            updated_at="2026-06-02T00:00:00",
        )


class TestTemplateManager(unittest.TestCase):
    """模板管理器测试"""

    @patch("agent.session_store.get_session_store")
    def test_apply_template_persists_full_template_config(self, mock_get_session_store):
        """应用模板时应将模板关键配置写入 session"""

        fake_store = FakeSessionStore()
        mock_get_session_store.return_value = fake_store

        manager = TemplateManager()

        result = manager.apply_template("春节", "session-001")

        self.assertEqual(fake_store.updated_session_id, "session-001")
        self.assertEqual(fake_store.updates["style"], result["style"])
        self.assertEqual(fake_store.updates["visual_keywords"], result["visual_keywords"])
        self.assertEqual(fake_store.updates["transition_params"], result["transition_params"])
        self.assertEqual(fake_store.updates["subtitle_style"], result["subtitle_style"])
        self.assertEqual(fake_store.updates["music_tags"], result["music_tags"])

    @patch("agent.session_store.get_session_store")
    def test_apply_template_customizations_override_persisted_fields(self, mock_get_session_store):
        """自定义覆盖应同时影响返回值和写入 session 的内容"""

        fake_store = FakeSessionStore()
        mock_get_session_store.return_value = fake_store

        manager = TemplateManager()

        customizations = {
            "style": "热血",
            "visual_keywords": ["自定义", "烟花"],
            "transition_params": {"avg_duration": 0.25, "transition_type": "fade"},
            "subtitle_style": {"fontsize": 60, "fontcolor": "gold"},
            "music_tags": ["Custom", "Festival"],
        }

        result = manager.apply_template("春节", "session-002", customizations)

        self.assertEqual(result["style"], "热血")
        self.assertEqual(result["visual_keywords"], ["自定义", "烟花"])
        self.assertEqual(result["transition_params"]["avg_duration"], 0.25)
        self.assertEqual(result["subtitle_style"]["fontsize"], 60)
        self.assertEqual(result["music_tags"], ["Custom", "Festival"])
        self.assertEqual(fake_store.updates, result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
