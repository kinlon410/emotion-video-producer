#!/usr/bin/env python3
"""
Emotion Video Producer — 情感驱动视频生产 CLI

用法:
    # 基本用法
    python3 main.py --theme "东京夜行" --bgm music.mp3

    # 指定风格
    python3 main.py --theme "人生旅程" --bgm song.mp3 --style 励志

    # 指定输出路径
    python3 main.py --theme "城市夜景" --bgm bgm.mp3 --output videos/my_video.mp4

    # 批量生产
    python3 main.py --batch "东京夜行,巴黎印象,人生旅程" --bgm music.mp3

    # 分析音乐（不生产视频）
    python3 main.py --analyze music.mp3 --output analysis.json

    # 列出风格预设
    python3 main.py --list-styles
"""

import argparse
import json
import sys
from pathlib import Path

from core import produce_video, analyze_music, get_style_preset
from core.style_presets import list_styles
from config import DEFAULT_OUTPUT_DIR, DEFAULT_VOICE, DEFAULT_TTS_SPEED


def main():
    parser = argparse.ArgumentParser(
        description="Emotion Video Producer — 情感驱动视频生产",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本用法
  python3 main.py --theme "东京夜行" --bgm music.mp3

  # 指定风格
  python3 main.py --theme "人生旅程" --bgm song.mp3 --style 励志

  # 批量生产
  python3 main.py --batch "东京夜行,巴黎印象" --bgm music.mp3

  # 分析音乐
  python3 main.py --analyze music.mp3

  # 列出风格
  python3 main.py --list-styles
        """
    )

    # 生产参数
    parser.add_argument("--theme", help="视频主题")
    parser.add_argument("--bgm", help="BGM 音频文件路径")
    parser.add_argument("--output", default=None, help="输出视频路径")
    parser.add_argument("--batch", help="批量主题，逗号分隔")

    # 风格参数
    parser.add_argument("--style", default=None, help="风格预设 (热血/励志/治愈/文艺/欢快)")
    parser.add_argument("--list-styles", action="store_true", help="列出所有风格预设")

    # TTS 参数
    parser.add_argument("--tts-provider", default="edge",
                        choices=["edge", "dashscope", "moss", "cosyvoice"],
                        help="TTS 提供者 (edge 免费, dashscope 需付费, moss 自然语言指令, cosyvoice 本地模型)")
    parser.add_argument("--voice", default=DEFAULT_VOICE,
                        help="TTS 语音选择")
    parser.add_argument("--tts-speed", type=float, default=DEFAULT_TTS_SPEED,
                        help="TTS 语速 (0.5-2.0)")
    parser.add_argument("--tts-instruction", default="",
                        help="MOSS-TTS 语音指令（自然语言描述语音风格）")

    # 素材参数
    parser.add_argument("--visual-mode", default="auto",
                        choices=["pexels", "download", "generate", "auto"],
                        help="视觉素材获取模式")
    parser.add_argument("--unified-style", default=None,
                        choices=["city", "nature", "night", "cinematic", "travel"],
                        help="统一素材风格 (推荐抖音)")

    # 短视频模式参数
    parser.add_argument("--mode", default="normal",
                        choices=["normal", "short"],
                        help="生产模式: normal=标准/short=短视频")
    parser.add_argument("--duration-limit", type=int, default=None,
                        help="短视频时长限制 (秒)")
    parser.add_argument("--transition", default="normal",
                        choices=["normal", "fast", "cinematic"],
                        help="转场强度")
    parser.add_argument("--max-segment-duration", type=float, default=None,
                        help="每片段最大时长 (秒)")

    # 分析参数
    parser.add_argument("--analyze", metavar="AUDIO", help="仅分析音乐，不生产视频")

    # 其他参数
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="输出目录")
    parser.add_argument("--keep-temp", action="store_true", help="保留临时文件")

    args = parser.parse_args()

    # ── 列出风格 ──
    if args.list_styles:
        styles = list_styles()
        print("\n可用风格预设:")
        print("-" * 40)
        for s in styles:
            print(f"  {s['name']}: {s['description']}")
        print("-" * 40)
        return

    # ── 仅分析音乐 ──
    if args.analyze:
        result = analyze_music(args.analyze, args.output)
        if args.output is None:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # ── 检查必需参数 ──
    if not args.theme and not args.batch:
        parser.error("请指定 --theme 或 --batch")

    if not args.bgm:
        parser.error("请指定 --bgm 参数")

    # ── 确保输出目录存在 ──
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    # ── 收集主题列表 ──
    themes = []
    if args.batch:
        themes = [t.strip() for t in args.batch.split(",") if t.strip()]
    elif args.theme:
        themes = [args.theme]

    # ── 执行生产 ──
    results = []

    for theme in themes:
        output_path = args.output or f"{args.output_dir}/{theme.replace(' ', '_')}.mp4"

        print(f"\n{'='*60}")
        print(f"  处理主题: {theme}")
        print(f"{'='*60}")

        result = produce_video(
            theme=theme,
            bgm_path=args.bgm,
            output_path=output_path,
            style=args.style,
            voice=args.voice,
            tts_speed=args.tts_speed,
            tts_provider=args.tts_provider,
            tts_instruction=args.tts_instruction,
            visual_mode=args.visual_mode,
            unified_style=args.unified_style,
            keep_temp=args.keep_temp,
            mode=args.mode,
            duration_limit=args.duration_limit,
            transition_intensity=args.transition,
            max_segment_duration=args.max_segment_duration,
        )

        results.append((theme, result))

    # ── 汇总结果 ──
    print(f"\n{'='*60}")
    print(f"  批量生产汇总")
    print(f"{'='*60}")

    for theme, path in results:
        status = "✓ " + path if path else "✗ 失败"
        print(f"  {theme}: {status}")

    success = sum(1 for _, p in results if p)
    print(f"\n  成功: {success}/{len(results)}")

    sys.exit(0 if success == len(results) else 1)


if __name__ == "__main__":
    main()