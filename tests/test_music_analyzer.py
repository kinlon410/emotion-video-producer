#!/usr/bin/env python3
"""
测试音乐情感分析模块 - 使用 unittest
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

from core.music_analyzer import (
    analyze_music,
    _detect_structure,
    _smooth_emotion_curve,
    _detect_tension_peaks,
    _recommend_style,
    _fallback_analysis,
)


class TestMusicAnalyzer(unittest.TestCase):
    """音乐分析器测试"""

    def test_fallback_analysis(self):
        """测试备用分析（无 librosa）"""

        # 创建临时音频文件
        temp_audio = tempfile.mktemp(suffix=".wav")

        # 创建简单的 WAV 文件头
        with open(temp_audio, "wb") as f:
            f.write(b"RIFF")
            f.write(b"\x24\x00\x00\x00")
            f.write(b"WAVE")
            f.write(b"fmt ")
            f.write(b"\x10\x00\x00\x00")
            f.write(b"\x01\x00")
            f.write(b"\x01\x00")
            f.write(b"\x44\xac\x00\x00")
            f.write(b"\x44\xac\x00\x00")
            f.write(b"\x02\x00")
            f.write(b"\x10\x00")
            f.write(b"data")
            f.write(b"\x00\x00\x00\x00")

        result = _fallback_analysis(temp_audio)

        self.assertIsNotNone(result)
        self.assertIn("duration", result)
        self.assertIn("structure", result)
        self.assertIn("emotion_curve", result)
        self.assertIn("tension_peaks", result)
        self.assertIn("fallback", result)
        self.assertTrue(result["fallback"])

        os.remove(temp_audio)

    @unittest.skipIf(not NUMPY_AVAILABLE, "numpy not installed")
    def test_detect_structure(self):
        """测试结构检测"""

        y = np.zeros(1000)
        sr = 22050
        rms = np.array([0.1, 0.3, 0.8, 0.6, 0.2])
        rms_times = np.array([0, 2, 4, 6, 8])

        structure = _detect_structure(y, sr, rms, rms_times, 8.0)

        self.assertTrue(len(structure) > 0)
        self.assertEqual(structure[0]["type"], "intro")
        self.assertEqual(structure[-1]["type"], "outro")

        for seg in structure:
            self.assertIn("start", seg)
            self.assertIn("end", seg)
            self.assertIn("energy", seg)
            self.assertIn(seg["energy"], ["low", "medium", "high"])

    @unittest.skipIf(not NUMPY_AVAILABLE, "numpy not installed")
    def test_smooth_emotion_curve(self):
        """测试情感曲线平滑"""

        times = np.linspace(0, 20, 100)
        values = np.sin(times) * 0.5 + 0.5

        curve = _smooth_emotion_curve(times, values)

        self.assertTrue(len(curve) > 0)
        # 允许稍微超过 50（因为可能添加最后一个点）
        self.assertTrue(len(curve) <= 52)

        for point in curve:
            self.assertIn("time", point)
            self.assertIn("value", point)
            self.assertTrue(0 <= point["value"] <= 1)

    def test_detect_tension_peaks(self):
        """测试张力峰值检测"""

        curve = [
            {"time": 0, "value": 0.2},
            {"time": 2, "value": 0.3},
            {"time": 4, "value": 0.8},  # 峰值
            {"time": 6, "value": 0.6},
            {"time": 8, "value": 0.9},  # 峰值
            {"time": 10, "value": 0.5},
        ]

        peaks = _detect_tension_peaks(curve, threshold=0.6)

        self.assertEqual(len(peaks), 2)
        self.assertIn(4, peaks)
        self.assertIn(8, peaks)

    def test_detect_tension_peaks_low_threshold(self):
        """测试低阈值张力峰值"""

        curve = [
            {"time": 0, "value": 0.1},
            {"time": 2, "value": 0.3},
            {"time": 4, "value": 0.2},
        ]

        peaks = _detect_tension_peaks(curve, threshold=0.6)

        self.assertEqual(len(peaks), 0)

    @unittest.skipIf(not NUMPY_AVAILABLE, "numpy not installed")
    def test_recommend_style(self):
        """测试风格推荐"""

        rms_high = np.array([0.7, 0.8, 0.9])
        style1 = _recommend_style(rms_high, bpm=130)
        self.assertEqual(style1, "热血")

        rms_med = np.array([0.4, 0.5, 0.6])
        style2 = _recommend_style(rms_med, bpm=100)
        self.assertEqual(style2, "励志")

        rms_low = np.array([0.1, 0.2, 0.3])
        style3 = _recommend_style(rms_low, bpm=80)
        self.assertEqual(style3, "治愈")


class TestMusicAnalyzerIntegration(unittest.TestCase):
    """音乐分析器集成测试"""

    def test_analyze_music_output_structure(self):
        """测试分析输出结构"""

        result = _fallback_analysis("dummy.mp3", error="test")

        required_fields = [
            "duration",
            "bpm",
            "structure",
            "emotion_curve",
            "tension_peaks",
            "recommended_style",
        ]

        for field in required_fields:
            self.assertIn(field, result)

    def test_structure_segments_valid(self):
        """测试结构片段有效性"""

        result = _fallback_analysis("dummy.mp3")

        for seg in result["structure"]:
            self.assertTrue(seg["start"] >= 0)
            self.assertTrue(seg["end"] > seg["start"])
            self.assertIn(seg["energy"], ["low", "medium", "high"])


if __name__ == "__main__":
    unittest.main(verbosity=2)