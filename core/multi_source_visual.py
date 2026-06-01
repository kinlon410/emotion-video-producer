#!/usr/bin/env python3
"""
多源视觉素材下载模块 — 支持多个免费视频素材源

支持源:
1. Pexels (https://www.pexels.com) - 高质量视频 [API Key]
2. Pixabay (https://pixabay.com) - 免费视频/图片 [API Key]
3. Coverr (https://coverr.co) - 免费视频
4. Mixkit (https://mixkit.co) - 免费视频/音乐
5. Videvo (https://www.videvo.net) - 免费4K视频
6. Videezy (https://www.videezy.com) - 高质量航拍/风景
7. Mazwai (https://mazwai.com) - 电影感视频
8. Dareful (https://dareful.com) - 4K精选视频
9. Life of Vids (https://lifeofvids.com) - 生活场景
10. Picsum (https://picsum.photos) - 图片备选

用法:
    python3 -m core.multi_source_visual --keywords '[{"id":"S1","keyword":"city night"}]' --output-dir ./clips
"""

import argparse
import json
import os
import random
import subprocess
import sys
import tempfile
import time
import re
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

import requests

from config import (
    PEXELS_API_KEY,
    PIXABAY_API_KEY,
    COVERR_API_KEY,
    DEFAULT_WIDTH,
    DEFAULT_HEIGHT,
    DEFAULT_FPS,
    DOWNLOAD_TIMEOUT,
    DOWNLOAD_RETRIES,
    PALETTES,
)

# 线程锁用于打印输出
_print_lock = threading.Lock()


# ── 素材源配置 ──

VIDEO_SOURCES = {
    "pexels": {
        "name": "Pexels",
        "search_url": "https://api.pexels.com/videos/search",
        "requires_key": True,
        "key_env": "PEXELS_API_KEY",
        "priority": 1,
        "free": True,
    },
    "pixabay": {
        "name": "Pixabay",
        "search_url": "https://pixabay.com/api/videos/",
        "requires_key": True,
        "key_env": "PIXABAY_API_KEY",
        "priority": 2,
        "free": True,
    },
    "coverr": {
        "name": "Coverr",
        "base_url": "https://coverr.co",
        "requires_key": False,
        "priority": 3,
        "free": True,
    },
    "mixkit": {
        "name": "Mixkit",
        "base_url": "https://mixkit.co",
        "requires_key": False,
        "priority": 4,
        "free": True,
    },
    "videvo": {
        "name": "Videvo",
        "base_url": "https://www.videvo.net",
        "requires_key": False,
        "priority": 5,
        "free": True,
    },
    "videezy": {
        "name": "Videezy",
        "base_url": "https://www.videezy.com",
        "requires_key": False,
        "priority": 6,
        "free": True,
    },
    "mazwai": {
        "name": "Mazwai",
        "base_url": "https://mazwai.com",
        "requires_key": False,
        "priority": 7,
        "free": True,
    },
    "dareful": {
        "name": "Dareful",
        "base_url": "https://dareful.com",
        "requires_key": False,
        "priority": 8,
        "free": True,
    },
    "lifeofvids": {
        "name": "Life of Vids",
        "base_url": "https://lifeofvids.com",
        "requires_key": False,
        "priority": 9,
        "free": True,
    },
}

# 关键词到分类映射（用于无搜索功能的网站）
CATEGORY_MAP = {
    "city": ["city", "urban", "building", "skyscraper", "street"],
    "night": ["night", "city night", "urban night", "night sky"],
    "nature": ["nature", "forest", "mountain", "ocean", "water", "river", "lake"],
    "people": ["people", "woman", "man", "child", "couple", "group"],
    "tech": ["tech", "computer", "code", "data", "digital", "cyber"],
    "abstract": ["abstract", "color", "gradient", "shape", "pattern"],
    "animal": ["animal", "dog", "cat", "bird", "wildlife"],
    "food": ["food", "cooking", "restaurant", "meal", "drink"],
    "travel": ["travel", "road", "car", "airplane", "airport", "train"],
    "sport": ["sport", "running", "fitness", "gym", "exercise"],
    "business": ["business", "office", "work", "meeting", "team"],
    "sunset": ["sunset", "sunrise", "dusk", "dawn"],
    "cloud": ["cloud", "sky", "weather", "storm"],
    "beach": ["beach", "sea", "sand", "coast"],
}

