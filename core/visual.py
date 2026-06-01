#!/usr/bin/env python3
"""
视觉素材模块 — 根据关键词下载视频素材

支持:
1. 多源视频下载（Pexels/Pixabay/Coverr/Mixkit/Videvo/Videezy/Mazwai/Dareful/Life of Vids）
2. 图片下载 + Ken Burns 动效（备选）
3. FFmpeg 生成动态背景（离线）

用法:
    python3 -m core.visual --keywords '[{"id":"S1","keyword":"city night"}]' --output-dir ./clips
"""

import argparse
import json
import os
import random
import subprocess
import sys
import time
import urllib3
from pathlib import Path
from typing import Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import PEXELS_API_KEY, PIXABAY_API_KEY, DEFAULT_WIDTH, DEFAULT_HEIGHT, DEFAULT_FPS

# 导入多源下载模块
from .multi_source_visual import download_from_multi_sources


# ── 创建带重试的 Session ──

def _create_retry_session(retries=3, backoff_factor=0.5):
    """创建带自动重试的 requests Session"""
    session = requests.Session()

    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


# 全局 retry session
_RETRY_SESSION = None


# ── 预设调色板 ──

PALETTES = {
    "city_night": ("0a0a2e", "1a1a4e", "2d1b69"),
    "sunset": ("1a0a2e", "4a1942", "c94b4b"),
    "ocean": ("0a1628", "0d3b66", "1a936f"),
    "neon": ("0a0a1a", "1a0a3e", "e94560"),
    "warm": ("1a0a0a", "3e1a0a", "b85c38"),
}


def download_visuals(visual_queries: List[Dict], output_dir: str,
                     mode: str = "auto",
                     width: int = None, height: int = None) -> Dict[str, str]:
    """下载视觉素材

    Args:
        visual_queries: [{"id": "S1", "keyword": "city night", "duration": 3.0}, ...]
        output_dir: 输出目录
        mode: 素材获取模式 (auto/pexels/pixabay/download/generate)
        width: 视频宽度（默认 1920）
        height: 视频高度（默认 1080 或根据 ratio 计算）

    Returns:
        dict: {segment_id: video_path} 映射
    """
    # 确定目标尺寸
    target_width = width or DEFAULT_WIDTH
    target_height = height or DEFAULT_HEIGHT

    print(f"[visual] 下载视觉素材: {len(visual_queries)} 个片段, 尺寸: {target_width}x{target_height}, 模式: {mode}")

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 使用多源下载模块（包含所有免费素材源）
    return download_from_multi_sources(
        visual_queries,
        output_dir,
        mode=mode
    )


def _download_from_pexels(keyword: str, output_path: str, duration: float,
                          max_retries: int = 2,
                          width: int = None, height: int = None) -> bool:
    """从 Pexels 下载视频（带重试）

    Args:
        keyword: 搜索关键词
        output_path: 输出路径
        duration: 片段时长
        max_retries: 最大重试次数
        width: 视频宽度
        height: 视频高度
    """
    global _RETRY_SESSION

    if not PEXELS_API_KEY:
        return False

    target_width = width or DEFAULT_WIDTH
    target_height = height or DEFAULT_HEIGHT

    # 根据宽高比确定搜索方向
    orientation = "landscape" if target_width > target_height else "portrait"

    for attempt in range(max_retries + 1):
        try:
            # 搜索视频
            search_url = "https://api.pexels.com/videos/search"
            headers = {"Authorization": PEXELS_API_KEY}
            params = {"query": keyword, "per_page": 10, "orientation": orientation, "size": "large"}

            # 使用 retry session
            resp = _RETRY_SESSION.get(search_url, headers=headers, params=params,
                                       timeout=30)

            if resp.status_code != 200:
                if attempt < max_retries:
                    time.sleep(1 * (attempt + 1))  # 递增等待
                    continue
                return False

            data = resp.json()
            videos = data.get("videos", [])

            if not videos:
                return False

            # 选择合适的视频
            for video in videos:
                video_files = video.get("video_files", [])

                # 选择符合尺寸的视频（优先目标比例）
                best_file = None
                best_score = 0
                target_ratio = target_width / target_height

                for f in video_files:
                    w = f.get("width", 0)
                    h = f.get("height", 0)
                    if w < target_width or h < target_height:
                        continue

                    # 计算宽高比匹配度
                    ratio = w / h
                    ratio_score = 1.0 - abs(ratio - target_ratio) / target_ratio

                    # 尺寸匹配度
                    size_score = min(w / target_width, 2.0)

                    total_score = ratio_score * 0.7 + size_score * 0.3

                    if total_score > best_score:
                        best_score = total_score
                        best_file = f

                hd_file = best_file

                if not hd_file:
                    continue

                video_url = hd_file.get("link", "")
                if not video_url:
                    continue

                # 下载视频
                video_resp = _RETRY_SESSION.get(video_url, timeout=120, stream=True)

                if video_resp.status_code != 200:
                    continue

                temp_path = output_path + ".temp.mp4"
                with open(temp_path, "wb") as f:
                    for chunk in video_resp.iter_content(chunk_size=8192):
                        f.write(chunk)

                # 截取片段并强制统一尺寸
                cmd = [
                    "ffmpeg", "-y",
                    "-i", temp_path,
                    "-t", str(duration),
                    "-vf", f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:black,setsar=1",
                    "-c:v", "libx264",
                    "-preset", "fast",
                    "-pix_fmt", "yuv420p",
                    "-r", str(DEFAULT_FPS),
                    "-an",
                    output_path
                ]

                subprocess.run(cmd, capture_output=True, timeout=120, check=True)
                os.remove(temp_path)

                return True

        except Exception as e:
            if attempt < max_retries:
                print(f"    [Pexels 重试 {attempt + 1}/{max_retries}] {e}", file=sys.stderr)
                time.sleep(2 * (attempt + 1))
            else:
                print(f"    [Pexels 错误] {e}", file=sys.stderr)

    return False


