#!/usr/bin/env python3
"""
TTS 模块 — 统一 TTS 接口，支持多种 TTS 服务

支持:
- Edge-TTS (免费，无需 API Key)
- Dashscope CosyVoice (阿里百炼)
- MOSS-TTS (studio.mosi.cn，支持自然语言指令控制语音风格)
- CosyVoice Local (本地 Fun-CosyVoice3 模型)

用法:
    python3 -m core.tts "夜幕降临，城市开始苏醒" --output narration.mp3
    python3 -m core.tts "文案内容" --provider edge --voice zh-CN-XiaoxiaoNeural --output narration.mp3
    python3 -m core.tts "文案内容" --provider dashscope --voice longxiaochun --output narration.wav
    python3 -m core.tts "文案内容" --provider moss --instruction "一个温柔的女声" --output narration.mp3
    python3 -m core.tts "文案内容" --provider cosyvoice --voice normal --output narration.wav

MOSS-TTS:
    - API Key: 通过 MOSS_API_KEY 环境变量设置
    - instruction: 自然语言语音指令，由大模型生成
    - 示例: --instruction "一个御姐充满妩媚而又有磁性的声音"

CosyVoice 本地模型:
    - 模型路径: pretrained_models/Fun-CosyVoice3-0.5B (可通过 COSYVOICE_MODEL_DIR 环境变量设置)
    - 参考音频: asset/zero_shot_prompt.wav (模型内置)
    - 支持风格: normal, guangdong, dongbei, sichuan, fast, slow, happy, sad
    - 官方文档: https://funaudiollm.github.io/cosyvoice3/
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from config import DEFAULT_VOICE, DEFAULT_TTS_SPEED, DEFAULT_TTS_PROVIDER, COSYVOICE_MODEL_DIR, COSYVOICE_PATH

# 导入 TTS Provider（使用绝对导入避免循环依赖）
try:
    from core.tts_provider import synthesize_text, get_tts_provider, EdgeTTSProvider, DashscopeTTSProvider, MossTTSProvider, CosyVoiceLocalProvider
except ImportError:
    # 模块直接运行时的导入
    from tts_provider import synthesize_text, get_tts_provider


# ── 兼容旧接口 ──

CHINESE_VOICES = {
    "longxiaochun": "longxiaochun",   # 女声，温暖亲切，适合旁白
    "longwan": "longwan",             # 女声，知性温柔
    "longyue": "longyue",             # 女声，活泼可爱
    "longfei": "longfei",             # 男声，沉稳大气
    "longjielidou": "longjielidou",   # 男声，亲切自然
    "longshuo": "longshuo",           # 男声，年轻活力
    "longsheng": "longsheng",         # 男声，新闻播报风格
    "longhua": "longhua",             # 女声，温柔甜美
}


def text_to_speech(text: str, output_path: str, voice: str = DEFAULT_VOICE,
                   speed: float = DEFAULT_TTS_SPEED, provider: str = DEFAULT_TTS_PROVIDER,
                   instruction: str = None) -> Optional[str]:
    """将文本转为语音文件（统一接口）

    Args:
        text: 要转换的文本
        output_path: 输出文件路径（.mp3 或 .wav）
        voice: 语音名称
        speed: 语速 (0.5-2.0)
        provider: TTS 提供者 (edge/dashscope/moss/cosyvoice)
        instruction: MOSS-TTS 语音指令（由大模型生成）

    Returns:
        str: 输出文件路径，失败返回 None
    """
    print(f"[tts] 生成语音 (provider={provider}): {text[:30]}...")

    # CosyVoice / MOSS-TTS 建议使用 WAV 格式
    if provider in ("cosyvoice", "moss") and not output_path.endswith(".wav"):
        output_path = output_path.replace(".mp3", ".wav")

    # 使用 TTS Provider 工厂
    result = synthesize_text(text, output_path, provider, voice, speed, instruction=instruction)

    if result:
        return result

    # 失败时尝试备用 Provider
    if provider == "dashscope":
        print("[tts] Dashscope 失败，尝试 Edge-TTS 备用...")
        result = synthesize_text(text, output_path, "edge", "zh-CN-XiaoxiaoNeural", speed)
        if result:
            return result
    elif provider == "moss":
        print("[tts] MOSS-TTS 失败，尝试 Edge-TTS 备用...")
        result = synthesize_text(text, output_path, "edge", "zh-CN-XiaoxiaoNeural", speed)
        if result:
            return result
    elif provider == "cosyvoice":
        print("[tts] CosyVoice 本地失败，尝试 Edge-TTS 备用...")
        result = synthesize_text(text, output_path, "edge", "zh-CN-XiaoxiaoNeural", speed)
        if result:
            return result

    print("[Warning] TTS 不可用，将跳过旁白生成", file=sys.stderr)
    return None


def get_audio_duration(audio_path: str) -> float:
    """获取音频文件时长"""

    import subprocess

    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        audio_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception:
        pass

    return 0.0


def main():
    parser = argparse.ArgumentParser(description="TTS 模块")
    parser.add_argument("text", help="要转换的文本")
    parser.add_argument("--output", default="narration.mp3", help="输出文件路径")
    parser.add_argument("--voice", default=None, help="语音选择")
    parser.add_argument("--speed", type=float, default=DEFAULT_TTS_SPEED, help="语速")
    parser.add_argument("--provider", default=DEFAULT_TTS_PROVIDER,
                        choices=["edge", "dashscope", "moss", "cosyvoice"], help="TTS 提供者")
    parser.add_argument("--instruction", default=None, help="MOSS-TTS 语音指令")
    parser.add_argument("--wav", action="store_true", help="输出 WAV 格式")
    parser.add_argument("--list-voices", action="store_true", help="列出可用语音")
    args = parser.parse_args()

    if args.list_voices:
        tts = get_tts_provider(args.provider)
        voices = tts.get_available_voices()
        for v in voices:
            print(f"  {v['name']}: {v['description']}")
        return

    output_path = args.output
    if args.wav and not output_path.endswith(".wav"):
        output_path = output_path.replace(".mp3", ".wav")

    # CosyVoice 建议使用 WAV
    if args.provider == "cosyvoice" and not output_path.endswith(".wav"):
        output_path = output_path.replace(".mp3", ".wav")

    # 默认语音选择
    voice = args.voice
    if voice is None:
        if args.provider == "edge":
            voice = "zh-CN-XiaoxiaoNeural"
        elif args.provider == "cosyvoice":
            voice = "normal"
        elif args.provider == "moss":
            voice = "default"
        else:
            voice = DEFAULT_VOICE

    result = text_to_speech(args.text, output_path, voice, args.speed, args.provider, args.instruction)

    if result:
        print(f"输出: {result}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()