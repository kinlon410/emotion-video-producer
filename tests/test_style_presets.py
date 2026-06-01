#!/usr/bin/env python3
"""
测试风格预设模块 - 使用 unittest
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.style_presets import (
    get_style_preset,
    list_styles,
    apply_preset_to_analysis,
    STYLE_PRESETS,
)


class TestStylePresets(unittest.TestCase):
    """风格预设测试"""

    def test_get_style_preset_valid(self):
        """测试获取有效风格预设"""

        for style_name in ["热血", "励志", "治愈", "文艺", "欢快"]:
            preset = get_style_preset(style_name)

            self.assertIsNotNone(preset)
            self.assertIn("description", preset)
            self.assertIn("transitions", preset)
            self.assertIn("subtitle_style", preset)
            self.assertTrue(len(preset["transitions"]) > 0)

    def test_get_style_preset_invalid(self):
        """测试获取无效风格名称"""

        preset = get_style_preset("invalid_style")

        # 应返回默认风格（励志）
        self.assertIsNotNone(preset)
        self.assertEqual(preset, STYLE_PRESETS["励志"])

    def test_list_styles(self):
        """测试列出所有风格"""

        styles = list_styles()

        self.assertEqual(len(styles), 5)  # 5种风格
        for s in styles:
            self.assertIn("name", s)
            self.assertIn("description", s)

    def test_apply_preset_to_analysis(self):
        """测试应用预设到分析结果"""

        analysis = {
            "duration": 20,
            "emotion_curve": [
                {"time": 0, "value": 0.2},
                {"time": 5, "value": 0.5},
                {"time": 10, "value": 0.9},  # 高峰值
                {"time": 15, "value": 0.4},
            ],
            "tension_peaks": [10],
            "recommended_style": "励志",
        }

        # 应用高阈值风格（热血）
        result = apply_preset_to_analysis(analysis, "热血")

        self.assertIn("applied_style", result)
        self.assertEqual(result["applied_style"], "热血")
        self.assertIn("style_config", result)

    def test_preset_transitions_match_energy(self):
        """测试预设转场与能量匹配"""

        high_transitions = STYLE_PRESETS["热血"]["transitions"]
        self.assertTrue("pixelize" in high_transitions or "zoomin" in high_transitions)

        low_transitions = STYLE_PRESETS["治愈"]["transitions"]
        self.assertTrue("fade" in low_transitions or "dissolve" in low_transitions)

    def test_preset_duration_matches_style(self):
        """测试转场时长与风格匹配"""

        # 热血：快速转场
        self.assertLessEqual(STYLE_PRESETS["热血"]["transition_duration"], 0.15)

        # 治愈：慢速转场
        self.assertGreaterEqual(STYLE_PRESETS["治愈"]["transition_duration"], 0.30)


if __name__ == "__main__":
    unittest.main(verbosity=2)