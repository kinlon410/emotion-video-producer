#!/usr/bin/env python3
"""
Session Store — Redis 存储的 Session 状态管理

支持：
1. Session CRUD
2. Checkpoint 管理
3. WorkDir 管理
4. 多 worker 共享
"""

import json
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import uuid

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from agent.schemas import SessionState, Checkpoint
from core.logging_config import get_logger
from core.exceptions import SessionNotFoundError, SessionExpiredError, CheckpointError

logger = get_logger("session_store")


class SessionStore:
    """Redis Session Store"""

    # Redis key prefix
    SESSION_PREFIX = "emotion_video:session:"
    CHECKPOINT_PREFIX = "emotion_video:checkpoint:"
    WORKDIR_PREFIX = "emotion_video:workdir:"

    # Session 过期时间（秒）
    SESSION_EXPIRE = 3600 * 24  # 24 小时

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """初始化 Session Store

        Args:
            redis_url: Redis 连接 URL
        """
        if REDIS_AVAILABLE:
            self.redis = redis.from_url(redis_url)
            logger.info(f"Session Store 连接 Redis: {redis_url}")
        else:
            # Fallback: 本地文件存储
            self.redis = None
            self.local_store_dir = Path(tempfile.gettempdir()) / "emotion_video_sessions"
            self.local_store_dir.mkdir(parents=True, exist_ok=True)
            logger.warning("Redis 不可用，使用本地文件存储（不支持多 worker）")

    def create_session(
        self,
        theme: str,
        bgm_path: str,
        style: str = None
    ) -> str:
        """创建新 Session

        Args:
            theme: 视频主题
            bgm_path: BGM 路径
            style: 风格预设

        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())[:8]
        work_dir = str(self._create_work_dir(session_id))
        now = datetime.utcnow().isoformat()

        state = SessionState(
            session_id=session_id,
            theme=theme,
            bgm_path=bgm_path,
            style=style,
            current_step=0,
            completed_steps=[],
            work_dir=work_dir,
            created_at=now,
            updated_at=now,
        )

        self._save_state(session_id, state.dict())
        logger.info(f"创建 Session: {session_id}, work_dir={work_dir}")
        return session_id

    def get_session(self, session_id: str) -> SessionState:
        """获取 Session 状态

        Args:
            session_id: Session ID

        Returns:
            SessionState 对象

        Raises:
            SessionNotFoundError: Session 不存在
            SessionExpiredError: Session 已过期
        """
        state_dict = self._load_state(session_id)

        if state_dict is None:
            raise SessionNotFoundError(f"Session 不存在: {session_id}")

        # 检查过期
        created_at = state_dict.get("created_at")
        if created_at:
            created = datetime.fromisoformat(created_at)
            if datetime.utcnow() - created > timedelta(seconds=self.SESSION_EXPIRE):
                raise SessionExpiredError(f"Session 已过期: {session_id}")

        return SessionState(**state_dict)

    def update_session(self, session_id: str, updates: Dict[str, Any]) -> SessionState:
        """更新 Session 状态

        Args:
            session_id: Session ID
            updates: 更新字段字典

        Returns:
            更新后的 SessionState
        """
        state = self.get_session(session_id)
        state_dict = state.dict()

        # 应用更新
        for key, value in updates.items():
            if key in state_dict:
                state_dict[key] = value

        state_dict["updated_at"] = datetime.utcnow().isoformat()
        self._save_state(session_id, state_dict)

        return SessionState(**state_dict)

    def save_checkpoint(
        self,
        session_id: str,
        step: int,
        step_name: str,
        result: Dict[str, Any]
    ) -> Checkpoint:
        """保存 Checkpoint

        Args:
            session_id: Session ID
            step: 步骤编号
            step_name: 步骤名称
            result: 步骤结果

        Returns:
            Checkpoint 对象
        """
        checkpoint = Checkpoint(
            step=step,
            step_name=step_name,
            timestamp=datetime.utcnow().isoformat(),
            result=result,
        )

        key = f"{self.CHECKPOINT_PREFIX}{session_id}:{step}"
        self._set_key(key, checkpoint.dict())

        # 更新 Session 的 completed_steps
        state = self.get_session(session_id)
        if step not in state.completed_steps:
            completed = state.completed_steps + [step]
            self.update_session(session_id, {"completed_steps": completed})

        logger.info(f"保存 Checkpoint: session={session_id}, step={step}")
        return checkpoint

    def get_checkpoint(self, session_id: str, step: int) -> Optional[Checkpoint]:
        """获取 Checkpoint

        Args:
            session_id: Session ID
            step: 步骤编号

        Returns:
            Checkpoint 对象，不存在返回 None
        """
        key = f"{self.CHECKPOINT_PREFIX}{session_id}:{step}"
        data = self._get_key(key)

        if data:
            return Checkpoint(**data)
        return None

    def restore_from_checkpoint(
        self,
        session_id: str,
        step: int
    ) -> Dict[str, Any]:
        """从 Checkpoint 恢复状态

        Args:
            session_id: Session ID
            step: 步骤编号

        Returns:
            Checkpoint 结果字典

        Raises:
            CheckpointError: Checkpoint 不存在
        """
        checkpoint = self.get_checkpoint(session_id, step)

        if checkpoint is None:
            raise CheckpointError(f"Checkpoint 不存在: session={session_id}, step={step}")

        # 更新 Session 当前步骤
        self.update_session(session_id, {"current_step": step})

        logger.info(f"从 Checkpoint 恢复: session={session_id}, step={step}")
        return checkpoint.result

    def get_work_dir(self, session_id: str) -> Path:
        """获取 Session 工作目录

        Args:
            session_id: Session ID

        Returns:
            工作目录 Path
        """
        state = self.get_session(session_id)
        return Path(state.work_dir)

    def cleanup_session(self, session_id: str):
        """清理 Session（删除工作目录和 Redis keys）

        Args:
            session_id: Session ID
        """
        # 删除工作目录
        work_dir = self.get_work_dir(session_id)
        if work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)
            logger.info(f"清理工作目录: {work_dir}")

        # 删除 Redis keys
        if self.redis:
            # Session key
            self.redis.delete(f"{self.SESSION_PREFIX}{session_id}")

            # Checkpoint keys
            for step in range(1, 10):
                self.redis.delete(f"{self.CHECKPOINT_PREFIX}{session_id}:{step}")

        logger.info(f"清理 Session: {session_id}")

    def _create_work_dir(self, session_id: str) -> Path:
        """创建工作目录

        Args:
            session_id: Session ID

        Returns:
            工作目录 Path
        """
        # 使用共享目录（支持多 worker）
        base_dir = Path(os.environ.get("EMOTION_VIDEO_SHARED_DIR", "/tmp/emotion_video_shared"))
        base_dir.mkdir(parents=True, exist_ok=True)

        work_dir = base_dir / session_id
        work_dir.mkdir(parents=True, exist_ok=True)

        return work_dir

    def _save_state(self, session_id: str, state_dict: Dict[str, Any]):
        """保存 Session 状态"""
        key = f"{self.SESSION_PREFIX}{session_id}"
        self._set_key(key, state_dict, expire=self.SESSION_EXPIRE)

    def _load_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """加载 Session 状态"""
        key = f"{self.SESSION_PREFIX}{session_id}"
        return self._get_key(key)

    def _set_key(self, key: str, value: Dict[str, Any], expire: int = None):
        """设置 Redis key"""
        if self.redis:
            data = json.dumps(value, ensure_ascii=False)
            if expire:
                self.redis.setex(key, expire, data)
            else:
                self.redis.set(key, data)
        else:
            # 本地文件存储
            file_path = self.local_store_dir / key.replace(":", "_") / "state.json"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(value, f, ensure_ascii=False, indent=2)

    def _get_key(self, key: str) -> Optional[Dict[str, Any]]:
        """获取 Redis key"""
        if self.redis:
            data = self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        else:
            # 本地文件存储
            file_path = self.local_store_dir / key.replace(":", "_") / "state.json"
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            return None


# 全局 Session Store 实例
_store = None


def get_session_store(redis_url: str = None) -> SessionStore:
    """获取 Session Store 实例

    Args:
        redis_url: Redis 连接 URL（可选，默认从环境变量读取）

    Returns:
        SessionStore 实例
    """
    global _store
    if _store is None:
        url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        _store = SessionStore(url)
    return _store