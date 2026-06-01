#!/usr/bin/env python3
"""
测试配置和 fixtures
"""

import os
import sys
import tempfile
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


@pytest.fixture
def temp_dir():
    """临时目录 fixture"""
    dir_path = tempfile.mkdtemp()
    yield dir_path
    # 清理
    import shutil
    shutil.rmtree(dir_path, ignore_errors=True)


@pytest.fixture
def sample_audio(temp_dir):
    """创建测试音频文件"""

    audio_path = os.path.join(temp_dir, "test_audio.wav")

    # 创建简单的 WAV 文件
    with open(audio_path, "wb") as f:
        # RIFF header
        f.write(b"RIFF")
        f.write(b"\x24\x00\x00\x00")
        f.write(b"WAVE")
        # fmt chunk
        f.write(b"fmt ")
        f.write(b"\x10\x00\x00\x00")
        f.write(b"\x01\x00")
        f.write(b"\x01\x00")
        f.write(b"\x44\xac\x00\x00")
        f.write(b"\x44\xac\x00\x00")
        f.write(b"\x02\x00")
        f.write(b"\x10\x00")
        # data chunk (空数据)
        f.write(b"data")
        f.write(b"\x00\x00\x00\x00")

    return audio_path


@pytest.fixture
def sample_analysis():
    """测试音乐分析结果"""

    return {
        "duration": 20.5,
        "bpm": 120,
        "structure": [
            {"type": "intro", "start": 0, "end": 3, "energy": "low"},
            {"type": "verse", "start": 3, "end": 8, "energy": "medium"},
            {"type": "chorus", "start": 8, "end": 15, "energy": "high"},
            {"type": "outro", "start": 15, "end": 20.5, "energy": "low"},
        ],
        "emotion_curve": [
            {"time": 0, "value": 0.2},
            {"time": 5, "value": 0.5},
            {"time": 10, "value": 0.9},
            {"time": 15, "value": 0.4},
            {"time": 20, "value": 0.1},
        ],
        "tension_peaks": [10],
        "recommended_style": "励志",
    }


@pytest.fixture
def sample_narrative():
    """测试叙事结果"""

    return {
        "title_text": "人生旅程",
        "narration_script": "每一步都算数，人生没有白走的路。",
        "subtitle_segments": [
            {"id": "L1", "text_zh": "每一步都算数", "text_en": "Every step counts", "start": 0.5, "end": 2.0},
            {"id": "L2", "text_zh": "人生没有白走的路", "text_en": "No wasted paths", "start": 2.5, "end": 4.0},
        ],
        "segment_narrations": [
            {"segment_type": "intro", "text": "旅程开始", "start": 0, "end": 3},
            {"segment_type": "verse", "text": "曾经迷茫", "start": 3, "end": 8},
            {"segment_type": "chorus", "text": "此刻坚定", "start": 8, "end": 15},
        ],
    }