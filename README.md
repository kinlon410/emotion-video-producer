# Emotion Video Producer

**Music-driven short video generation with AI-powered narrative sync**

Emotion Video Producer automatically generates short videos based on music emotion analysis. Unlike beat-sync approaches, this system uses librosa to analyze audio energy curves, AI to generate narrative scripts, emotion-driven visual selection, and dynamic transition mapping.

---

## Features

- **Music Emotion Analysis**: Analyze music structure, energy curves, and tension peaks using librosa
- **AI Narrative Generation**: Dynamically generate scripts based on emotional structure
- **Emotion-Driven Visual Selection**: High energy → sports/crowds, low energy → landscapes/nature
- **Dynamic Transitions**: Tension peaks use intense transitions, calm sections use soft ones
- **Subtitle Emotion Sync**: Subtitles appear at emotional turning points
- **Style Presets**: 热血/励志/治愈/文艺/欢快 one-click selection
- **7 Subtitle Styles**: impact, minimal, neon, cinematic, typewriter, bounce, card
- **Multiple TTS Providers**: Edge-TTS (free), Dashscope, local CosyVoice

---

## Quick Start

### 1. Install Dependencies

```bash
# Python dependencies
pip install -r requirements.txt

# FFmpeg (required for video processing)
# macOS:
brew install ffmpeg

# Linux:
sudo apt install ffmpeg
```

### 2. Configure API Keys

```bash
# Copy example config
cp .env.example .env

# Edit with your keys
# - DASHSCOPE_API_KEY: https://dashscope.console.aliyun.com/
# - PEXELS_API_KEY: https://www.pexels.com/api/
```

Do not commit `.env`, browser-exported credentials, or any local config file containing API keys. This repository is configured to keep those files out of Git by default.

### 3. Generate a Video

```bash
# CLI
python main.py --theme "Tokyo Night Walk" --bgm music.mp3

# Web UI
python web_api.py
# Open http://localhost:5001

# Streamlit UI
streamlit run streamlit_app.py
```

---

## Architecture

```
emotion-video-producer/
├── core/                    # Core modules (10K lines)
│   ├── music_analyzer.py    # Audio emotion analysis (librosa)
│   ├── narrative_generator.py # AI narrative (Dashscope)
│   ├── visual_selector.py   # Emotion → visual keywords
│   ├── transition_mapper.py # Tension → transition duration
│   ├── subtitle_sync.py     # ASR-based subtitle timing
│   ├── tts.py               # TTS providers (Edge/Dashscope/CosyVoice)
│   └── producer.py          # Main pipeline orchestrator
├── web/                     # Flask Web UI
├── agent/                   # Agent architecture (async)
├── tests/                   # Test suite
└── Dockerfile               # Container deployment
```

---

## Pipeline Flow

```
BGM Upload → Music Analysis → AI Narrative → Visual Selection → 
TTS Generation → ASR Sync → Video Rendering → Output
```

| Step | Module | Description |
|------|--------|-------------|
| 1 | music_analyzer | librosa: energy curve, segments, tension peaks |
| 2 | narrative_generator | AI: script based on emotional structure |
| 3 | visual_selector | Emotion → keywords (high→sports, low→nature) |
| 4 | transition_mapper | Tension → transition duration |
| 5 | subtitle_sync | ASR → precise subtitle timing (≤8 chars) |
| 6 | tts | Generate narration audio |
| 7 | visual | Download stock footage (Pexels/Pixabay/Coverr) |
| 8 | producer | FFmpeg: compile clips, overlay subtitles, mix audio |

---

## Style Presets

| Style | Tension | Transition | Visuals | Subtitles |
|-------|---------|------------|---------|-----------|
| 热血 | 0.75 | 0.12s | Sports/crowds | Large bold |
| 励志 | 0.55 | 0.18s | City/walking | Medium |
| 治愈 | 0.35 | 0.35s | Landscape/nature | Soft small |
| 文艺 | 0.30 | 0.40s | Sky/stars | Cinematic |
| 欢快 | 0.45 | 0.15s | Market/food | Neon |

---

## Comparison with Beat-Sync Tools

| Feature | Beat-Sync (autocutclaw) | Emotion-Driven (this) |
|---------|-------------------------|------------------------|
| Driver | BPM beats | Energy curve |
| Visuals | Random keywords | Emotion-aligned |
| Transitions | Uniform duration | Dynamic by tension |
| Subtitles | Time-based allocation | Tension peak sync |
| Styles | None | 5 presets |

---

## License

MIT License - see [LICENSE](LICENSE) file.

---

## Open Source Safety

- Keep all API keys in environment variables or in the local UI config stored under `~/.emotion-video-producer/`.
- Do not commit `.env`, model weights, generated videos, uploaded user media, or local cache directories.
- Download `CosyVoice` code and pretrained models separately; they are intentionally excluded from version control.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and PR guidelines.

