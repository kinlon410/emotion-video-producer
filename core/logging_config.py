#!/usr/bin/env python3
"""
日志配置 — 替代 print-based 日志
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


# 创建 logger
logger = logging.getLogger("emotion_video")


def setup_logging(log_level: str = "INFO", log_file: str = None):
    """配置日志

    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        log_file: 日志文件路径（可选）
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    # 格式化器
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s [%(name)s.%(funcName)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # 文件 handler（可选）
    file_handler = None
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)

    # 配置 root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    if file_handler:
        root_logger.addHandler(file_handler)

    return logger


def get_logger(name: str = None) -> logging.Logger:
    """获取 logger

    Args:
        name: 子模块名称（可选）

    Returns:
        Logger 实例
    """
    if name:
        return logging.getLogger(f"emotion_video.{name}")
    return logger


# 便捷函数
def debug(msg: str):
    logger.debug(msg)


def info(msg: str):
    logger.info(msg)


def warning(msg: str):
    logger.warn(msg)


def error(msg: str):
    logger.error(msg)


def critical(msg: str):
    logger.critical(msg)


# 初始化默认配置
setup_logging()