#!/usr/bin/env python3
"""
WebSocket 服务 — 实时进度推送

支持：
1. Redis pub/sub 订阅
2. WebSocket 连接管理
3. 进度推送
"""

import asyncio
import json
import os
from typing import Dict, Set
import redis

try:
    from flask_sock import Sock
    SOCK_AVAILABLE = True
except ImportError:
    SOCK_AVAILABLE = False

from celeryconfig import broker_url
from core.logging_config import get_logger

logger = get_logger("websocket")


# Redis pub/sub 客户端
redis_client = redis.from_url(broker_url)

# WebSocket 连接管理
connections: Dict[str, Set] = {}  # session_id -> set of websocket connections


def setup_websocket(app):
    """设置 WebSocket 服务

    Args:
        app: Flask app
    """
    if not SOCK_AVAILABLE:
        logger.warning("flask_sock 不可用，WebSocket 功能禁用")
        return

    sock = Sock(app)

    @sock.route("/ws/progress/<session_id>")
    def progress_ws(ws, session_id):
        """进度 WebSocket 路由

        Args:
            ws: WebSocket 连接
            session_id: Session ID
        """
        logger.info(f"WebSocket 连接: session={session_id}")

        # 注册连接
        if session_id not in connections:
            connections[session_id] = set()
        connections[session_id].add(ws)

        try:
            # 启动 Redis pub/sub 监听
            pubsub = redis_client.pubsub()
            channel = f"emotion_video:progress:{session_id}"
            pubsub.subscribe(channel)

            # 监听消息
            for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    ws.send(json.dumps(data, ensure_ascii=False))

                    # 如果是最终完成消息，关闭连接
                    if data.get("status") == "completed":
                        logger.info(f"任务完成，关闭 WebSocket: session={session_id}")
                        break

        except Exception as e:
            logger.error(f"WebSocket 错误: {e}")

        finally:
            # 清理连接
            if session_id in connections:
                connections[session_id].discard(ws)
                if not connections[session_id]:
                    del connections[session_id]

            pubsub.unsubscribe(channel)
            pubsub.close()
            ws.close()


async def listen_progress_async(session_id: str, callback):
    """异步监听进度

    Args:
        session_id: Session ID
        callback: 回调函数
    """
    pubsub = redis_client.pubsub()
    channel = f"emotion_video:progress:{session_id}"
    pubsub.subscribe(channel)

    try:
        for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                callback(data)

                if data.get("status") == "completed":
                    break

    finally:
        pubsub.unsubscribe(channel)
        pubsub.close()


def broadcast_progress(session_id: str, message: Dict):
    """广播进度到所有连接

    Args:
        session_id: Session ID
        message: 进度消息
    """
    if session_id in connections:
        for ws in connections[session_id]:
            try:
                ws.send(json.dumps(message, ensure_ascii=False))
            except Exception as e:
                logger.warning(f"发送失败: {e}")