#!/usr/bin/env python3
"""
TTS 提供者模块 — 支持多种 TTS 服务

提供者：
- EdgeTTSProvider: Microsoft Edge-TTS (免费，无需 API Key)
- DashscopeTTSProvider: 阿里百炼 CosyVoice (现有实现)
- CosyVoiceLocalProvider: 本地 CosyVoice 模型 (Fun-CosyVoice3)

用法:
    python3 -m core.tts_provider --provider edge --text "测试" --output test.mp3
    python3 -m core.tts_provider --provider dashscope --text "测试" --output test.mp3
    python3 -m core.tts_provider --provider cosyvoice --text "测试" --output test.wav
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional

from config import DASHSCOPE_API_KEY, MOSS_API_KEY, DEFAULT_VOICE, DEFAULT_TTS_SPEED

# ── Edge-TTS 配置 ──

EDGE_TTS_VOICES = {
    # 中文音色
    "zh-CN-XiaoxiaoNeural": "晓晓 - 女声，活泼自然",
    "zh-CN-YunxiNeural": "云希 - 男声，年轻活力",
    "zh-CN-YunjianNeural": "云健 - 男声，新闻播报",
    "zh-CN-XiaoyiNeural": "晓伊 - 女声，温柔甜美",
    "zh-CN-YunjianSportNeural": "云健体育 - 男声，运动解说",
    "zh-CN-XiaochenNeural": "晓辰 - 女声，知性温柔",
    "zh-CN-XiaohanNeural": "晓涵 - 女声，温暖亲切",
    "zh-CN-XiaomengNeural": "晓梦 - 女声，儿童风格",
    "zh-CN-XiaomoNeural": "晓墨 - 女声，成熟稳重",
    "zh-CN-XiaoruiNeural": "晓睿 - 女声，客服风格",
    "zh-CN-XiaoshuangNeural": "晓双 - 女声，儿童风格",
    "zh-CN-XiaoxuanNeural": "晓萱 - 女声，温柔自然",
    "zh-CN-XiaoyanNeural": "晓颜 - 女声，客服风格",
    "zh-CN-XiaoyouNeural": "晓悠 - 女声，儿童风格",
    "zh-CN-YunfengNeural": "云枫 - 男声，沉稳大气",
    "zh-CN-YunhaoNeural": "云皓 - 男声，新闻播报",
    "zh-CN-YunxiaNeural": "云夏 - 男声，儿童风格",
    "zh-CN-YunyeNeural": "云野 - 男声，故事讲述",
    "zh-CN-YunzeNeural": "云泽 - 男声，新闻播报",

    # 英文音色
    "en-US-JennyNeural": "Jenny - 美式女声，自然流畅",
    "en-US-GuyNeural": "Guy - 美式男声，沉稳有力",
    "en-US-AriaNeural": "Aria - 美式女声，情感丰富",
    "en-US-DavisNeural": "Davis - 美式男声，商务风格",
    "en-GB-SoniaNeural": "Sonia - 英式女声，优雅稳重",
    "en-GB-RyanNeural": "Ryan - 英式男声，新闻播报",
}


class TTSProvider(ABC):
    """TTS 提供者抽象基类"""

    @abstractmethod
    def synthesize(
        self,
        text: str,
        output_path: str,
        voice: str = None,
        speed: float = 1.0,
    ) -> Optional[str]:
        """合成语音

        Args:
            text: 要转换的文本
            output_path: 输出文件路径
            voice: 语音名称
            speed: 语速 (0.5-2.0)

        Returns:
            str: 输出文件路径，失败返回 None
        """
        pass

    @abstractmethod
    def get_available_voices(self) -> List[Dict]:
        """获取可用语音列表

        Returns:
            list: [{"name": "...", "description": "..."}, ...]
        """
        pass

    def clone_voice(self, reference_audio: str) -> Optional[str]:
        """克隆语音（仅部分 Provider 支持）

        Args:
            reference_audio: 参考音频路径

        Returns:
            str: 克隆的语音 ID，不支持返回 None
        """
        return None


class EdgeTTSProvider(TTSProvider):
    """Microsoft Edge-TTS 提供者（免费）"""

    def __init__(self):
        self._check_edge_tts()

    def _check_edge_tts(self):
        """检查 edge-tts 是否可用"""
        try:
            import edge_tts
            self._edge_tts = edge_tts
        except ImportError:
            print("[Warning] edge-tts 未安装，请运行: pip install edge-tts", file=sys.stderr)
            self._edge_tts = None

    def synthesize(
        self,
        text: str,
        output_path: str,
        voice: str = "zh-CN-XiaoxiaoNeural",
        speed: float = 1.0,
    ) -> Optional[str]:
        """使用 Edge-TTS 合成语音"""

        if self._edge_tts is None:
            print("[Error] edge-tts 不可用", file=sys.stderr)
            return None

        if not text:
            print("[Error] 文本为空", file=sys.stderr)
            return None

        # 语速转换: edge-tts 使用 "+0%" 或 "-0%" 格式
        # speed=1.0 -> +0%, speed=1.5 -> +50%, speed=0.8 -> -20%
        if speed >= 1.0:
            rate = f"+{int((speed - 1.0) * 100)}%"
        else:
            rate = f"-{int((1.0 - speed) * 100)}%"

        print(f"[EdgeTTS] 生成语音: {text[:30]}...")
        print(f"  音色: {voice}, 语速: {rate}")

        try:
            # 创建 Communicate 对象
            communicate = self._edge_tts.Communicate(text, voice, rate=rate)

            # 确保输出目录存在
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # 异步保存
            asyncio.run(communicate.save(output_path))

            # 获取时长
            duration = self._get_audio_duration(output_path)
            print(f"  语音时长: {duration}s")

            return output_path

        except Exception as e:
            print(f"[Error] Edge-TTS 失败: {e}", file=sys.stderr)
            return None

    def _get_audio_duration(self, audio_path: str) -> float:
        """获取音频时长"""

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

    def get_available_voices(self) -> List[Dict]:
        """获取可用语音列表"""

        voices = []
        for name, desc in EDGE_TTS_VOICES.items():
            voices.append({
                "name": name,
                "description": desc,
                "language": name.split("-")[0],
            })

        return voices

    async def list_all_voices(self) -> List[Dict]:
        """从 Edge-TTS API 获取完整语音列表"""

        if self._edge_tts is None:
            return []

        try:
            voices = await self._edge_tts.list_voices()
            return [
                {
                    "name": v["ShortName"],
                    "description": v.get("FriendlyName", v["ShortName"]),
                    "language": v["Locale"],
                }
                for v in voices
            ]
        except Exception as e:
            print(f"[Error] 获取语音列表失败: {e}", file=sys.stderr)
            return []


class DashscopeTTSProvider(TTSProvider):
    """阿里百炼 CosyVoice TTS 提供者

    注意：仅支持中文音色，不支持其他语言
    """

    CHINESE_VOICES = {
        "longxiaochun": "龙小春 - 女声，温暖亲切",
        "longwan": "龙婉 - 女声，知性温柔",
        "longyue": "龙悦 - 女声，活泼可爱",
        "longfei": "龙飞 - 男声，沉稳大气",
        "longjielidou": "龙杰力豆 - 男声，亲切自然",
        "longshuo": "龙硕 - 男声，年轻活力",
        "longsheng": "龙生 - 男声，新闻播报",
        "longhua": "龙花 - 女声，温柔甜美",
    }

    # Dashscope 支持的其他音色（如有）
    OTHER_VOICES = {
        "zhiyan": "知燕 - 女声，温柔知性",
        "zhixiao": "知小 - 女声，活泼可爱",
        "zhimiao": "知妙 - 女声，甜美温柔",
        "zhiyan_emo": "知燕情感版 - 支持情感表达",
    }

    TTS_MODEL = "cosyvoice-v1"

    def __init__(self):
        self._check_dashscope()

    def _check_dashscope(self):
        """检查 dashscope 是否可用"""
        try:
            import dashscope
            from dashscope.audio.tts_v2 import SpeechSynthesizer, AudioFormat
            self._dashscope = dashscope
            self._SpeechSynthesizer = SpeechSynthesizer
            self._AudioFormat = AudioFormat
        except ImportError:
            print("[Warning] dashscope 未安装", file=sys.stderr)
            self._dashscope = None

    def synthesize(
        self,
        text: str,
        output_path: str,
        voice: str = "longxiaochun",
        speed: float = 1.0,
    ) -> Optional[str]:
        """使用 Dashscope 合成语音"""

        if self._dashscope is None or not DASHSCOPE_API_KEY:
            print("[Error] Dashscope TTS 不可用", file=sys.stderr)
            return None

        if not text:
            print("[Error] 文本为空", file=sys.stderr)
            return None

        self._dashscope.api_key = DASHSCOPE_API_KEY

        # 合并所有支持的音色
        all_voices = {**self.CHINESE_VOICES, **self.OTHER_VOICES}

        # 检查音色是否有效
        if voice not in all_voices:
            # 如果传入的是 Edge-TTS 的英文音色，提示错误
            if voice.startswith("en-") or voice.startswith("zh-CN-"):
                print(f"[Error] Dashscope 不支持 Edge-TTS 音色 '{voice}'，请使用中文音色如 'longxiaochun'", file=sys.stderr)
            else:
                print(f"[Error] Dashscope 不支持音色 '{voice}'，可用音色: {list(all_voices.keys())}", file=sys.stderr)
            return None

        voice_id = voice  # 直接使用传入的音色名称

        print(f"[DashscopeTTS] 生成语音: {text[:30]}...")
        print(f"  音色: {voice_id}")

        # 根据输出格式选择
        if output_path.endswith(".wav"):
            format = self._AudioFormat.WAV_16000HZ_MONO_16BIT
        else:
            format = self._AudioFormat.MP3_22050HZ_MONO_256KBPS

        try:
            synthesizer = self._SpeechSynthesizer(
                model=self.TTS_MODEL,
                voice=voice_id,
                format=format,
                speech_rate=speed,
                volume=50
            )

            audio = synthesizer.call(text)

            if audio is None:
                print("[Error] Dashscope TTS 未生成音频", file=sys.stderr)
                return None

            # 保存
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(audio)

            # 获取时长
            duration = self._get_audio_duration(output_path)
            print(f"  语音时长: {duration}s")

            return output_path

        except Exception as e:
            error_msg = str(e)
            # 解析常见错误
            if "418" in error_msg or "InvalidParameter" in error_msg:
                print(f"[Error] Dashscope 音色 '{voice_id}' 无效或不可用。请检查: 1) 音色名称是否正确 2) API Key 是否有权限", file=sys.stderr)
            else:
                print(f"[Error] Dashscope TTS 失败: {e}", file=sys.stderr)
            return None

    def _get_audio_duration(self, audio_path: str) -> float:
        """获取音频时长"""

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

    def get_available_voices(self) -> List[Dict]:
        """获取可用语音列表"""

        voices = []
        # 合并所有音色
        all_voices = {**self.CHINESE_VOICES, **self.OTHER_VOICES}

        for name, desc in all_voices.items():
            voices.append({
                "name": name,
                "description": desc,
                "language": "zh",
            })

        return voices


class MossTTSProvider(TTSProvider):
    """MOSS-TTS 提供者 (studio.mosi.cn)

    支持通过自然语言指令控制语音风格，如"一个御姐充满妩媚而又有磁性的声音"。

    API 文档: https://studio.mosi.cn/docs/voice-generator
    """

    API_URL = "https://studio.mosi.cn/api/v1/audio/speech"
    MODEL = "moss-voice-generator"

    # 预设语音风格指令
    VOICE_INSTRUCTIONS = {
        "default": "一个自然、流畅的声音",
        "female_gentle": "一个温柔的女声",
        "female_mature": "一个御姐充满妩媚而又有磁性的声音",
        "male_deep": "一个沉稳、有磁性的男声",
        "young_energetic": "一个年轻活力的声音",
        "storyteller": "一个讲故事的声音，富有感染力",
        "news_anchor": "一个新闻播报的声音，专业沉稳",
        "cute": "一个可爱活泼的声音",
        "sad": "一个悲伤、情感充沛的声音",
        "happy": "一个开心、愉悦的声音",
    }

    # 默认采样参数
    DEFAULT_SAMPLING_PARAMS = {
        "temperature": 1.5,
        "top_p": 0.6,
        "top_k": 50,
    }

    def __init__(self, api_key: str = None):
        # 动态读取环境变量，而不是使用 config.py 的静态值
        self.api_key = api_key or os.environ.get("MOSS_API_KEY", "") or MOSS_API_KEY

    def synthesize(
        self,
        text: str,
        output_path: str,
        voice: str = "default",
        speed: float = 1.0,
        instruction: str = None,
        sampling_params: dict = None,
    ) -> Optional[str]:
        """使用 MOSS-TTS 合成语音

        Args:
            text: 要转换的文本
            output_path: 输出文件路径
            voice: 语音风格名称 (default/female_gentle/female_mature 等)
            speed: 语速 (MOSS-TTS 不直接支持，可通过 instruction 调整)
            instruction: 自定义语音指令（如 "一个温柔的女声，语速稍快"）
            sampling_params: 自定义采样参数

        Returns:
            str: 输出文件路径，失败返回 None
        """
        if not self.api_key:
            print("[Error] MOSS_API_KEY 未设置", file=sys.stderr)
            return None

        if not text:
            print("[Error] 文本为空", file=sys.stderr)
            return None

        # 确定指令
        if instruction is None:
            instruction = self.VOICE_INSTRUCTIONS.get(voice, self.VOICE_INSTRUCTIONS["default"])

            # 语速调整
            if speed > 1.2:
                instruction += "，语速稍快"
            elif speed < 0.8:
                instruction += "，语速稍慢"

        # 合并采样参数
        params = {**self.DEFAULT_SAMPLING_PARAMS}
        if sampling_params:
            params.update(sampling_params)

        print(f"[MossTTS] 生成语音: {text[:30]}...")
        print(f"  模型: {self.MODEL}, 指令: {instruction}")

        try:
            import requests

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.MODEL,
                "text": text,
                "instruction": instruction,
                "sampling_params": params,
            }

            response = requests.post(
                self.API_URL,
                headers=headers,
                json=payload,
                timeout=60,
            )

            if response.status_code != 200:
                print(f"[Error] MOSS-TTS API 返回错误: {response.status_code} - {response.text}", file=sys.stderr)
                return None

            # 解析 JSON 响应，提取 base64 音频数据
            try:
                result = response.json()
                audio_data = result.get("audio_data")
                if not audio_data:
                    print(f"[Error] MOSS-TTS 返回无音频数据", file=sys.stderr)
                    return None

                # Base64 解码
                import base64
                audio_bytes = base64.b64decode(audio_data)

            except (json.JSONDecodeError, base64.binascii.Error) as e:
                print(f"[Error] MOSS-TTS 响应解析失败: {e}", file=sys.stderr)
                return None

            # MOSS-TTS 返回 WAV 格式，建议保存为 .wav
            if not output_path.endswith(".wav"):
                output_path = output_path.replace(".mp3", ".wav")

            # 保存音频
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(audio_bytes)

            # 获取时长
            duration = self._get_audio_duration(output_path)
            print(f"  语音时长: {duration}s")

            return output_path

        except ImportError:
            print("[Error] requests 未安装，请运行: pip install requests", file=sys.stderr)
            return None
        except Exception as e:
            print(f"[Error] MOSS-TTS 失败: {e}", file=sys.stderr)
            return None

    def _get_audio_duration(self, audio_path: str) -> float:
        """获取音频时长"""

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

    def get_available_voices(self) -> List[Dict]:
        """获取可用语音列表"""

        voices = []
        for name, instruction in self.VOICE_INSTRUCTIONS.items():
            voices.append({
                "name": name,
                "description": instruction,
                "language": "zh",
            })

        return voices


class CosyVoiceLocalProvider(TTSProvider):
    """本地 CosyVoice 模型提供者 (Fun-CosyVoice3)

    支持中文、英文、日语等多语言，支持音色克隆。
    需要预先下载模型文件到本地。

    官方文档: https://funaudiollm.github.io/cosyvoice3/
    """

    # 模型路径配置
    DEFAULT_MODEL_DIR = "pretrained_models/Fun-CosyVoice3-0.5B"
    DEFAULT_REFERENCE_AUDIO = "asset/zero_shot_prompt.wav"  # 模型内置参考音频

    # 支持的语言/风格指令 (参考 cosyvoice/utils/common.py#L28)
    INSTRUCT_OPTIONS = {
        "normal": "You are a helpful assistant.<|endofprompt|>",
        "guangdong": "You are a helpful assistant. 请用广东话表达。<|endofprompt|>",
        "dongbei": "You are a helpful assistant. 请用东北话表达。<|endofprompt|>",
        "sichuan": "You are a helpful assistant. 请用四川话表达。<|endofprompt|>",
        "fast": "You are a helpful assistant. 请用尽可能快地语速说一句话。<|endofprompt|>",
        "slow": "You are a helpful assistant. 请用慢一点的语速说话。<|endofprompt|>",
        "happy": "You are a helpful assistant. 请用开心的语气说话。<|endofprompt|>",
        "sad": "You are a helpful assistant. 请用悲伤的语气说话。<|endofprompt|>",
    }

    # 细粒度控制标记 (参考 cosyvoice/tokenizer/tokenizer.py#L280)
    CONTROL_TAGS = {
        "breath": "[breath]",  # 呼吸停顿
        "emphasis": "[emphasis]",  # 强调
    }

    def __init__(self, model_dir: str = None, cosyvoice_path: str = None):
        """初始化 CosyVoice 本地模型

        Args:
            model_dir: 模型目录路径，默认 pretrained_models/Fun-CosyVoice3-0.5B
            cosyvoice_path: CosyVoice 代码目录路径
        """
        self.model_dir = model_dir or self.DEFAULT_MODEL_DIR
        self.cosyvoice_path = cosyvoice_path
        self._cosyvoice = None
        self._sample_rate = 24000  # 默认采样率
        self._initialized = False
        self._init_error = None

    def _lazy_init(self):
        """延迟初始化（首次使用时才加载模型）"""
        if self._initialized:
            return self._cosyvoice is not None

        self._initialized = True

        try:
            import torchaudio

            # 确定 CosyVoice 代码路径
            if self.cosyvoice_path:
                cosyvoice_root = Path(self.cosyvoice_path)
            else:
                # 尝试多个可能的位置
                possible_paths = [
                    Path(__file__).parent.parent / "CosyVoice",
                    Path(__file__).parent.parent / "cosyvoice",
                    Path.cwd() / "CosyVoice",
                    Path.cwd() / "cosyvoice",
                ]
                cosyvoice_root = None
                for p in possible_paths:
                    if p.exists():
                        cosyvoice_root = p
                        break

            if cosyvoice_root is None or not cosyvoice_root.exists():
                self._init_error = f"CosyVoice 代码目录不存在，请确保已克隆 CosyVoice 仓库"
                print(f"[Warning] {self._init_error}", file=sys.stderr)
                return False

            # 添加 Matcha-TTS 到 sys.path (必须在 CosyVoice 之前)
            matcha_path = cosyvoice_root / "third_party" / "Matcha-TTS"
            if matcha_path.exists():
                sys.path.insert(0, str(matcha_path))

            # 添加 CosyVoice 到 sys.path
            sys.path.insert(0, str(cosyvoice_root))

            # 导入 AutoModel
            from cosyvoice.cli.cosyvoice import AutoModel

            # 确定模型路径
            model_path = Path(self.model_dir)
            if not model_path.exists():
                # 尝试相对于 CosyVoice 目录
                model_path = cosyvoice_root / self.model_dir
            if not model_path.exists():
                # 尝试相对于项目根目录
                model_path = Path(__file__).parent.parent / self.model_dir

            if not model_path.exists():
                self._init_error = f"模型目录不存在: {self.model_dir}"
                print(f"[Warning] {self._init_error}", file=sys.stderr)
                return False

            print(f"[CosyVoice] 加载模型: {model_path}")
            self._cosyvoice = AutoModel(model_dir=str(model_path))
            self._sample_rate = self._cosyvoice.sample_rate
            print(f"[CosyVoice] 模型加载成功，采样率: {self._sample_rate}")
            return True

        except ImportError as e:
            self._init_error = f"CosyVoice 导入失败: {e}"
            print(f"[Warning] {self._init_error}", file=sys.stderr)
            return False
        except Exception as e:
            self._init_error = f"CosyVoice 加载失败: {e}"
            print(f"[Warning] {self._init_error}", file=sys.stderr)
            return False

    def synthesize(
        self,
        text: str,
        output_path: str,
        voice: str = None,
        speed: float = 1.0,
        reference_audio: str = None,
        instruct: str = None,
    ) -> Optional[str]:
        """使用 CosyVoice 合成语音 (inference_instruct2)

        Args:
            text: 要转换的文本
            output_path: 输出文件路径 (建议 .wav 格式)
            voice: 语音风格 (normal/guangdong/dongbei/sichuan/fast/slow/happy/sad)
            speed: 语速 (暂不支持，保留参数)
            reference_audio: 参考音频路径（用于音色克隆）
            instruct: 自定义指令文本

        Returns:
            str: 输出文件路径，失败返回 None
        """
        # 延迟初始化
        if not self._lazy_init():
            print(f"[Error] {self._init_error}", file=sys.stderr)
            return None

        if not text:
            print("[Error] 文本为空", file=sys.stderr)
            return None

        try:
            import torchaudio

            print(f"[CosyVoice] 生成语音: {text[:50]}...")

            # 获取参考音频路径
            ref_audio = self._get_reference_audio(reference_audio)
            if ref_audio is None:
                return None

            # 构建指令文本
            if instruct is None:
                voice_style = voice or "normal"
                instruct = self.INSTRUCT_OPTIONS.get(voice_style, self.INSTRUCT_OPTIONS["normal"])

            # 使用 inference_instruct2 方法
            result = None
            for i, j in enumerate(self._cosyvoice.inference_instruct2(
                text, instruct, ref_audio, stream=False
            )):
                result = j
                break  # 只取第一个结果

            if result is None or 'tts_speech' not in result:
                print("[Error] CosyVoice 未生成音频", file=sys.stderr)
                return None

            # 保存音频
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            torchaudio.save(output_path, result['tts_speech'], self._sample_rate)

            # 获取时长
            duration = result['tts_speech'].shape[-1] / self._sample_rate
            print(f"  语音时长: {duration:.2f}s")

            return output_path

        except Exception as e:
            print(f"[Error] CosyVoice 生成失败: {e}", file=sys.stderr)
            return None

    def synthesize_zero_shot(
        self,
        text: str,
        output_path: str,
        prompt_text: str,
        reference_audio: str,
    ) -> Optional[str]:
        """零样本音色克隆 (inference_zero_shot)

        Args:
            text: 要转换的文本
            output_path: 输出文件路径
            prompt_text: 参考音频对应的文本内容
            reference_audio: 参考音频路径

        Returns:
            str: 输出文件路径，失败返回 None
        """
        if not self._lazy_init():
            print(f"[Error] {self._init_error}", file=sys.stderr)
            return None

        try:
            import torchaudio

            print(f"[CosyVoice] 零样本克隆: {text[:30]}...")

            # 构建指令格式
            instruct = f"You are a helpful assistant.<|endofprompt|>{prompt_text}"

            ref_audio = self._get_reference_audio(reference_audio)
            if ref_audio is None:
                return None

            result = None
            for i, j in enumerate(self._cosyvoice.inference_zero_shot(
                text, instruct, ref_audio, stream=False
            )):
                result = j
                break

            if result is None or 'tts_speech' not in result:
                print("[Error] CosyVoice 未生成音频", file=sys.stderr)
                return None

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            torchaudio.save(output_path, result['tts_speech'], self._sample_rate)

            duration = result['tts_speech'].shape[-1] / self._sample_rate
            print(f"  语音时长: {duration:.2f}s")

            return output_path

        except Exception as e:
            print(f"[Error] CosyVoice 零样本克隆失败: {e}", file=sys.stderr)
            return None

    def synthesize_cross_lingual(
        self,
        text: str,
        output_path: str,
        reference_audio: str = None,
    ) -> Optional[str]:
        """跨语言/细粒度控制合成 (inference_cross_lingual)

        支持 [breath] 等控制标记来添加自然停顿。

        Args:
            text: 要转换的文本，可包含 [breath] 等控制标记
            output_path: 输出文件路径
            reference_audio: 参考音频路径

        Returns:
            str: 输出文件路径，失败返回 None
        """
        if not self._lazy_init():
            print(f"[Error] {self._init_error}", file=sys.stderr)
            return None

        try:
            import torchaudio

            print(f"[CosyVoice] 跨语言合成: {text[:50]}...")

            ref_audio = self._get_reference_audio(reference_audio)
            if ref_audio is None:
                return None

            # 构建指令格式
            instruct = "You are a helpful assistant.<|endofprompt|>"

            result = None
            for i, j in enumerate(self._cosyvoice.inference_cross_lingual(
                instruct + text, ref_audio, stream=False
            )):
                result = j
                break

            if result is None or 'tts_speech' not in result:
                print("[Error] CosyVoice 未生成音频", file=sys.stderr)
                return None

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            torchaudio.save(output_path, result['tts_speech'], self._sample_rate)

            duration = result['tts_speech'].shape[-1] / self._sample_rate
            print(f"  语音时长: {duration:.2f}s")

            return output_path

        except Exception as e:
            print(f"[Error] CosyVoice 跨语言合成失败: {e}", file=sys.stderr)
            return None

    def _get_reference_audio(self, reference_audio: str = None) -> Optional[str]:
        """获取参考音频路径"""
        if reference_audio:
            if Path(reference_audio).exists():
                return reference_audio
            print(f"[Warning] 参考音频不存在: {reference_audio}", file=sys.stderr)

        # 使用模型内置参考音频
        # 先尝试相对于模型目录
        model_path = Path(self.model_dir)
        if not model_path.exists():
            model_path = Path(__file__).parent.parent / self.model_dir

        ref_path = model_path / self.DEFAULT_REFERENCE_AUDIO
        if ref_path.exists():
            return str(ref_path)

        # 尝试相对于 CosyVoice 目录
        if self.cosyvoice_path:
            ref_path = Path(self.cosyvoice_path) / self.DEFAULT_REFERENCE_AUDIO
            if ref_path.exists():
                return str(ref_path)

        # 尝试当前工作目录
        ref_path = Path.cwd() / self.DEFAULT_REFERENCE_AUDIO
        if ref_path.exists():
            return str(ref_path)

        print(f"[Warning] 参考音频不存在: {self.DEFAULT_REFERENCE_AUDIO}", file=sys.stderr)
        return None

    def get_available_voices(self) -> List[Dict]:
        """获取可用语音列表"""

        voices = []
        for name, instruct in self.INSTRUCT_OPTIONS.items():
            desc = instruct.replace("You are a helpful assistant.", "").replace("<|endofprompt|>", "").strip()
            voices.append({
                "name": name,
                "description": desc or "默认风格",
                "language": "multi",
            })

        return voices


# ── TTS 工厂 ──

def get_tts_provider(provider_name: str = "edge", model_dir: str = None, cosyvoice_path: str = None) -> TTSProvider:
    """获取 TTS 提供者

    Args:
        provider_name: 提供者名称 (edge/dashscope/cosyvoice)
        model_dir: CosyVoice 模型目录路径 (可选，默认从环境变量读取)
        cosyvoice_path: CosyVoice 代码目录路径 (可选)

    Returns:
        TTSProvider 实例
    """
    providers = {
        "edge": EdgeTTSProvider,
        "dashscope": DashscopeTTSProvider,
        "moss": MossTTSProvider,
        "cosyvoice": CosyVoiceLocalProvider,
    }

    provider_class = providers.get(provider_name)

    if provider_class is None:
        print(f"[Warning] 未知的 TTS 提供者: {provider_name}, 使用 edge", file=sys.stderr)
        return EdgeTTSProvider()

    # CosyVoice 支持自定义模型路径
    if provider_name == "cosyvoice":
        # 从环境变量读取配置
        env_model_dir = os.environ.get("COSYVOICE_MODEL_DIR", "")
        env_cosyvoice_path = os.environ.get("COSYVOICE_PATH", "")

        return CosyVoiceLocalProvider(
            model_dir=model_dir or env_model_dir or "pretrained_models/Fun-CosyVoice3-0.5B",
            cosyvoice_path=cosyvoice_path or env_cosyvoice_path or None
        )

    return provider_class()


def synthesize_text(
    text: str,
    output_path: str,
    provider: str = "edge",
    voice: str = None,
    speed: float = 1.0,
    instruction: str = None,
    model_dir: str = None,
    cosyvoice_path: str = None,
) -> Optional[str]:
    """合成语音（便捷函数）

    Args:
        text: 要转换的文本
        output_path: 输出文件路径
        provider: TTS 提供者 (edge/dashscope/moss/cosyvoice)
        voice: 语音名称
        speed: 语速
        instruction: MOSS-TTS 语音指令（由大模型生成）
        model_dir: CosyVoice 模型目录路径 (可选)
        cosyvoice_path: CosyVoice 代码目录路径 (可选)

    Returns:
        str: 输出文件路径，失败返回 None
    """
    tts = get_tts_provider(provider, model_dir, cosyvoice_path)

    # 默认语音选择
    if voice is None:
        if provider == "edge":
            voice = "zh-CN-XiaoxiaoNeural"
        elif provider == "cosyvoice":
            voice = "normal"
        elif provider == "moss":
            voice = "default"
        else:
            voice = DEFAULT_VOICE

    # MOSS-TTS 使用 instruction 参数
    if provider == "moss":
        return tts.synthesize(text, output_path, voice, speed, instruction=instruction)

    return tts.synthesize(text, output_path, voice, speed)


def main():
    parser = argparse.ArgumentParser(description="TTS 提供者模块")
    parser.add_argument("--provider", default="edge", choices=["edge", "dashscope", "moss", "cosyvoice"],
                        help="TTS 提供者")
    parser.add_argument("--text", required=True, help="要转换的文本")
    parser.add_argument("--output", default="tts_output.mp3", help="输出文件路径")
    parser.add_argument("--voice", default=None, help="语音选择")
    parser.add_argument("--speed", type=float, default=1.0, help="语速")
    parser.add_argument("--instruction", default=None, help="MOSS-TTS 语音指令")
    parser.add_argument("--list-voices", action="store_true", help="列出可用语音")
    args = parser.parse_args()

    if args.list_voices:
        tts = get_tts_provider(args.provider)
        voices = tts.get_available_voices()
        print(json.dumps(voices, ensure_ascii=False, indent=2))
        return

    result = synthesize_text(
        args.text,
        args.output,
        args.provider,
        args.voice,
        args.speed,
        instruction=args.instruction,
    )

    if result:
        print(f"输出: {result}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()