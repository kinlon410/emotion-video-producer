# CosyVoice Local TTS Setup

CosyVoice is an optional local TTS (Text-to-Speech) provider for high-quality Chinese voice synthesis. This document explains how to set it up separately from the main installation.

---

## Why Separate Installation?

The CosyVoice model files are large (~9GB) and should not be included in the Git repository. Instead, download them separately if you want to use local TTS.

---

## Prerequisites

- Python 3.9+
- CUDA-capable GPU (recommended) or CPU fallback
- ~9GB disk space for model files

---

## Installation Steps

### 1. Clone CosyVoice Repository

```bash
cd emotion-video-producer
git clone https://github.com/FunAudioLLM/CosyVoice.git
```

### 2. Download Model Files

Download pretrained models from HuggingFace:

```bash
# Option 1: Download Fun-CosyVoice3-0.5B (recommended)
# From https://huggingface.co/FunAudioLLM/Fun-CosyVoice3-0.5B
# Place in: Fun-CosyVoice3-0.5B-2512/

# Option 2: Use huggingface-cli
pip install huggingface_hub
huggingface-cli download FunAudioLLM/Fun-CosyVoice3-0.5B --local-dir Fun-CosyVoice3-0.5B-2512
```

### 3. Install CosyVoice Dependencies

```bash
cd CosyVoice
pip install -r requirements.txt
```

### 4. Configure Environment

Add to your `.env` file:

```bash
# CosyVoice code directory
COSYVOICE_PATH=/path/to/emotion-video-producer/CosyVoice

# Model directory
COSYVOICE_MODEL_DIR=/path/to/emotion-video-producer/Fun-CosyVoice3-0.5B-2512
```

---

## Usage

In Web UI, select "CosyVoice" as TTS provider. Available voice styles:

- `normal` — Default neutral voice
- `guangdong` — Cantonese accent
- `dongbei` — Northeast Mandarin accent
- `sichuan` — Sichuan accent
- `fast` — Fast speech
- `slow` — Slow speech
- `happy` — Happy emotion
- `sad` — Sad emotion

---

## Troubleshooting

### Import Error: No module named 'cosyvoice'

Check that:
1. COSYVOICE_PATH points to the CosyVoice **code** directory (not model directory)
2. CosyVoice dependencies are installed

### Model Loading Slow

First load takes ~30 seconds. Subsequent calls are faster.

### GPU Memory Issues

Use smaller model or reduce batch size in config.

---

## Alternative: Use Free TTS

If CosyVoice setup is complex, use Edge-TTS (free, no API key required):

- Default in Web UI
- Multiple Chinese voices available
- Works offline after first download