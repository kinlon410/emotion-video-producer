#!/usr/bin/env python3
"""
Celery Tasks — 异步视频生产任务

支持：
1. produce_video_task — 完整视频生产
2. redo_from_step_task — 从指定步骤重新执行
3. 进度推送 — Redis pub/sub
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

from celery import Celery
from celery.result import AsyncResult
import redis

from celeryconfig import broker_url, result_backend
from agent.orchestrator import get_orchestrator
from agent.schemas import SessionState
from core.logging_config import get_logger

logger = get_logger("tasks")


# Celery app
app = Celery("emotion_video", broker=broker_url, backend=result_backend)
app.config_from_object("celeryconfig")

# Redis pub/sub client
redis_client = redis.from_url(broker_url)


def publish_progress(session_id: str, step: int, step_name: str, status: str, result: Dict = None, message: str = None):
    """发布进度到 Redis pub/sub

    Args:
        session_id: Session ID
        step: 步骤编号
        step_name: 步骤名称
        status: 状态 (started, completed, failed)
        result: 步骤结果（可选）
        message: 进度消息（可选）
    """
    # 根据步骤生成消息
    if message is None:
        step_messages = {
            0: "开始生产",
            1: "音乐情感分析完成",
            2: "AI 叙事生成完成",
            3: "视觉素材下载完成",
            4: "TTS 语音合成完成",
            5: "字幕同步完成",
            6: "视频渲染完成",
            9: "生产完成",
        }
        message = step_messages.get(step, step_name)

    message_data = {
        "session_id": session_id,
        "step": step,
        "step_name": step_name,
        "status": status,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
        "result": result,
    }

    channel = f"emotion_video:progress:{session_id}"
    redis_client.publish(channel, json.dumps(message_data, ensure_ascii=False))

    logger.info(f"发布进度: {channel} step={step} status={status}")


@app.task(bind=True, name="tasks.produce_video_task")
def produce_video_task(
    self,
    theme: str,
    bgm_path: str,
    output_path: str = None,
    style: str = None,
    voice: str = "longxiaochun",
    tts_speed: float = 1.0,
    visual_mode: str = "auto",
    style_profile: Dict = None
) -> Dict[str, Any]:
    """异步视频生产任务

    Args:
        theme: 视频主题
        bgm_path: BGM 路径
        output_path: 输出路径（可选）
        style: 风格预设
        voice: TTS 语音
        tts_speed: TTS 语速
        visual_mode: 素材获取模式
        style_profile: 风格分析结果

    Returns:
        生产结果字典
    """
    orchestrator = get_orchestrator()

    # 创建 Session
    session_id = orchestrator.create_session(theme, bgm_path, style, output_path)
    task_id = self.request.id

    # 定义进度回调
    def progress_callback(step: int, step_name: str, result: Dict):
        publish_progress(session_id, step, step_name, "completed", result)

    # 发布开始进度
    publish_progress(session_id, 0, "start", "started")

    try:
        # 执行流程（async）
        result = asyncio.run(orchestrator.run_pipeline_async(
            session_id,
            voice=voice,
            tts_speed=tts_speed,
            visual_mode=visual_mode,
            style_profile=style_profile,
            progress_callback=progress_callback
        ))

        # 发布完成进度
        publish_progress(session_id, 9, "render", "completed", result)

        return {
            "success": True,
            "session_id": session_id,
            "output_path": result.get("output_path"),
            "task_id": task_id,
        }

    except Exception as e:
        logger.error(f"任务失败: {e}")
        publish_progress(session_id, 0, "error", "failed", {"error": str(e)})
        return {
            "success": False,
            "session_id": session_id,
            "error": str(e),
            "task_id": task_id,
        }


@app.task(bind=True, name="tasks.redo_from_step_task")
def redo_from_step_task(
    self,
    session_id: str,
    target_step: int,
    voice: str = "longxiaochun",
    tts_speed: float = 1.0,
    visual_mode: str = "auto",
    style_profile: Dict = None
) -> Dict[str, Any]:
    """从指定步骤重新执行

    Args:
        session_id: Session ID
        target_step: 目标步骤
        其他参数同 produce_video_task

    Returns:
        生产结果字典
    """
    orchestrator = get_orchestrator()
    task_id = self.request.id

    # 定义进度回调
    def progress_callback(step: int, step_name: str, result: Dict):
        publish_progress(session_id, step, step_name, "completed", result)

    try:
        result = asyncio.run(orchestrator.redo_from_step_async(
            session_id,
            target_step,
            voice=voice,
            tts_speed=tts_speed,
            visual_mode=visual_mode,
            style_profile=style_profile,
            progress_callback=progress_callback
        ))

        return {
            "success": True,
            "session_id": session_id,
            "output_path": result.get("output_path"),
            "task_id": task_id,
        }

    except Exception as e:
        logger.error(f"重做任务失败: {e}")
        return {
            "success": False,
            "session_id": session_id,
            "error": str(e),
            "task_id": task_id,
        }


@app.task(name="tasks.download_visual_task")
def download_visual_task(visual_queries: List[Dict], output_dir: str, visual_mode: str = "auto") -> Dict[str, str]:
    """异步下载视觉素材

    Args:
        visual_queries: 视觉查询列表
        output_dir: 输出目录
        visual_mode: 素材获取模式

    Returns:
        素材片段路径字典
    """
    from core_async.visual_downloader import download_visuals_async

    result = asyncio.run(download_visuals_async(visual_queries, output_dir, visual_mode))
    return result


def get_task_status(task_id: str) -> Dict[str, Any]:
    """获取任务状态

    Args:
        task_id: 任务 ID

    Returns:
        任务状态字典
    """
    result = AsyncResult(task_id, app=app)

    status = {
        "task_id": task_id,
        "status": result.state,
        "result": None,
        "error": None,
    }

    if result.ready():
        if result.successful():
            status["result"] = result.result
        else:
            status["error"] = str(result.result)

    return status


# 导入 List 类型
from typing import List