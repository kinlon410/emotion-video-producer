# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.1.0] - 2026-04-19

### Added

- Initial open source release
- Music emotion analysis using librosa
- AI narrative generation via Dashscope
- Emotion-driven visual selection
- Dynamic transition mapping based on tension peaks
- ASR-based subtitle synchronization (≤8 chars per subtitle)
- 5 style presets: 热血/励志/治愈/文艺/欢快
- 7 subtitle styles: impact/minimal/neon/cinematic/typewriter/bounce/card
- Multiple TTS providers: Edge-TTS (free), Dashscope, local CosyVoice
- Flask Web UI with Apple-inspired design
- Streamlit Web UI
- Docker deployment support
- CLI and batch production mode

### Technical Features

- FFmpeg video rendering with unified encoding
- Multi-source visual download: Pexels, Pixabay, Coverr
- Real-time progress tracking
- API key persistence in Web UI
- User asset upload and AI analysis

---

## Future Roadmap

### [0.2.0] - Planned

- GitHub Actions CI/CD
- Unit test coverage >80%
- English narrative generation option
- Video preview before rendering

### [0.3.0] - Planned

- YouTube/Bilibili video download (yt-dlp)
- Direct upload to platforms
- Real-time collaborative editing