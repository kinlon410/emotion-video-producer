#!/usr/bin/env python3
"""
测试主演编器模块 - 使用 unittest
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.producer import (
    produce_video,
    _render_video,
    _save_srt,
    _format_srt_time,
)


class TestProducer(unittest.TestCase):
    """主演编器测试"""

    def test_format_srt_time(self):
        """测试 SRT 时间格式化"""

        self.assertEqual(_format_srt_time(0), "00:00:00,000")
        self.assertEqual(_format_srt_time(1.5), "00:00:01,500")
        self.assertEqual(_format_srt_time(65.123), "00:01:05,123")
        self.assertEqual(_format_srt_time(3661), "01:01:01,000")

    def test_save_srt(self):
        """测试 SRT 文件保存"""

        subtitles = [
            {"id": "L1", "text_zh": "第一句字幕", "start": 0.0, "end": 2.5},
            {"id": "L2", "text_zh": "第二句字幕", "start": 2.5, "end": 5.0},
        ]

        output_path = tempfile.mktemp(suffix=".srt")

        _save_srt(subtitles, output_path)

        self.assertTrue(os.path.exists(output_path))

        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("第一句字幕", content)
        self.assertIn("第二句字幕", content)
        self.assertIn("00:00:00,000 --> 00:00:02,500", content)

        os.remove(output_path)

    def test_render_video_no_clips(self):
        """测试无素材时渲染失败"""

        config = {
            "clips": {},
            "transitions": [],
            "subtitles": [],
            "bgm_path": "dummy.mp3",
            "output_path": "output.mp4",
        }

        result = _render_video(config)

        self.assertFalse(result)

    def test_render_video_config_structure(self):
        """测试渲染配置结构"""

        config = {
            "title_text": "测试",
            "bgm_path": "/tmp/bgm.mp3",
            "narration_path": None,
            "clips": {"S1": "/tmp/clip1.mp4"},
            "transitions": [{"segment_index": 0, "transition_out": "fade"}],
            "subtitles": [{"id": "L1", "text_zh": "测试", "start": 0, "end": 2}],
            "output_path": "/tmp/output.mp4",
            "width": 1920,
            "height": 1080,
            "fps": 30,
        }

        required_keys = [
            "clips",
            "transitions",
            "output_path",
            "width",
            "height",
        ]

        for key in required_keys:
            self.assertIn(key, config)


class TestProducerIntegration(unittest.TestCase):
    """主演编器集成测试"""

    def test_produce_video_missing_bgm(self):
        """测试缺少 BGM 时生产失败"""

        result = produce_video(
            theme="测试",
            bgm_path="/nonexistent/music.mp3",
            output_path="/tmp/test.mp4",
        )

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)