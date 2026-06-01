#!/usr/bin/env python3
"""
Tool 输入 Schema — Pydantic 模型定义
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator


class AnalyzeInput(BaseModel):
    """音乐分析 Tool 输入"""
    bgm_path: str = Field(..., description="BGM 音频文件路径")
    output_json: Optional[str] = Field(None, description="输出 JSON 文件路径")


class NarrativeInput(BaseModel):
    """叙事生成 Tool 输入"""
    theme: str = Field(..., description="视频主题")
    analysis: Dict[str, Any] = Field(..., description="音乐分析结果")
    style: Optional[str] = Field(None, description="风格预设")
    output_json: Optional[str] = Field(None, description="输出 JSON 文件路径")


class VisualSelectInput(BaseModel):
    """视觉选择 Tool 输入"""
    analysis: Dict[str, Any] = Field(..., description="音乐分析结果")
    segment_count: int = Field(7, description="目标片段数量", ge=3, le=15)
    output_json: Optional[str] = Field(None, description="输出 JSON 文件路径")


class TransitionInput(BaseModel):
    """转场映射 Tool 输入"""
    analysis: Dict[str, Any] = Field(..., description="音乐分析结果")
    visuals: List[Dict[str, Any]] = Field(..., description="视觉选择结果")
    output_json: Optional[str] = Field(None, description="输出 JSON 文件路径")


class TTSInput(BaseModel):
    """TTS Tool 输入"""
    text: str = Field(..., description="要转换的文本")
    output_path: str = Field(..., description="输出文件路径")
    voice: str = Field("longxiaochun", description="语音名称")
    speed: float = Field(1.0, description="语速", ge=0.5, le=2.0)


class ASRInput(BaseModel):
    """ASR Tool 输入"""
    audio_path: str = Field(..., description="音频文件路径")
    language: str = Field("zh", description="语言")
    output_json: Optional[str] = Field(None, description="输出 JSON 文件路径")


class SubtitleInput(BaseModel):
    """字幕同步 Tool 输入"""
    analysis: Dict[str, Any] = Field(..., description="音乐分析结果")
    narrative: Dict[str, Any] = Field(..., description="叙事结果")
    narration_duration: Optional[float] = Field(None, description="旁白时长")
    asr_result: Optional[Dict[str, Any]] = Field(None, description="ASR 结果")
    output_json: Optional[str] = Field(None, description="输出 JSON 文件路径")


class VisualDownloadInput(BaseModel):
    """视觉素材下载 Tool 输入"""
    visual_queries: List[Dict[str, Any]] = Field(..., description="视觉查询列表")
    output_dir: str = Field(..., description="输出目录")
    visual_mode: str = Field("auto", description="素材获取模式")


class RenderInput(BaseModel):
    """视频渲染 Tool 输入"""
    title_text: str = Field(..., description="标题文本")
    bgm_path: str = Field(..., description="BGM 文件路径")
    narration_path: Optional[str] = Field(None, description="旁白文件路径")
    clips: Dict[str, str] = Field(..., description="素材片段路径")
    transitions: List[Dict[str, Any]] = Field(..., description="转场配置")
    subtitles: List[Dict[str, Any]] = Field(..., description="字幕配置")
    output_path: str = Field(..., description="输出视频路径")
    width: int = Field(1920, description="视频宽度")
    height: int = Field(1080, description="视频高度")
    fps: int = Field(30, description="帧率")


class SessionState(BaseModel):
    """Session 状态"""
    session_id: str = Field(..., description="Session ID")
    theme: str = Field(..., description="视频主题")
    bgm_path: str = Field(..., description="BGM 路径")
    style: Optional[str] = Field(None, description="风格预设")
    current_step: int = Field(0, description="当前步骤编号")
    completed_steps: List[int] = Field(default_factory=list, description="已完成步骤列表")
    work_dir: Optional[str] = Field(None, description="工作目录")
    created_at: Optional[str] = Field(None, description="创建时间")
    updated_at: Optional[str] = Field(None, description="更新时间")

    # 各步骤结果缓存
    analysis: Optional[Dict[str, Any]] = Field(None, description="音乐分析结果")
    narrative: Optional[Dict[str, Any]] = Field(None, description="叙事结果")
    visuals: Optional[List[Dict[str, Any]]] = Field(None, description="视觉选择结果")
    transitions: Optional[List[Dict[str, Any]]] = Field(None, description="转场配置")
    subtitles: Optional[List[Dict[str, Any]]] = Field(None, description="字幕配置")
    narration_audio: Optional[str] = Field(None, description="旁白音频路径")
    clips: Optional[Dict[str, str]] = Field(None, description="素材片段路径")
    output_path: Optional[str] = Field(None, description="输出视频路径")


class SkillDefinition(BaseModel):
    """Skill 定义"""
    name: str = Field(..., description="Skill 名称")
    description: str = Field(..., description="Skill 描述")
    style: Optional[str] = Field(None, description="风格预设")
    visual_keywords: Optional[List[str]] = Field(None, description="视觉关键词列表")
    transition_params: Optional[Dict[str, Any]] = Field(None, description="转场参数")
    subtitle_style: Optional[Dict[str, Any]] = Field(None, description="字幕样式")
    music_tags: Optional[List[str]] = Field(None, description="音乐标签")
    created_at: Optional[str] = Field(None, description="创建时间")


class Checkpoint(BaseModel):
    """Checkpoint 定义"""
    step: int = Field(..., description="步骤编号")
    step_name: str = Field(..., description="步骤名称")
    timestamp: str = Field(..., description="时间戳")
    result: Dict[str, Any] = Field(..., description="步骤结果")


class StyleProfile(BaseModel):
    """风格分析结果"""
    sentence_structure: List[str] = Field(default_factory=list, description="句式特征")
    tone: str = Field(..., description="基调")
    vocabulary_level: str = Field(..., description="词汇等级")
    rhetorical_devices: List[str] = Field(default_factory=list, description="修辞手法")
    avg_sentence_length: float = Field(..., description="平均句子长度")
    emotion_intensity: float = Field(..., description="情感强度")
    style_prompt: str = Field(..., description="风格提示")