# ── Dedup 管理器 ──

class VideoDedupManager:
    """视频去重管理器"""

    _downloaded_ids: set = set()
    _downloaded_urls: set = set()

    @classmethod
    def reset(cls):
        cls._downloaded_ids = set()
        cls._downloaded_urls = set()

    @classmethod
    def add(cls, video_id: str, url: str = ""):
        cls._downloaded_ids.add(video_id)
        if url:
            cls._downloaded_urls.add(url)

    @classmethod
    def is_downloaded(cls, video_id: str) -> bool:
        return video_id in cls._downloaded_ids

    @classmethod
    def is_url_downloaded(cls, url: str) -> bool:
        return url in cls._downloaded_urls


# ── HTTP 请求工具 ──

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
}


def safe_request(url: str, timeout: int = 30, stream: bool = False) -> Optional[requests.Response]:
    """安全的HTTP请求，带重试"""
    for attempt in range(3):
        try:
            if stream:
                return requests.get(url, headers=HEADERS, timeout=timeout, stream=True)
            else:
                return requests.get(url, headers=HEADERS, timeout=timeout)
        except Exception as e:
            if attempt < 2:
                time.sleep(1)
            continue
    return None


def download_video_file(video_url: str, output_path: str, duration: float) -> bool:
    """下载视频文件并截取片段"""
    try:
        temp_path = output_path + ".temp.mp4"

        resp = safe_request(video_url, timeout=DOWNLOAD_TIMEOUT, stream=True)
        if not resp or resp.status_code != 200:
            return False

        with open(temp_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        # 截取片段并强制统一尺寸
        cmd = [
            "ffmpeg", "-y", "-i", temp_path,
            "-t", str(duration),
            "-vf", f"scale={DEFAULT_WIDTH}:{DEFAULT_HEIGHT}:force_original_aspect_ratio=decrease,pad={DEFAULT_WIDTH}:{DEFAULT_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,setsar=1",
            "-c:v", "libx264", "-preset", "fast",
            "-pix_fmt", "yuv420p", "-r", str(DEFAULT_FPS),
            "-an",
            output_path
        ]

        subprocess.run(cmd, capture_output=True, timeout=120, check=True)
        os.remove(temp_path)
        return True

    except Exception:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        return False


def get_category_for_keyword(keyword: str) -> str:
    """根据关键词推断分类"""
    keyword_lower = keyword.lower()
    for category, keywords in CATEGORY_MAP.items():
        for k in keywords:
            if k in keyword_lower:
                return category
    return "nature"  # 默认分类


def download_from_multi_sources(
    keywords: List[Dict],
    output_dir: str,
    sources: Optional[List[str]] = None,
    mode: str = "auto",
    max_workers: int = 10,  # 增加并发数到10
) -> Dict[str, str]:
    """从多源下载视觉素材（并发下载）

    Args:
        keywords: [{"id": "S1", "keyword": "city night", "duration": 3.0}, ...]
        output_dir: 输出目录
        sources: 素材源优先级列表
        mode: 素材获取模式 (auto/pexels/pixabay/coverr/mixkit/videvo/videezy/mazwai/dareful/download/generate)
        max_workers: 最大并发线程数（默认5）

    Returns:
        dict: {segment_id: video_path} 映射
    """
    print(f"[multi_source_visual] 多源素材下载（并发模式）")
    print(f"  支持源: Pexels, Pixabay, Coverr, Mixkit, Videvo, Videezy, Mazwai, Dareful, Life of Vids")
    print(f"  并发数: {max_workers}")

    if sources is None:
        sources = ["pexels", "pixabay", "coverr", "mixkit", "videvo", "videezy", "mazwai", "dareful", "lifeofvids"]

    VideoDedupManager.reset()

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    clips = {}
    total = len(keywords)
    completed = 0

    def download_single(query: Dict) -> Tuple[str, Optional[str]]:
        """下载单个片段"""
        seg_id = query["id"]
        keyword = query.get("keyword", "")
        duration = query.get("duration", 3.0)
        output_path = str(Path(output_dir) / f"{seg_id}.mp4")

        success = False

        # 按优先级尝试各源
        for source in sources:
            if mode != "auto" and mode != source:
                continue

            source_func = SOURCE_DOWNLOADERS.get(source)
            if not source_func:
                continue

            try:
                success = source_func(keyword, output_path, duration)
                if success:
                    with _print_lock:
                        print(f"  [{seg_id}] ✓ {VIDEO_SOURCES[source]['name']} ({keyword})")
                    break
            except Exception:
                continue

        # 如果所有源都失败，尝试图片 + Ken Burns
        if not success and mode in ("auto", "download"):
            img_path = str(Path(output_dir) / f"{seg_id}.jpg")
            if _download_image(keyword, img_path):
                success = _image_to_video(img_path, output_path, duration)
                if success:
                    with _print_lock:
                        print(f"  [{seg_id}] ✓ 图片+Ken Burns ({keyword})")

        # 最后尝试生成动态背景
        if not success and mode in ("auto", "generate"):
            palette = random.choice(list(PALETTES.keys()))
            success = _generate_background(output_path, duration, palette)
            if success:
                with _print_lock:
                    print(f"  [{seg_id}] ✓ 动态背景 ({palette})")

        if not success:
            with _print_lock:
                print(f"  [{seg_id}] ✗ 失败 ({keyword})")

        return seg_id, output_path if success else None

    # 使用线程池并发下载
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_single, query): query for query in keywords}

        for future in as_completed(futures):
            seg_id, path = future.result()
            if path:
                clips[seg_id] = path
            completed += 1

            # 打印进度
            with _print_lock:
                if completed % 3 == 0 or completed == total:
                    print(f"  进度: {completed}/{total} ({len(clips)} 成功)")

    print(f"  完成: {len(clips)}/{total} 个片段")

    return clips