def _download_from_pixabay(keyword: str, output_path: str, duration: float,
                           width: int = None, height: int = None) -> bool:
    """从 Pixabay 下载视频（备选）

    Args:
        keyword: 搜索关键词
        output_path: 输出路径
        duration: 片段时长
        width: 视频宽度
        height: 视频高度
    """

    global _RETRY_SESSION

    if not PIXABAY_API_KEY:
        return False

    target_width = width or DEFAULT_WIDTH
    target_height = height or DEFAULT_HEIGHT

    # 根据宽高比确定搜索方向
    orientation = "horizontal" if target_width > target_height else "vertical"

    try:
        # 搜索视频
        search_url = "https://pixabay.com/api/videos/"
        params = {
            "key": PIXABAY_API_KEY,
            "q": keyword,
            "per_page": 10,
            "video_type": "all",
            "orientation": orientation,
            "min_width": target_width,
            "min_height": target_height,
        }

        resp = _RETRY_SESSION.get(search_url, params=params, timeout=30)

        if resp.status_code != 200:
            return False

        data = resp.json()
        hits = data.get("hits", [])

        if not hits:
            return False

        # 选择合适的视频
        for hit in hits:
            videos = hit.get("videos", {})

            # 选择 HD 质量
            hd_url = videos.get("large", {}).get("url") or \
                     videos.get("medium", {}).get("url")

            if not hd_url:
                continue

            # 下载视频
            video_resp = _RETRY_SESSION.get(hd_url, timeout=120, stream=True)

            if video_resp.status_code != 200:
                continue

            temp_path = output_path + ".temp.mp4"
            with open(temp_path, "wb") as f:
                for chunk in video_resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            # 截取片段并强制统一尺寸
            cmd = [
                "ffmpeg", "-y",
                "-i", temp_path,
                "-t", str(duration),
                "-vf", f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:black,setsar=1",
                "-c:v", "libx264",
                "-preset", "fast",
                "-pix_fmt", "yuv420p",
                "-r", str(DEFAULT_FPS),
                "-an",
                output_path
            ]

            subprocess.run(cmd, capture_output=True, timeout=120, check=True)
            os.remove(temp_path)

            print(f"    ✓ Pixabay 备选成功")
            return True

    except Exception as e:
        print(f"    [Pixabay 错误] {e}", file=sys.stderr)

    return False


def _download_image(keyword: str, output_path: str,
                    width: int = None, height: int = None) -> bool:
    """下载图片

    Args:
        keyword: 搜索关键词
        output_path: 输出路径
        width: 图片宽度
        height: 图片高度
    """
    target_width = width or DEFAULT_WIDTH
    target_height = height or DEFAULT_HEIGHT

    try:
        seed = keyword.replace(" ", "_")
        url = f"https://picsum.photos/seed/{seed}/{target_width}/{target_height}"

        resp = requests.get(url, timeout=30)

        if resp.status_code == 200 and len(resp.content) > 10000:
            with open(output_path, "wb") as f:
                f.write(resp.content)
            return True

    except Exception:
        pass

    return False


def _image_to_video(image_path: str, output_path: str, duration: float,
                    width: int = None, height: int = None) -> bool:
    """将图片转为带 Ken Burns 效果的视频

    Args:
        image_path: 图片路径
        output_path: 输出路径
        duration: 视频时长
        width: 视频宽度
        height: 视频高度
    """
    target_width = width or DEFAULT_WIDTH
    target_height = height or DEFAULT_HEIGHT

    total_frames = int(duration * DEFAULT_FPS)

    vf = (
        f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
        f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,"
        f"zoompan=z='min(zoom+0.0003,1.2)':d={total_frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={target_width}x{target_height}:fps={DEFAULT_FPS},"
        f"format=yuv420p"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
        "-vf", vf,
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-an",
        output_path
    ]

    try:
        subprocess.run(cmd, capture_output=True, timeout=120, check=True)
        # 清理图片
        os.remove(image_path)
        return True
    except Exception as e:
        print(f"    [图片转视频错误] {e}", file=sys.stderr)
        return False


def _generate_background(output_path: str, duration: float, palette: str,
                         width: int = None, height: int = None) -> bool:
    """生成动态背景

    Args:
        output_path: 输出路径
        duration: 视频时长
        palette: 调色板名称
        width: 视频宽度
        height: 视频高度
    """
    target_width = width or DEFAULT_WIDTH
    target_height = height or DEFAULT_HEIGHT

    colors = PALETTES.get(palette, PALETTES["city_night"])

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i",
        f"gradients=s={target_width}x{target_height}:c0=0x{colors[0]}:c1=0x{colors[1]}:duration={duration}:speed=0.3:angle=45",
        "-vf", f"boxblur=20:10,eq=saturation=1.2",
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-an",
        output_path
    ]

    try:
        subprocess.run(cmd, capture_output=True, timeout=120, check=True)
        return True
    except Exception as e:
        print(f"    [背景生成错误] {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="视觉素材模块")
    parser.add_argument("--keywords", required=True, help="关键词 JSON 数组")
    parser.add_argument("--output-dir", default="clips", help="输出目录")
    parser.add_argument("--mode", default="auto", choices=["pexels", "download", "generate", "auto"])
    args = parser.parse_args()

    queries = json.loads(args.keywords)
    clips = download_visuals(queries, args.output_dir, args.mode)

    print(json.dumps(clips, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()