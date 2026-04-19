# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Emotion Video Producer — 情感驱动视频生产系统。根据音乐情感分析自动生成短视频，使用 librosa 分析音频、AI 生成叙事文案、情感驱动素材选择、动态转场映射、字幕同步。

## Commands

### CLI Usage
```bash
# 生产单个视频
python3 main.py --theme "东京夜行" --bgm music.mp3

# 指定风格预设
python3 main.py --theme "人生旅程" --bgm song.mp3 --style 励志

# 批量生产
python3 main.py --batch "东京夜行,巴黎印象,人生旅程" --bgm music.mp3

# 仅分析音乐
python3 main.py --analyze music.mp3 --output analysis.json

# 列出风格预设
python3 main.py --list-styles
```

### Testing
```bash
# 运行所有测试
pytest

# 运行单个测试文件
pytest tests/test_music_analyzer.py

# 运行单个测试（verbose）
pytest tests/test_music_analyzer.py::TestMusicAnalyzer::test_fallback_analysis -v
```

### Web API
```bash
# 启动 Web 服务 (Flask)
python3 web_api.py
# 访问 http://localhost:5001
```

### Module Direct Execution
Each core module can be run standalone for debugging:
```bash
python3 -m core.music_analyzer --audio music.mp3 --output analysis.json
python3 -m core.visual_selector --analysis analysis.json --output visuals.json
python3 -m core.producer --theme "测试" --bgm music.mp3
```

## Environment Setup

Required environment variables:
```bash
export DASHSCOPE_API_KEY="your-api-key"  # TTS + AI文案 (阿里百炼)
export PEXELS_API_KEY="your-api-key"      # 视频素材下载
export PIXABAY_API_KEY="your-api-key"     # 视频素材备选
```

Required system dependency:
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

## Architecture

### Pipeline Flow (producer.py orchestrates)

1. **music_analyzer** — librosa 分析音频：能量曲线、结构分段、张力峰值、推荐风格
2. **narrative_generator** — AI 根据音乐情感结构生成文案和字幕
3. **visual_selector** — 情感能量 → 素材关键词映射 (high→运动/人群, medium→城市/建筑, low→风景/自然)
4. **transition_mapper** — 张力峰值 → 转场强度映射
5. **subtitle_sync** — ASR 语音识别 → 精确字幕分段（每条 ≤ 8 字）
6. **tts** — dashscope TTS API 生成旁白音频
7. **visual** — 多源素材下载 (pexels/pixabay/coverr)
8. **video_renderer** — FFmpeg 拼接片段、叠加字幕、混音

### Core Modules

```
core/
├── producer.py          # 主编排器，8-step pipeline
├── music_analyzer.py    # 音频情感分析 (librosa + fallback)
├── narrative_generator.py # AI 叙事生成 (dashscope)
├── visual_selector.py   # 情感→素材类型映射
├── transition_mapper.py # 张力→转场时长映射
├── subtitle_sync.py     # 字幕时间同步 (ASR-based)
├── style_presets.py     # 5种风格预设 (热血/励志/治愈/文艺/欢快)
├── tts.py               # TTS语音合成 (dashscope)
├── asr.py               # ASR语音识别 (dashscope whisper)
├── visual.py            # 素材下载 (pexels API)
├── video_renderer.py    # FFmpeg 视频渲染
└── multi_source_visual.py # 多源素材获取
```

### Key Config (config.py)

- `DEFAULT_WIDTH/HEIGHT/FPS`: 1920x1080 @ 30fps
- `BGM_VOLUME_WITH_NARRATION`: 0.35 (旁白时 BGM 降为背景)
- `NARRATION_VOLUME`: 1.5 (旁白突出)
- `FONT_PATH`: macOS/Linux/Windows 字体路径适配
- Style presets modify: 张力阈值、转场时长、字幕样式

### Style Presets

| 风格 | 张力阈值 | 转场时长 | 适用场景 |
|------|----------|----------|----------|
| 热血 | 0.75 | 0.12s | 高能量音乐 |
| 励志 | 0.55 | 0.18s | 正能量内容 |
| 治愈 | 0.35 | 0.35s | 温柔叙事 |
| 文艺 | 0.30 | 0.40s | 诗意意境 |
| 欢快 | 0.45 | 0.15s | 节日美食 |

## Notes

- FFmpeg 视频渲染使用 concat 模式拼接片段，统一编码参数避免停顿
- music_analyzer 有 fallback 模式：librosa 不可用时用 ffprobe 获取时长
- subtitle_sync 使用 ASR 结果实现精确字幕分段（每条 ≤ 8 字）
- Web API (web_api.py) 提供上传、生产、下载接口，前端在 web/index.html