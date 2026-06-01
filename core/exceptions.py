#!/usr/bin/env python3
"""
自定义异常类 — 替代 catch-all except Exception
"""

class EmotionVideoError(Exception):
    """基础异常类"""
    pass


class APIError(EmotionVideoError):
    """API 调用错误"""
    pass


class TimeoutError(APIError):
    """API 超时"""
    pass


class RateLimitError(APIError):
    """API 速率限制"""
    pass


class JSONParseError(APIError):
    """JSON 解析失败"""
    pass


class AuthenticationError(APIError):
    """API 认证失败"""
    pass


class DownloadError(EmotionVideoError):
    """下载错误"""
    pass


class NetworkError(DownloadError):
    """网络连接错误"""
    pass


class ResourceNotFoundError(EmotionVideoError):
    """资源未找到"""
    pass


class AudioNotFoundError(ResourceNotFoundError):
    """音频文件未找到"""
    pass


class VisualNotFoundError(ResourceNotFoundError):
    """视觉素材未找到"""
    pass


class RenderError(EmotionVideoError):
    """渲染错误"""
    pass


class FFmpegError(RenderError):
    """FFmpeg 执行错误"""
    pass


class SessionError(EmotionVideoError):
    """Session 错误"""
    pass


class SessionNotFoundError(SessionError):
    """Session 未找到"""
    pass


class SessionExpiredError(SessionError):
    """Session 已过期"""
    pass


class CheckpointError(SessionError):
    """Checkpoint 错误"""
    pass


class TTSError(EmotionVideoError):
    """TTS 错误"""
    pass


class ASRError(EmotionVideoError):
    """ASR 错误"""
    pass


class StyleAnalysisError(EmotionVideoError):
    """风格分析错误"""
    pass


class SkillError(EmotionVideoError):
    """Skill 错误"""
    pass


class SkillNotFoundError(SkillError):
    """Skill 未找到"""
    pass


class SkillValidationError(SkillError):
    """Skill 验证失败"""
    pass


class TemplateError(EmotionVideoError):
    """模板错误"""
    pass


class TemplateNotFoundError(TemplateError):
    """模板未找到"""
    pass


class AssetError(EmotionVideoError):
    """素材错误"""
    pass


class AssetNotFoundError(AssetError):
    """素材未找到"""
    pass


class TranslationError(EmotionVideoError):
    """翻译错误"""
    pass