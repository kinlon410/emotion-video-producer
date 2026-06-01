#!/usr/bin/env python3
"""
Async 视觉素材下载器 — asyncio 并行下载

支持：
1. 并行下载多个素材片段
2. Pexels/Pixabay/Coverr 多源
3. 进度通知
"""

import asyncio
import aiohttp
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any

from core.logging_config import get_logger
from core.exceptions import DownloadError, NetworkError, VisualNotFoundError
from config import PEXELS_API_KEY, PIXABAY_API_KEY, DOWNLOAD_TIMEOUT, DOWNLOAD_RETRIES

logger = get_logger("visual_downloader")


async def download_visuals_async(
    visual_queries: List[Dict[str, Any]],
    output_dir: str,
    visual_mode: str = "auto"
) -> Dict[str, str]:
    """异步并行下载视觉素材

    Args:
        visual_queries: 视觉查询列表 [{id, keyword, duration}]
        output_dir: 输出目录
        visual_mode: 素材获取模式

    Returns:
        素材片段路径字典 {segment_id: file_path}
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 并行下载所有片段
    tasks = []
    for query in visual_queries:
        task = download_single_clip_async(
            query["id"],
            query["keyword"],
            query["duration"],
            output_dir,
            visual_mode
        )
        tasks.append(task)

    # 执行并行下载
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 整理结果
    clips = {}
    for i, result in enumerate(results):
        query = visual_queries[i]
        if isinstance(result, Exception):
            logger.warning(f"片段 {query['id']} 下载失败: {result}")
            # 生成背景图片作为 fallback
            clips[query["id"]] = _generate_background(query["id"], output_dir)
        else:
            clips[query["id"]] = result

    return clips


async def download_single_clip_async(
    segment_id: str,
    keyword: str,
    duration: float,
    output_dir: str,
    visual_mode: str = "auto"
) -> str:
    """异步下载单个素材片段

    Args:
        segment_id: 片段 ID
        keyword: 搜索关键词
        duration: 目标时长
        output_dir: 输出目录
        visual_mode: 素材获取模式

    Returns:
        下载文件路径
    """
    output_path = os.path.join(output_dir, f"{segment_id}.mp4")

    # 尝试多个源
    sources = _get_sources(visual_mode)

    for source in sources:
        try:
            video_url = await _search_video_async(source, keyword, duration)
            if video_url:
                await _download_file_async(video_url, output_path)
                logger.info(f"下载完成: {segment_id} from {source}")
                return output_path
        except Exception as e:
            logger.warning(f"源 {source} 失败: {e}")
            continue

    # 所有源失败，生成背景
    return _generate_background(segment_id, output_dir)


async def _search_video_async(
    source: str,
    keyword: str,
    min_duration: float
) -> Optional[str]:
    """异步搜索视频

    Args:
        source: 素材源 (pexels, pixabay, coverr)
        keyword: 搜索关键词
        min_duration: 最小时长

    Returns:
        视频 URL，未找到返回 None
    """
    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        if source == "pexels":
            return await _search_pexels_async(session, keyword, min_duration)
        elif source == "pixabay":
            return await _search_pixabay_async(session, keyword, min_duration)
        elif source == "coverr":
            return await _search_coverr_async(session, keyword, min_duration)

    return None


async def _search_pexels_async(
    session: aiohttp.ClientSession,
    keyword: str,
    min_duration: float
) -> Optional[str]:
    """Pexels 异步搜索"""
    if not PEXELS_API_KEY:
        return None

    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": keyword, "per_page": 5}

    try:
        async with session.get(url, headers=headers, params=params) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()

            for video in data.get("videos", []):
                for file in video.get("video_files", []):
                    if file.get("width", 0) >= 1920:
                        return file.get("link")

    except Exception as e:
        logger.warning(f"Pexels 搜索失败: {e}")

    return None


async def _search_pixabay_async(
    session: aiohttp.ClientSession,
    keyword: str,
    min_duration: float
) -> Optional[str]:
    """Pixabay 异步搜索"""
    if not PIXABAY_API_KEY:
        return None

    url = "https://pixabay.com/api/videos/"
    params = {"key": PIXABAY_API_KEY, "q": keyword, "per_page": 5}

    try:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()

            for hit in data.get("hits", []):
                videos = hit.get("videos", {})
                for quality in ["large", "medium", "small"]:
                    if videos.get(quality):
                        return videos[quality].get("url")

    except Exception as e:
        logger.warning(f"Pixabay 搜索失败: {e}")

    return None


async def _search_coverr_async(
    session: aiohttp.ClientSession,
    keyword: str,
    min_duration: float
) -> Optional[str]:
    """Coverr 异步搜索（无需 API Key）"""
    # Coverr 没有 API，使用预定义视频列表
    # 这里简化实现，实际需要维护一个视频索引
    return None


async def _download_file_async(url: str, output_path: str) -> bool:
    """异步下载文件

    Args:
        url: 文件 URL
        output_path: 输出路径

    Returns:
        是否成功
    """
    timeout = aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise DownloadError(f"下载失败: HTTP {resp.status}")

            with open(output_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(1024 * 1024):
                    f.write(chunk)

    return True


def _get_sources(visual_mode: str) -> List[str]:
    """获取素材源列表"""
    if visual_mode == "pexels":
        return ["pexels"]
    elif visual_mode == "pixabay":
        return ["pixabay"]
    elif visual_mode == "coverr":
        return ["coverr"]
    else:
        # auto: 按优先级尝试
        sources = []
        if PEXELS_API_KEY:
            sources.append("pexels")
        if PIXABAY_API_KEY:
            sources.append("pixabay")
        sources.append("coverr")
        return sources


def _generate_background(segment_id: str, output_dir: str) -> str:
    """生成背景图片/视频作为 fallback

    Args:
        segment_id: 片段 ID
        output_dir: 输出目录

    Returns:
        生成的文件路径
    """
    # 使用 FFmpeg 生成纯色背景
    output_path = os.path.join(output_dir, f"{segment_id}_bg.mp4")

    # 随机颜色
    colors = ["0a0a2e", "1a1a4e", "2d1b69", "0a1628", "1a0a0a"]
    import random
    color = random.choice(colors)

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=0x{color}:s=1920x1080:d=5",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        output_path
    ]

    try:
        subprocess.run(cmd, capture_output=True, timeout=30, check=True)
        logger.info(f"生成背景: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"生成背景失败: {e}")
        # 返回空文件路径，后续渲染会处理
        return output_path