# ── 材源下载函数 ──

# 函数映射在文件末尾定义


def _download_from_pexels(keyword: str, output_path: str, duration: float) -> bool:
    """从 Pexels 下载视频"""

    if not PEXELS_API_KEY:
        return False

    try:
        headers = {"Authorization": PEXELS_API_KEY}
        params = {"query": keyword, "per_page": 20, "orientation": "landscape", "size": "large"}

        resp = requests.get(
            "https://api.pexels.com/videos/search",
            headers=headers,
            params=params,
            timeout=30
        )

        if resp.status_code != 200:
            return False

        data = resp.json()
        videos = data.get("videos", [])

        for video in videos:
            video_id = str(video.get("id", ""))

            if VideoDedupManager.is_downloaded(video_id):
                continue

            video_files = video.get("video_files", [])

            best_file = None
            best_score = 0
            target_ratio = DEFAULT_WIDTH / DEFAULT_HEIGHT

            for f in video_files:
                w = f.get("width", 0)
                h = f.get("height", 0)

                if w < DEFAULT_WIDTH or h < DEFAULT_HEIGHT:
                    continue

                ratio = w / h
                ratio_score = 1.0 - abs(ratio - target_ratio) / target_ratio
                size_score = min(w / DEFAULT_WIDTH, 2.0)
                total_score = ratio_score * 0.7 + size_score * 0.3

                if total_score > best_score:
                    best_score = total_score
                    best_file = f

            if not best_file:
                continue

            video_url = best_file.get("link", "")
            if not video_url:
                continue

            if download_video_file(video_url, output_path, duration):
                VideoDedupManager.add(video_id, video_url)
                return True

    except Exception:
        pass

    return False


def _download_from_pixabay(keyword: str, output_path: str, duration: float) -> bool:
    """从 Pixabay 下载视频"""

    if not PIXABAY_API_KEY:
        return False

    try:
        params = {
            "key": PIXABAY_API_KEY,
            "q": keyword,
            "video_type": "all",
            "per_page": 20,
            "orientation": "horizontal",
            "min_width": DEFAULT_WIDTH,
            "min_height": DEFAULT_HEIGHT,
        }

        resp = requests.get(
            "https://pixabay.com/api/videos/",
            params=params,
            timeout=30
        )

        if resp.status_code != 200:
            return False

        data = resp.json()
        videos = data.get("hits", [])

        for video in videos:
            video_id = str(video.get("id", ""))

            if VideoDedupManager.is_downloaded(video_id):
                continue

            video_files = video.get("videos", {})
            hd_file = video_files.get("large", {}) or video_files.get("medium", {})

            video_url = hd_file.get("url", "")
            if not video_url:
                continue

            if download_video_file(video_url, output_path, duration):
                VideoDedupManager.add(video_id, video_url)
                return True

    except Exception:
        pass

    return False


