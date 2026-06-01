#!/usr/bin/env python3
"""
Emotion Video Producer 配置管理
"""

import os
from pathlib import Path

# ── API Keys ──

DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
MOSS_API_KEY = os.environ.get("MOSS_API_KEY", "")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "")
COVERR_API_KEY = os.environ.get("COVERR_API_KEY", "")  # Coverr 无需 API Key

# ── 默认参数 ──

DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"  # Edge-TTS 默认音色 (免费)
DEFAULT_TTS_SPEED = 1.0
DEFAULT_TTS_PROVIDER = "edge"  # 默认使用 Edge-TTS (免费)

# CosyVoice 本地模型配置
COSYVOICE_MODEL_DIR = os.environ.get("COSYVOICE_MODEL_DIR", "pretrained_models/Fun-CosyVoice3-0.5B")
COSYVOICE_PATH = os.environ.get("COSYVOICE_PATH", "")  # CosyVoice 代码目录路径
DEFAULT_OUTPUT_DIR = "output"
DEFAULT_FPS = 30
DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080

# ── 音频分析参数 ──

ANALYSIS_SAMPLE_RATE = 22050  # librosa 默认
ANALYSIS_HOP_LENGTH = 512     # librosa 默认
MIN_TENSION_THRESHOLD = 0.6   # 张力峰值阈值
ANALYSIS_TARGET_SEGMENTS = 7  # 目标片段数

# ── 转场时长映射（快速模式）──

TRANSITION_DURATIONS = {
    "high_energy": 0.06,   # 极快转场 - 激烈切换
    "medium_energy": 0.12, # 快速转场 - 流畅切换
    "low_energy": 0.20,    # 中等转场 - 平滑过渡
}

# ── 片段时长限制 ──

DEFAULT_MAX_SEGMENT_DURATION = 2.0  # 默认每片段最大时长（秒）
SHORT_VIDEO_MAX_SEGMENT = 1.5       # 短视频模式每片段最大时长（秒）
MIN_SEGMENT_DURATION = 0.8          # 最小片段时长（秒）

# ── 音量配置 ──

BGM_VOLUME = 0.8           # BGM 默认音量（无旁白时）
BGM_VOLUME_WITH_NARRATION = 0.35  # BGM 音量（有旁白时，作为背景）
NARRATION_VOLUME = 1.5     # 旁白音量（突出）
SUBTITLE_SYNC_OFFSET = 0.5  # 字幕开始偏移

# ── 字幕样式 ──

SUBTITLE_STYLES = {
    # 大字体粗边框 - 适合热血/励志视频
    "impact": {
        "fontsize": 52,
        "fontcolor": "white",
        "borderw": 3,
        "bordercolor": "black@0.7",
        "bold": True,
        "shadow": "0px 0px 10px rgba(255,255,255,0.5)",
        "description": "冲击力风格 - 大字体粗边框",
    },
    # 小字体无边框 - 适合治愈/文艺视频
    "minimal": {
        "fontsize": 36,
        "fontcolor": "white@0.85",
        "borderw": 0,
        "bold": False,
        "description": "极简风格 - 小字体无边框",
    },
    # 霓虹发光 - 适合夜景/科技视频
    "neon": {
        "fontsize": 48,
        "fontcolor": "cyan",
        "borderw": 2,
        "bordercolor": "black@0.5",
        "bold": False,
        "shadow": "0px 0px 15px cyan",
        "description": "霓虹风格 - 发光效果",
    },
    # 电影风格 - 适合叙事视频
    "cinematic": {
        "fontsize": 42,
        "fontcolor": "white@0.9",
        "borderw": 1,
        "bordercolor": "black@0.4",
        "bold": False,
        "description": "电影风格 - 专业叙事",
    },
    # 打字机效果 - 新增
    "typewriter": {
        "fontsize": 38,
        "fontcolor": "white",
        "borderw": 1,
        "bordercolor": "black@0.6",
        "bold": False,
        "animation": "typewriter",
        "description": "打字机风格 -逐字显示",
    },
    # 弹跳动画 - 新增
    "bounce": {
        "fontsize": 44,
        "fontcolor": "yellow",
        "borderw": 2,
        "bordercolor": "black@0.5",
        "bold": True,
        "animation": "bounce",
        "description": "弹跳风格 - 活泼可爱",
    },
    # 卡片风格 - 新增
    "card": {
        "fontsize": 40,
        "fontcolor": "white",
        "borderw": 0,
        "background": "rgba(0,0,0,0.6)",
        "padding": 10,
        "bold": False,
        "description": "卡片风格 - 黑底白字",
    },
}

