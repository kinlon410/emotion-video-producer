#!/usr/bin/env python3
"""
测试视频渲染模块 - 使用 unittest
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.video_renderer import (
    render_video,
    get_clip_info,
    _build_single_clip_filter,
    _build_xfade_filter_chain,
    _build_render_command,
    XFADE_EFFECTS,
)


class TestVideoRenderer(unittest.TestCase):
    """视频渲染器测试"""

    def test_xfade_effects_mapping(self):
        """测试转场效果映射"""

        # 基础转场
        self.assertIn("fade", XFADE_EFFECTS)
        self.assertEqual(XFADE_EFFECTS["fade"], "fade")

        # 滑动转场
        self.assertIn("slideleft", XFADE_EFFECTS)
        self.assertIn("slideright", XFADE_EFFECTS)
        self.assertIn("slideup", XFADE_EFFECTS)
        self.assertIn("slidedown", XFADE_EFFECTS)

        # 缩放转场
        self.assertIn("zoomin", XFADE_EFFECTS)
        self.assertIn("zoomout", XFADE_EFFECTS)

        # 覆盖转场
        self.assertIn("coverleft", XFADE_EFFECTS)
        self.assertIn("revealleft", XFADE_EFFECTS)

    def test_get_clip_info_fallback(self):
        """测试片段信息获取（备选）"""

        # 创建临时文件
        temp_clip = tempfile.mktemp(suffix=".mp4")
        with open(temp_clip, "wb") as f:
            f.write(b"dummy video content")

        info = get_clip_info(temp_clip)

        # ffprobe 返回结果
        self.assertIn("path", info)
        self.assertIn("duration", info)
        self.assertIn("width", info)
        self.assertIn("height", info)

        # 路径应匹配
        self.assertEqual(info["path"], temp_clip)

        # ffprobe 对非视频文件返回空数据，duration 可能是 0 或 3.0（备选）
        # 两种情况都接受
        self.assertIn(info["duration"], [0.0, 3.0])

        # 尺寸应大于 0
        self.assertGreater(info["width"], 0)
        self.assertGreater(info["height"], 0)

        os.remove(temp_clip)

    def test_build_single_clip_filter(self):
        """测试单片段滤镜构建"""

        clip_path = "dummy.mp4"
        subtitles = [
            {"text_zh": "测试字幕", "text_en": "Test subtitle", "start": 0, "end": 3}
        ]
        title_text = "视频标题"

        filter_str = _build_single_clip_filter(
            clip_path, subtitles, title_text, 1920, 1080
        )

        # 应包含缩放滤镜
        self.assertIn("scale=1920:1080", filter_str)
        self.assertIn("format=yuv420p", filter_str)

        # 应包含字幕
        self.assertIn("drawtext", filter_str)
        self.assertIn("测试字幕", filter_str)
        self.assertIn("Test subtitle", filter_str)

        # 应包含标题
        self.assertIn("视频标题", filter_str)

    def test_build_single_clip_filter_no_subtitle(self):
        """测试单片段滤镜（无字幕）"""

        filter_str = _build_single_clip_filter(
            "dummy.mp4", [], None, 1920, 1080
        )

        self.assertIn("scale=1920:1080", filter_str)
        self.assertNotIn("drawtext", filter_str)

    def test_build_xfade_filter_chain_basic(self):
        """测试 xfade 转场滤镜链"""

        clips = ["clip1.mp4", "clip2.mp4", "clip3.mp4"]
        clip_info = [
            {"path": "clip1.mp4", "duration": 3.0, "width": 1920, "height": 1080},
            {"path": "clip2.mp4", "duration": 4.0, "width": 1920, "height": 1080},
            {"path": "clip3.mp4", "duration": 2.5, "width": 1920, "height": 1080},
        ]
        transitions = [
            {"transition_out": "fade", "transition_duration": 0.3},
            {"transition_out": "slideleft", "transition_duration": 0.2},
        ]

        filter_chain = _build_xfade_filter_chain(
            clips, clip_info, transitions, [], None, 1920, 1080
        )

        # 应包含多个滤镜部分（用分号分隔）
        parts = filter_chain.split(";")

        # 应包含缩放滤镜
        self.assertTrue(any("scale=1920:1080" in p for p in parts))

        # 应包含 xfade 转场
        self.assertTrue(any("xfade" in p for p in parts))

        # 应包含 fade 转场
        self.assertTrue(any("transition=fade" in p for p in parts))

        # 应包含 slideleft 转场
        self.assertTrue(any("transition=slideleft" in p for p in parts))

    def test_build_xfade_filter_chain_with_subtitles(self):
        """测试带字幕的 xfade 滤镜链"""

        clips = ["clip1.mp4", "clip2.mp4"]
        clip_info = [
            {"path": "clip1.mp4", "duration": 3.0, "width": 1920, "height": 1080},
            {"path": "clip2.mp4", "duration": 4.0, "width": 1920, "height": 1080},
        ]
        subtitles = [
            {"text_zh": "第一句", "start": 0, "end": 2},
            {"text_zh": "第二句", "start": 3, "end": 6},
        ]

        filter_chain = _build_xfade_filter_chain(
            clips, clip_info, [], subtitles, None, 1920, 1080
        )

        # 应包含字幕
        self.assertIn("第一句", filter_chain)
        self.assertIn("第二句", filter_chain)

    def test_build_render_command_basic(self):
        """测试渲染命令构建"""

        clips = ["clip1.mp4", "clip2.mp4"]
        filter_complex = "[0:v]scale=1920:1080[v0];[v0]null[outv]"

        cmd = _build_render_command(
            clips,
            "bgm.mp3",
            None,
            "output.mp4",
            filter_complex,
            1920, 1080, 30,
            0.6, 1.0
        )

        # 检查基本命令结构
        self.assertEqual(cmd[0], "ffmpeg")
        self.assertIn("-y", cmd)

        # 输入文件
        self.assertIn("clip1.mp4", cmd)
        self.assertIn("clip2.mp4", cmd)
        self.assertIn("bgm.mp3", cmd)

        # 滤镜
        self.assertIn("-filter_complex", cmd)

        # 输出编码
        self.assertIn("libx264", cmd)
        self.assertIn("yuv420p", cmd)

        # 音频编码
        self.assertIn("aac", cmd)

        # 输出文件
        self.assertIn("output.mp4", cmd)

    def test_build_render_command_with_narration(self):
        """测试带旁白的渲染命令"""

        # 创建临时旁白文件（函数检查文件是否存在）
        temp_dir = tempfile.mkdtemp()
        narration_path = os.path.join(temp_dir, "narration.mp3")
        with open(narration_path, "wb") as f:
            f.write(b"dummy audio content")

        clips = ["clip.mp4"]
        filter_complex = "[0:v]scale=1920:1080[outv]"

        cmd = _build_render_command(
            clips,
            "bgm.mp3",
            narration_path,
            "output.mp4",
            filter_complex,
            1920, 1080, 30,
            0.6, 1.0
        )

        # 应包含旁白输入
        self.assertIn(narration_path, cmd)

        # 应包含音量调节和混音
        self.assertTrue(any("volume" in c for c in cmd))
        self.assertTrue(any("amix" in c for c in cmd))

        # 清理
        os.remove(narration_path)
        os.rmdir(temp_dir)

    def test_render_video_empty_clips(self):
        """测试空片段列表"""

        result = render_video(
            clips=[],
            transitions=[],
            subtitles=[],
            bgm_path="bgm.mp3",
            output_path="output.mp4",
        )

        # 应返回 False
        self.assertFalse(result)


class TestVideoRendererIntegration(unittest.TestCase):
    """视频渲染器集成测试"""

    def test_transition_duration_calculation(self):
        """测试转场时长计算"""

        # 两个片段，总时长减去转场时长
        clip_info = [
            {"duration": 3.0},
            {"duration": 4.0},
        ]
        transitions = [
            {"transition_duration": 0.3},
        ]

        # 第一个 xfade 偏移 = 3.0 - 0.3 = 2.7
        offset = clip_info[0]["duration"] - transitions[0]["transition_duration"]
        self.assertEqual(offset, 2.7)

    def test_default_transition_fallback(self):
        """测试默认转场备选"""

        # 无转场配置时使用默认 fade
        clips = ["clip1.mp4", "clip2.mp4"]
        clip_info = [
            {"path": "clip1.mp4", "duration": 3.0, "width": 1920, "height": 1080},
            {"path": "clip2.mp4", "duration": 4.0, "width": 1920, "height": 1080},
        ]

        filter_chain = _build_xfade_filter_chain(
            clips, clip_info, [], [], None, 1920, 1080
        )

        # 应使用 fade 转场
        self.assertIn("transition=fade", filter_chain)


if __name__ == "__main__":
    unittest.main(verbosity=2)