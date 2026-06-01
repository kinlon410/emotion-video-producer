#!/usr/bin/env python3
"""
Celery 配置 — 异步任务队列
"""

import os

# Redis 配置
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Celery 配置
broker_url = REDIS_URL
result_backend = REDIS_URL

# 任务配置
task_serializer = "json"
accept_content = ["json"]
result_serializer = "json"
timezone = "Asia/Shanghai"
enable_utc = True

# Worker 配置
worker_prefetch_multiplier = 1
worker_max_tasks_per_child = 100

# 任务结果过期时间（秒）
result_expires = 3600

# 任务路由（可选）
task_routes = {
    "tasks.produce_video_task": {"queue": "video"},
    "tasks.download_visual_task": {"queue": "download"},
}

# 任务优先级
task_default_priority = 10