# 字幕样式列表（用于界面选择）
SUBTITLE_STYLE_LIST = [
    {"name": "impact", "description": "冲击力风格 - 大字体粗边框（适合热血/励志）"},
    {"name": "minimal", "description": "极简风格 - 小字体无边框（适合治愈/文艺）"},
    {"name": "neon", "description": "霓虹风格 - 发光效果（适合夜景/科技）"},
    {"name": "cinematic", "description": "电影风格 - 专业叙事"},
    {"name": "typewriter", "description": "打字机风格 - 逐字显示"},
    {"name": "bounce", "description": "弹跳风格 - 活泼可爱（适合欢快）"},
    {"name": "card", "description": "卡片风格 - 黑底白字"},
]

# ── 字体路径 ──

FONT_PATH = "/System/Library/Fonts/PingFang.ttc"  # macOS
FONT_FALLBACK = "/System/Library/Fonts/Helvetica.ttc"  # macOS 英文备选

# Linux 字体路径
if not os.path.exists(FONT_PATH):
    FONT_PATH = "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"
    FONT_FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# Windows 字体路径
if not os.path.exists(FONT_PATH):
    FONT_PATH = "C:/Windows/Fonts/msyh.ttc"
    FONT_FALLBACK = "C:/Windows/Fonts/arial.ttf"

# ── 视觉素材模式 ──

VISUAL_MODES = {
    "pexels": {
        "priority": 1,
        "requires_key": True,
        "supports_video": True,
    },
    "pixabay": {
        "priority": 2,
        "requires_key": True,
        "supports_video": True,
    },
    "coverr": {
        "priority": 3,
        "requires_key": False,
        "supports_video": True,
    },
    "generate": {
        "priority": 4,
        "requires_key": False,
        "supports_video": False,
    },
}

# ── 预设调色板 ──

PALETTES = {
    "city_night": ("0a0a2e", "1a1a4e", "2d1b69"),
    "sunset": ("1a0a2e", "4a1942", "c94b4b"),
    "ocean": ("0a1628", "0d3b66", "1a936f"),
    "neon": ("0a0a1a", "1a0a3e", "e94560"),
    "warm": ("1a0a0a", "3e1a0a", "b85c38"),
    "minimal": ("0f0f0f", "1a1a2e", "16213e"),
    "forest": ("0a1a0a", "1a3a1a", "2d5a2d"),
}

# ── 工作目录 ──

WORK_DIR = Path(os.environ.get("EMOTION_VIDEO_WORK_DIR", "/tmp/emotion-video-producer"))

# ── 模板目录 ──

TEMPLATE_DIR = Path(os.environ.get("EMOTION_VIDEO_TEMPLATE_DIR", str(Path(__file__).parent / "templates")))

# ── 渲染参数 ──

RENDER_PRESET = "medium"
RENDER_CRF = 23
RENDER_TIMEOUT = 600  # 渲染超时（秒）

# ── AI 叙事参数 ──

NARRATIVE_MAX_TOKENS = 800
NARRATIVE_TIMEOUT = 60

# ── 素材下载参数 ──

DOWNLOAD_TIMEOUT = 120
DOWNLOAD_RETRIES = 3
MIN_CLIP_DURATION = 1.0
MAX_CLIP_DURATION = 10.0