def _download_from_coverr(keyword: str, output_path: str, duration: float) -> bool:
    """从 Coverr 下载视频（爬取方式）"""

    try:
        # Coverr 搜索页面
        search_url = f"https://coverr.co/search?q={urllib.parse.quote(keyword)}"

        resp = safe_request(search_url)
        if not resp:
            return False

        html_content = resp.text

        # 查找 .mp4 链接
        mp4_pattern = r'https?://[^"\']+\.mp4'
        mp4_urls = re.findall(mp4_pattern, html_content)

        if not mp4_urls:
            # 尝试分类页面
            category = get_category_for_keyword(keyword)
            category_url = f"https://coverr.co/category/{category}"

            resp = safe_request(category_url)
            if resp:
                mp4_urls = re.findall(mp4_pattern, resp.text)

        if not mp4_urls:
            return False

        # 选择未下载的视频
        for video_url in mp4_urls[:5]:
            if VideoDedupManager.is_url_downloaded(video_url):
                continue

            video_id = video_url.split("/")[-1].replace(".mp4", "")

            if download_video_file(video_url, output_path, duration):
                VideoDedupManager.add(video_id, video_url)
                return True

    except Exception:
        pass

    return False


def _download_from_mixkit(keyword: str, output_path: str, duration: float) -> bool:
    """从 Mixkit 下载视频"""

    try:
        # Mixkit 搜索
        search_url = f"https://mixkit.co/search/?q={urllib.parse.quote(keyword)}"

        resp = safe_request(search_url)
        if not resp:
            return False

        html_content = resp.text

        # Mixkit 视频链接格式
        mp4_pattern = r'https?://[^"\']*mixkit[^"\']*\.mp4'
        mp4_urls = re.findall(mp4_pattern, html_content)

        if not mp4_urls:
            # 尝试分类页面
            category = get_category_for_keyword(keyword)
            category_map = {
                "city": "city",
                "nature": "nature",
                "people": "people",
                "tech": "technology",
                "abstract": "abstract",
                "animal": "animals",
                "food": "food",
                "travel": "travel",
                "sport": "sports",
                "business": "business",
                "sunset": "nature",
                "cloud": "nature",
                "beach": "nature",
            }

            category_slug = category_map.get(category, "nature")
            category_url = f"https://mixkit.co/free-stock-video/{category_slug}/"

            resp = safe_request(category_url)
            if resp:
                mp4_urls = re.findall(mp4_pattern, resp.text)

        if not mp4_urls:
            return False

        for video_url in mp4_urls[:5]:
            if VideoDedupManager.is_url_downloaded(video_url):
                continue

            video_id = video_url.split("/")[-1].replace(".mp4", "")

            if download_video_file(video_url, output_path, duration):
                VideoDedupManager.add(video_id, video_url)
                return True

    except Exception:
        pass

    return False


def _download_from_videvo(keyword: str, output_path: str, duration: float) -> bool:
    """从 Videvo 下载视频"""

    try:
        # Videvo 搜索
        search_url = f"https://www.videvo.net/search/video/{urllib.parse.quote(keyword)}/"

        resp = safe_request(search_url)
        if not resp:
            return False

        html_content = resp.text

        # Videvo 视频链接
        mp4_pattern = r'https?://[^"\']*videvo[^"\']*\.mp4'
        mp4_urls = re.findall(mp4_pattern, html_content)

        if not mp4_urls:
            # 尝试分类
            category = get_category_for_keyword(keyword)
            category_url = f"https://www.videvo.net/video/{category}/"

            resp = safe_request(category_url)
            if resp:
                mp4_urls = re.findall(mp4_pattern, resp.text)

        if not mp4_urls:
            return False

        for video_url in mp4_urls[:5]:
            if VideoDedupManager.is_url_downloaded(video_url):
                continue

            video_id = video_url.split("/")[-1].replace(".mp4", "")

            if download_video_file(video_url, output_path, duration):
                VideoDedupManager.add(video_id, video_url)
                return True

    except Exception:
        pass

    return False