---

<br>
<br>

---

# Emotion Video Producer（中文）

**情感驱动视频生产系统 — 根据音乐情感自动生成短视频**

不同于节拍同步方案，本系统使用 librosa 分析音频能量曲线，AI 生成叙事文案，情感驱动素材选择，动态转场映射。

---

## 特性

- **音乐情感分析**: 使用 librosa 分析音乐结构、情感曲线、张力峰值
- **AI叙事生成**: 根据音乐情感结构动态生成文案
- **情感驱动素材选择**: 高潮配运动/人群，平静配风景/自然
- **动态转场**: 张力峰值使用激烈转场，低能量使用柔和转场
- **字幕情感同步**: 字幕在张力转折点出现
- **风格预设**: 热血/励志/治愈/文艺/欢快一键选择
- **7 种字幕样式**: impact, minimal, neon, cinematic, typewriter, bounce, card
- **多种 TTS 提供者**: Edge-TTS（免费）、阿里百炼、本地 CosyVoice

---

## 快速开始

### 1. 安装依赖

```bash
# Python 依赖
pip install -r requirements.txt

# FFmpeg（视频处理必需）
# macOS:
brew install ffmpeg

# Linux:
sudo apt install ffmpeg
```

### 2. 配置 API Key

```bash
# 复制示例配置
cp .env.example .env

# 编辑填入你的 Key
# - DASHSCOPE_API_KEY: https://dashscope.console.aliyun.com/
# - PEXELS_API_KEY: https://www.pexels.com/api/
```

### 3. 生成视频

```bash
# CLI 命令行
python main.py --theme "东京夜行" --bgm music.mp3

# Web 界面
python web_api.py
# 访问 http://localhost:5001

# Streamlit 界面
streamlit run streamlit_app.py
```

---

## 架构

```
emotion-video-producer/
├── core/                    # 核心模块（10K 行代码）
│   ├── music_analyzer.py    # 音频情感分析（librosa）
│   ├── narrative_generator.py # AI 叙事生成（Dashscope）
│   ├── visual_selector.py   # 情感→素材关键词映射
│   ├── transition_mapper.py # 张力→转场时长映射
│   ├── subtitle_sync.py     # ASR 精确字幕分段
│   ├── tts.py               # TTS 提供者（Edge/Dashscope/CosyVoice）
│   └── producer.py          # 主流程编排器
├── web/                     # Flask Web 界面
├── agent/                   # Agent 异步架构
├── tests/                   # 测试套件
└── Dockerfile               # 容器部署
```

---

## 流程

```
上传 BGM → 音乐分析 → AI 叙事 → 素材选择 → 
TTS 生成 → ASR 同步 → 视频渲染 → 输出
```

| 步骤 | 模块 | 说明 |
|------|------|------|
| 1 | music_analyzer | librosa: 能量曲线、分段、张力峰值 |
| 2 | narrative_generator | AI: 根据情感结构生成文案 |
| 3 | visual_selector | 情感 → 关键词（高潮→运动，平静→自然） |
| 4 | transition_mapper | 张力 → 转场时长 |
| 5 | subtitle_sync | ASR → 精确字幕时间（每条≤8字） |
| 6 | tts | 生成旁白音频 |
| 7 | visual | 下载素材（Pexels/Pixabay/Coverr） |
| 8 | producer | FFmpeg: 拼接片段、叠加字幕、混音 |

---

## 风格预设

| 风格 | 张力阈值 | 转场时长 | 素材类型 | 字幕样式 |
|------|----------|----------|----------|----------|
| 热血 | 0.75 | 0.12s | 运动/人群/光效 | 大号加粗 |
| 劬志 | 0.55 | 0.18s | 城市/行走/地标 | 中号 |
| 治愈 | 0.35 | 0.35s | 风景/空镜/自然 | 小号柔和 |
| 文艺 | 0.30 | 0.40s | 天空/星空/光影 | 电影感 |
| 欢快 | 0.45 | 0.15s | 市场/美食/节日 | 霓虹色 |

---

## 与节拍同步工具的区别

| 特性 | 节拍同步（autocutclaw） | 情感驱动（本项目） |
|------|------------------------|-------------------|
| 驱动方式 | BPM 节拍 | 能量曲线 |
| 视觉选择 | 随机关键词 | 情感语义对齐 |
| 转场强度 | 统一时长 | 动态调整 |
| 字幕时机 | 按时长分配 | 张力峰值同步 |
| 风格选择 | 无 | 5 种预设风格 |

---

## 许可证

MIT 许可证 — 见 [LICENSE](LICENSE) 文件。

---

## 贡献指南

开发环境和 PR 规范见 [CONTRIBUTING.md](CONTRIBUTING.md)。
