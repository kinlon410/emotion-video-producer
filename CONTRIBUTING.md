# Contributing to Emotion Video Producer

Thank you for your interest in contributing! This document outlines the development setup and contribution guidelines.

---

## Development Setup

### 1. Clone and Install

```bash
git clone https://github.com/YOUR_USERNAME/emotion-video-producer.git
cd emotion-video-producer
pip install -r requirements.txt
```

### 2. Install FFmpeg

```bash
# macOS
brew install ffmpeg

# Linux
sudo apt install ffmpeg
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 4. Run Tests

```bash
pytest tests/
```

---

## Project Structure

```
core/           # Core pipeline modules
web/            # Flask Web UI
agent/          # Async agent architecture
tests/          # Test suite
```

---

## Contribution Workflow

### Branch Naming

- `feature/xxx` — New features
- `fix/xxx` — Bug fixes
- `docs/xxx` — Documentation updates
- `refactor/xxx` — Code refactoring

### Commit Message Format

```
type: short description

# Types: feature, fix, docs, refactor, test, chore
# Example:
feature: add neon subtitle style option
fix: subtitle timing offset adjustment
```

### Pull Request Process

1. Fork the repository
2. Create a feature branch from `main`
3. Make changes with clear commit messages
4. Add tests for new functionality
5. Ensure all tests pass: `pytest`
6. Submit PR with description of changes

---

## Code Style

- Python 3.9+ compatibility
- Use type hints for public functions
- Follow existing naming conventions
- Add docstrings for complex functions
- No unnecessary comments (code should be self-explanatory)

---

## Testing

- Write unit tests for new modules
- Write integration tests for pipeline changes
- Test edge cases (nil input, empty input, error paths)

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_music_analyzer.py

# Run with coverage
pytest --cov=core tests/
```

---

## Adding New Features

### New TTS Provider

1. Create provider class in `core/tts_provider.py`
2. Implement `TTSProvider` interface
3. Add to provider registry in `config.py`
4. Add UI option in `web/index.html` and `streamlit_app.py`

### New Subtitle Style

1. Add style definition in `config.py` under `SUBTITLE_STYLES`
2. Add UI option in `web/static/app.js` and `streamlit_app.py`

### New Visual Source

1. Add API integration in `core/visual.py` or `core/multi_source_visual.py`
2. Add to source selector in UI

---

## Reporting Issues

Use GitHub Issues with:

- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version)

---

## Questions?

Open a GitHub Issue or Discussion for questions and suggestions.