def _download_from_videezy(keyword: str, output_path: str, duration: float) -> bool:
    """从 Videezy 下载视频"""

    try:
        # Videezy 搜索
        search_url = f"https://www.videezy.com/search/{urllib.parse.quote(keyword)}"

        resp = safe_request(search_url)
        if not resp:
            return False

        html_content = resp.text

        # Videezy 视频链接
        mp4_pattern = r'https?://[^"\']*\.mp4'
        mp4_urls = re.findall(mp4_pattern, html_content)

        # 过滤掉非视频相关的链接
        mp4_urls = [url for url in mp4_urls if 'videezy' in url or 'cdn' in url]

        if not mp4_urls:
            # 尝试分类页面
            category = get_category_for_keyword(keyword)
            category_url = f"https://www.videezy.com/{category}"

            resp = safe_request(category_url)
            if resp:
                mp4_urls = re.findall(mp4_pattern, resp.text)
                mp4_urls = [url for url in mp4_urls if 'videezy' in url or 'cdn' in url]

        if not mp4_urls:
            return False

        for video_url in mp4_urls[:5]:
            if VideoDedupManager.is_url_downloaded(video_url):
                continue

            video_id = video_url.split("/")[-1].replace(".mp4", "")

            if download_video_file(video_url, output_path, duration):
                VideoDedupManager.add(video_id, video_url)
                return True

    except Exception:
        pass

    return False


def _download_from_mazwai(keyword: str, output_path: str, duration: float) -> bool:
    """从 Mazwai 下载视频"""

    try:
        # Mazwai 搜索页面
        search_url = f"https://mazwai.com/search?query={urllib.parse.quote(keyword)}"

        resp = safe_request(search_url)
        if not resp:
            return False

        html_content = resp.text

        # Mazwai 视频链接
        mp4_pattern = r'https?://[^"\']*\.mp4'
        mp4_urls = re.findall(mp4_pattern, html_content)

        if not mp4_urls:
            # 尝试分类页面
            category = get_category_for_keyword(keyword)
            category_url = f"https://mazwai.com/videos/{category}"

            resp = safe_request(category_url)
            if resp:
                mp4_urls = re.findall(mp4_pattern, resp.text)

        if not mp4_urls:
            return False

        for video_url in mp4_urls[:5]:
            if VideoDedupManager.is_url_downloaded(video_url):
                continue

            video_id = video_url.split("/")[-1].replace(".mp4", "")

            if download_video_file(video_url, output_path, duration):
                VideoDedupManager.add(video_id, video_url)
                return True

    except Exception:
        pass

    return False


def _download_from_dareful(keyword: str, output_path: str, duration: float) -> bool:
    """从 Dareful 下载视频"""

    try:
        # Dareful 直接视频链接列表
        # Dareful 提供精选4K视频，有固定分类
        category = get_category_for_keyword(keyword)

        # Dareful 分类映射和视频链接
        dareful_videos = {
            "nature": [
                "https://dareful.com/videos/forest-morning.mp4",
                "https://dareful.com/videos/ocean-waves.mp4",
                "https://dareful.com/videos/sunset-field.mp4",
            ],
            "city": [
                "https://dareful.com/videos/city-night.mp4",
                "https://dareful.com/videos/urban-street.mp4",
            ],
            "sunset": [
                "https://dareful.com/videos/sunset-sky.mp4",
                "https://dareful.com/videos/golden-hour.mp4",
            ],
            "cloud": [
                "https://dareful.com/videos/clouds-moving.mp4",
                "https://dareful.com/videos/sky-timelapse.mp4",
            ],
            "abstract": [
                "https://dareful.com/videos/color-gradient.mp4",
                "https://dareful.com/videos/abstract-motion.mp4",
            ],
        }

        # 获取分类视频
        videos = dareful_videos.get(category, dareful_videos.get("nature", []))

        # 如果没有匹配分类，尝试搜索页面
        if not videos:
            search_url = f"https://dareful.com/search?q={urllib.parse.quote(keyword)}"
            resp = safe_request(search_url)
            if resp:
                mp4_pattern = r'https?://[^"\']*\.mp4'
                videos = re.findall(mp4_pattern, resp.text)

        for video_url in videos[:3]:
            if VideoDedupManager.is_url_downloaded(video_url):
                continue

            video_id = video_url.split("/")[-1].replace(".mp4", "")

            if download_video_file(video_url, output_path, duration):
                VideoDedupManager.add(video_id, video_url)
                return True

    except Exception:
        pass

    return False


