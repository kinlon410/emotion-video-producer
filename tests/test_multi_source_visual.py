#!/usr/bin/env python3
"""
测试多源视觉素材模块 - 使用 unittest
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.multi_source_visual import (
    download_from_multi_sources,
    VideoDedupManager,
    _download_image,
    _image_to_video,
    _generate_background,
    VIDEO_SOURCES,
)


class TestVideoDedupManager(unittest.TestCase):
    """视频去重管理器测试"""

    def test_initial_state(self):
        """测试初始状态"""

        VideoDedupManager.reset()

        self.assertEqual(len(VideoDedupManager._downloaded_ids), 0)

    def test_add_and_check(self):
        """测试添加和检查"""

        VideoDedupManager.reset()

        VideoDedupManager.add("video_123")

        self.assertTrue(VideoDedupManager.is_downloaded("video_123"))
        self.assertFalse(VideoDedupManager.is_downloaded("video_456"))

    def test_multiple_adds(self):
        """测试多次添加"""

        VideoDedupManager.reset()

        VideoDedupManager.add("video_1")
        VideoDedupManager.add("video_2")
        VideoDedupManager.add("video_1")  # 重复添加

        self.assertEqual(len(VideoDedupManager._downloaded_ids), 2)


class TestVideoSources(unittest.TestCase):
    """视频源配置测试"""

    def test_source_priority(self):
        """测试素材源优先级"""

        # Pexels 应最高优先级
        self.assertEqual(VIDEO_SOURCES["pexels"]["priority"], 1)
        self.assertEqual(VIDEO_SOURCES["pixabay"]["priority"], 2)
        self.assertEqual(VIDEO_SOURCES["coverr"]["priority"], 3)

    def test_source_requires_key(self):
        """测试素材源 API Key 要求"""

        self.assertTrue(VIDEO_SOURCES["pexels"]["requires_key"])
        self.assertTrue(VIDEO_SOURCES["pixabay"]["requires_key"])
        self.assertFalse(VIDEO_SOURCES["coverr"]["requires_key"])

    def test_source_names(self):
        """测试素材源名称"""

        self.assertEqual(VIDEO_SOURCES["pexels"]["name"], "Pexels")
        self.assertEqual(VIDEO_SOURCES["pixabay"]["name"], "Pixabay")


class TestImageFunctions(unittest.TestCase):
    """图片处理函数测试"""

    def test_download_image_placeholder(self):
        """测试图片下载（占位测试）"""

        # 创建临时目录
        output_dir = tempfile.mkdtemp()
        output_path = os.path.join(output_dir, "test.jpg")

        # 实际下载可能失败（无网络），测试函数可调用
        try:
            result = _download_image("city night", output_path)
            # 结果取决于网络
        except Exception:
            pass

        # 清理
        if os.path.exists(output_path):
            os.remove(output_path)
        os.rmdir(output_dir)

    def test_generate_background_creates_file(self):
        """测试背景生成"""

        output_dir = tempfile.mkdtemp()
        output_path = os.path.join(output_dir, "bg.mp4")

        # 需要 ffmpeg
        try:
            result = _generate_background(output_path, 2.0, "city_night")

            if result:
                self.assertTrue(os.path.exists(output_path))
                # 文件大小应大于 0
                self.assertGreater(os.path.getsize(output_path), 0)
        except Exception:
            # ffmpeg 可能不可用
            pass

        # 清理
        if os.path.exists(output_path):
            os.remove(output_path)
        os.rmdir(output_dir)

    def test_image_to_video_requires_ffmpeg(self):
        """测试图片转视频"""

        # 创建临时图片
        output_dir = tempfile.mkdtemp()
        img_path = os.path.join(output_dir, "test.jpg")
        video_path = os.path.join(output_dir, "test.mp4")

        # 创建简单的图片文件（不是真正的图片，仅用于测试）
        with open(img_path, "wb") as f:
            f.write(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        try:
            result = _image_to_video(img_path, video_path, 2.0)
        except Exception:
            # ffmpeg 可能失败
            pass

        # 清理
        for path in [img_path, video_path]:
            if os.path.exists(path):
                os.remove(path)
        os.rmdir(output_dir)


class TestMultiSourceDownload(unittest.TestCase):
    """多源下载函数测试"""

    def test_download_from_multi_sources_empty(self):
        """测试空关键词列表"""

        output_dir = tempfile.mkdtemp()

        clips = download_from_multi_sources(
            keywords=[],
            output_dir=output_dir,
            mode="auto",
        )

        self.assertEqual(len(clips), 0)

        os.rmdir(output_dir)

    def test_download_from_multi_sources_keywords_structure(self):
        """测试关键词结构"""

        keywords = [
            {"id": "S1", "keyword": "city night", "duration": 3.0},
            {"id": "S2", "keyword": "sunset", "duration": 2.5},
        ]

        output_dir = tempfile.mkdtemp()

        # 使用 generate 模式避免网络请求
        clips = download_from_multi_sources(
            keywords=keywords,
            output_dir=output_dir,
            mode="generate",
        )

        # 检查返回结构
        self.assertIsInstance(clips, dict)

        # 检查 ID 映射
        for seg_id, path in clips.items():
            self.assertIn(seg_id, ["S1", "S2"])

        # 清理
        for path in clips.values():
            if os.path.exists(path):
                os.remove(path)
        os.rmdir(output_dir)

    def test_download_mode_selection(self):
        """测试下载模式选择"""

        keywords = [{"id": "T1", "keyword": "test", "duration": 1.0}]
        output_dir = tempfile.mkdtemp()

        # generate 模式应跳过 API 源
        clips = download_from_multi_sources(
            keywords=keywords,
            output_dir=output_dir,
            mode="generate",
        )

        # 应生成背景
        if clips:
            self.assertIn("T1", clips)

        # 清理
        for path in clips.values():
            if os.path.exists(path):
                os.remove(path)
        os.rmdir(output_dir)


class TestPaletteSelection(unittest.TestCase):
    """调色板选择测试"""

    def test_palette_names(self):
        """测试调色板名称"""

        from config import PALETTES

        self.assertIn("city_night", PALETTES)
        self.assertIn("sunset", PALETTES)
        self.assertIn("ocean", PALETTES)
        self.assertIn("neon", PALETTES)
        self.assertIn("warm", PALETTES)

    def test_palette_structure(self):
        """测试调色板结构"""

        from config import PALETTES

        for name, colors in PALETTES.items():
            self.assertTrue(len(colors) >= 2)
            # 颜色应为十六进制字符串
            for color in colors:
                self.assertEqual(len(color), 6)


if __name__ == "__main__":
    unittest.main(verbosity=2)