def _download_from_lifeofvids(keyword: str, output_path: str, duration: float) -> bool:
    """从 Life of Vids 下载视频"""

    try:
        # Life of Vids 搜索
        search_url = f"https://lifeofvids.com/search/{urllib.parse.quote(keyword)}"

        resp = safe_request(search_url)
        if not resp:
            return False

        html_content = resp.text

        # Life of Vids 视频链接
        mp4_pattern = r'https?://[^"\']*\.mp4'
        mp4_urls = re.findall(mp4_pattern, html_content)

        if not mp4_urls:
            # 尝试分类页面
            category = get_category_for_keyword(keyword)
            category_url = f"https://lifeofvids.com/category/{category}"

            resp = safe_request(category_url)
            if resp:
                mp4_urls = re.findall(mp4_pattern, resp.text)

        if not mp4_urls:
            return False

        for video_url in mp4_urls[:5]:
            if VideoDedupManager.is_url_downloaded(video_url):
                continue

            video_id = video_url.split("/")[-1].replace(".mp4", "")

            if download_video_file(video_url, output_path, duration):
                VideoDedupManager.add(video_id, video_url)
                return True

    except Exception:
        pass

    return False


def _download_image(keyword: str, output_path: str) -> bool:
    """从 Picsum 下载图片"""

    try:
        seed = keyword.replace(" ", "_").replace(",", "")
        url = f"https://picsum.photos/seed/{seed}/{DEFAULT_WIDTH}/{DEFAULT_HEIGHT}"

        resp = safe_request(url)
        if resp and resp.status_code == 200 and len(resp.content) > 10000:
            with open(output_path, "wb") as f:
                f.write(resp.content)
            return True

    except Exception:
        pass

    return False


def _image_to_video(image_path: str, output_path: str, duration: float) -> bool:
    """将图片转为带 Ken Burns 效果的视频"""

    total_frames = int(duration * DEFAULT_FPS)

    vf = (
        f"scale={DEFAULT_WIDTH}:{DEFAULT_HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={DEFAULT_WIDTH}:{DEFAULT_HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
        f"zoompan=z='min(zoom+0.0003,1.2)':d={total_frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={DEFAULT_WIDTH}x{DEFAULT_HEIGHT}:fps={DEFAULT_FPS},"
        f"format=yuv420p"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
        "-vf", vf,
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast",
        "-pix_fmt", "yuv420p", "-an",
        output_path
    ]

    try:
        subprocess.run(cmd, capture_output=True, timeout=120, check=True)
        os.remove(image_path)
        return True
    except Exception:
        return False


def _generate_background(output_path: str, duration: float, palette: str) -> bool:
    """生成动态渐变背景"""

    colors = PALETTES.get(palette, PALETTES["city_night"])

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i",
        f"gradients=s={DEFAULT_WIDTH}x{DEFAULT_HEIGHT}:c0=0x{colors[0]}:c1=0x{colors[1]}:duration={duration}:speed=0.3:angle=45",
        "-vf", f"boxblur=20:10,eq=saturation=1.2",
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast",
        "-pix_fmt", "yuv420p", "-an",
        output_path
    ]

    try:
        subprocess.run(cmd, capture_output=True, timeout=120, check=True)
        return True
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="多源视觉素材下载模块")
    parser.add_argument("--keywords", required=True, help="关键词 JSON 数组")
    parser.add_argument("--output-dir", default="clips", help="输出目录")
    parser.add_argument("--sources", default="pexels,pixabay,coverr,mixkit,videvo,videezy,mazwai,dareful,lifeofvids", help="素材源列表")
    parser.add_argument("--mode", default="auto", choices=["auto", "pexels", "pixabay", "coverr", "mixkit", "videvo", "videezy", "mazwai", "dareful", "lifeofvids", "download", "generate"])
    args = parser.parse_args()

    keywords = json.loads(args.keywords)
    sources = args.sources.split(",")

    clips = download_from_multi_sources(keywords, args.output_dir, sources, args.mode)

    print(json.dumps(clips, ensure_ascii=False, indent=2))


# ── 材源下载函数映射 ──

SOURCE_DOWNLOADERS = {
    "pexels": _download_from_pexels,
    "pixabay": _download_from_pixabay,
    "coverr": _download_from_coverr,
    "mixkit": _download_from_mixkit,
    "videvo": _download_from_videvo,
    "videezy": _download_from_videezy,
    "mazwai": _download_from_mazwai,
    "dareful": _download_from_dareful,
    "lifeofvids": _download_from_lifeofvids,
}


if __name__ == "__main__":
    main()