#!/usr/bin/env python3
"""
素材本地管理 — 用户上传素材，自动打标签，优先匹配

支持：
1. upload_asset — 上传素材并自动打标签
2. search_assets — 搜索用户素材
3. match_assets — 匹配素材到视频片段
4. manage_assets — 素材库管理（删除、重命名）
"""

import json
import os
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from core.logging_config import get_logger
from core.exceptions import AssetNotFoundError

logger = get_logger("asset_manager")


ASSETS_DIR = Path(__file__).parent.parent / "user_assets"
ASSETS_INDEX = ASSETS_DIR / "index.json"


@dataclass
class UserAsset:
    """用户素材"""
    asset_id: str
    file_path: str
    file_type: str  # video, image, audio
    filename: str
    size: int  # 文件大小 (bytes)
    duration: Optional[float] = None  # 视频时长 (seconds)
    width: Optional[int] = None
    height: Optional[int] = None

    # 自动标签
    auto_tags: List[str] = field(default_factory=list)
    # 用户标签
    user_tags: List[str] = field(default_factory=list)

    # 元数据
    upload_time: str = ""
    last_used: str = ""
    use_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "filename": self.filename,
            "size": self.size,
            "duration": self.duration,
            "width": self.width,
            "height": self.height,
            "auto_tags": self.auto_tags,
            "user_tags": self.user_tags,
            "upload_time": self.upload_time,
            "last_used": self.last_used,
            "use_count": self.use_count,
        }


# 标签推断规则
TAG_RULES = {
    # 文件名关键词 → 标签
    "keywords": {
        "城市": ["城市", "都市", "夜景", "霓虹", "街道"],
        "自然": ["自然", "风景", "山水", "森林", "海洋", "日落", "日出"],
        "人物": ["人物", "人", "笑脸", "团队", "运动", "奔跑"],
        "科技": ["科技", "技术", "数码", "手机", "电脑", "创新"],
        "节日": ["春节", "中秋", "生日", "烟花", "灯笼", "礼物"],
        "美食": ["美食", "食物", "烹饪", "餐厅", "食材"],
        "旅行": ["旅行", "旅游", "风景", "探索", "城市"],
        "情感": ["爱", "浪漫", "表白", "温馨", "幸福"],
    },

    # 文件类型 → 默认标签
    "type_defaults": {
        "video": ["动态", "场景"],
        "image": ["静态", "画面"],
        "audio": ["声音", "背景"],
    },
}


class AssetManager:
    """素材管理器"""

    def __init__(self, assets_dir: str = None):
        """初始化

        Args:
            assets_dir: 素材存储目录
        """
        self.assets_dir = Path(assets_dir) if assets_dir else ASSETS_DIR
        self.assets_dir.mkdir(parents=True, exist_ok=True)

        # 创建子目录
        self.videos_dir = self.assets_dir / "videos"
        self.images_dir = self.assets_dir / "images"
        self.audio_dir = self.assets_dir / "audio"
        self.videos_dir.mkdir(exist_ok=True)
        self.images_dir.mkdir(exist_ok=True)
        self.audio_dir.mkdir(exist_ok=True)

        # 加载索引
        self.index: Dict[str, Dict] = self._load_index()

    def _load_index(self) -> Dict[str, Dict]:
        """加载素材索引"""
        if ASSETS_INDEX.exists():
            with open(ASSETS_INDEX, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_index(self):
        """保存素材索引"""
        with open(ASSETS_INDEX, "w", encoding="utf-8") as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)

    def upload_asset(
        self,
        file_path: str,
        user_tags: List[str] = None
    ) -> UserAsset:
        """上传素材

        Args:
            file_path: 源文件路径
            user_tags: 用户自定义标签（可选）

        Returns:
            UserAsset 素材对象
        """
        src_path = Path(file_path)
        if not src_path.exists():
            raise AssetNotFoundError(f"文件不存在: {file_path}")

        # 确定文件类型
        ext = src_path.suffix.lower()
        if ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
            file_type = "video"
            dest_dir = self.videos_dir
        elif ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]:
            file_type = "image"
            dest_dir = self.images_dir
        elif ext in [".mp3", ".wav", ".ogg", ".flac", ".aac"]:
            file_type = "audio"
            dest_dir = self.audio_dir
        else:
            file_type = "unknown"
            dest_dir = self.assets_dir

        # 生成唯一 ID
        asset_id = hashlib.md5(f"{src_path.name}{datetime.utcnow().isoformat()}".encode()).hexdigest()[:12]

        # 复制文件
        dest_path = dest_dir / f"{asset_id}{ext}"
        shutil.copy2(src_path, dest_path)

        # 自动标签
        auto_tags = self._infer_tags(src_path.name, file_type)

        # 获取文件信息
        size = dest_path.stat().st_size
        duration, width, height = self._get_media_info(str(dest_path), file_type)

        # 创建素材对象
        asset = UserAsset(
            asset_id=asset_id,
            file_path=str(dest_path),
            file_type=file_type,
            filename=src_path.name,
            size=size,
            duration=duration,
            width=width,
            height=height,
            auto_tags=auto_tags,
            user_tags=user_tags or [],
            upload_time=datetime.utcnow().isoformat(),
            use_count=0,
        )

        # 更新索引
        self.index[asset_id] = asset.to_dict()
        self._save_index()

        logger.info(f"素材上传: {asset_id}, type={file_type}, tags={auto_tags}")
        return asset

    def _infer_tags(self, filename: str, file_type: str) -> List[str]:
        """推断标签

        Args:
            filename: 文件名
            file_type: 文件类型

        Returns:
            标签列表
        """
        tags = []
        filename_lower = filename.lower()

        # 关键词匹配
        for category, keywords in TAG_RULES["keywords"].items():
            for kw in keywords:
                if kw in filename_lower:
                    tags.append(category)
                    tags.append(kw)
                    break

        # 类型默认标签
        type_tags = TAG_RULES["type_defaults"].get(file_type, [])
        tags.extend(type_tags)

        # 去重
        return list(set(tags))[:10]

    def _get_media_info(
        self,
        file_path: str,
        file_type: str
    ) -> Tuple[Optional[float], Optional[int], Optional[int]]:
        """获取媒体信息

        Args:
            file_path: 文件路径
            file_type: 文件类型

        Returns:
            (时长, 宽度, 高度)
        """
        duration = None
        width = None
        height = None

        if file_type == "video":
            # 使用 ffprobe 获取视频信息
            try:
                import subprocess
                result = subprocess.run(
                    [
                        "ffprobe", "-v", "quiet", "-print_format", "json",
                        "-show_format", "-show_streams", file_path
                    ],
                    capture_output=True, text=True, timeout=10
                )
                data = json.loads(result.stdout)

                # 时长
                duration = float(data.get("format", {}).get("duration", 0))

                # 宽高
                for stream in data.get("streams", []):
                    if stream.get("codec_type") == "video":
                        width = stream.get("width")
                        height = stream.get("height")
                        break

            except Exception as e:
                logger.warning(f"获取视频信息失败: {e}")

        elif file_type == "image":
            # 获取图片尺寸
            try:
                from PIL import Image
                with Image.open(file_path) as img:
                    width, height = img.size
            except Exception as e:
                logger.warning(f"获取图片信息失败: {e}")

        elif file_type == "audio":
            # 获取音频时长
            try:
                import subprocess
                result = subprocess.run(
                    [
                        "ffprobe", "-v", "quiet", "-print_format", "json",
                        "-show_format", file_path
                    ],
                    capture_output=True, text=True, timeout=10
                )
                data = json.loads(result.stdout)
                duration = float(data.get("format", {}).get("duration", 0))
            except Exception as e:
                logger.warning(f"获取音频信息失败: {e}")

        return duration, width, height

    def search_assets(
        self,
        tags: List[str] = None,
        file_type: str = None,
        keyword: str = None
    ) -> List[UserAsset]:
        """搜索素材

        Args:
            tags: 标签列表（可选）
            file_type: 文件类型（可选）
            keyword: 关键词（可选）

        Returns:
            匹配的素材列表
        """
        results = []

        for asset_id, data in self.index.items():
            asset = UserAsset(**data)

            # 文件类型过滤
            if file_type and asset.file_type != file_type:
                continue

            # 标签过滤
            if tags:
                all_tags = asset.auto_tags + asset.user_tags
                if not any(t in all_tags for t in tags):
                    continue

            # 关键词过滤
            if keyword:
                keyword_lower = keyword.lower()
                if keyword_lower not in asset.filename.lower():
                    if not any(keyword_lower in t.lower() for t in asset.auto_tags + asset.user_tags):
                        continue

            results.append(asset)

        # 按使用次数排序（热门优先）
        results.sort(key=lambda x: x.use_count, reverse=True)
        return results

    def match_assets(
        self,
        visual_keywords: List[str],
        preferred_type: str = "video"
    ) -> List[UserAsset]:
        """匹配素材到关键词

        Args:
            visual_keywords: 视觉关键词
            preferred_type: 优先类型

        Returns:
            匹配的素材列表
        """
        # 先搜索用户素材
        user_assets = self.search_assets(tags=visual_keywords, file_type=preferred_type)

        if user_assets:
            logger.info(f"匹配用户素材: {len(user_assets)} 个")
            return user_assets

        # 没有匹配，返回空
        return []

    def get_asset(self, asset_id: str) -> UserAsset:
        """获取素材

        Args:
            asset_id: 素材 ID

        Returns:
            UserAsset 素材对象

        Raises:
            AssetNotFoundError: 素材不存在
        """
        if asset_id not in self.index:
            raise AssetNotFoundError(f"素材不存在: {asset_id}")

        return UserAsset(**self.index[asset_id])

    def update_asset_tags(
        self,
        asset_id: str,
        add_tags: List[str] = None,
        remove_tags: List[str] = None
    ) -> UserAsset:
        """更新素材标签

        Args:
            asset_id: 素材 ID
            add_tags: 添加的标签
            remove_tags: 移除的标签

        Returns:
            更新后的素材
        """
        asset = self.get_asset(asset_id)

        # 添加标签
        if add_tags:
            for tag in add_tags:
                if tag not in asset.user_tags:
                    asset.user_tags.append(tag)

        # 移除标签
        if remove_tags:
            asset.user_tags = [t for t in asset.user_tags if t not in remove_tags]

        # 更新索引
        self.index[asset_id] = asset.to_dict()
        self._save_index()

        logger.info(f"更新标签: {asset_id}, tags={asset.user_tags}")
        return asset

    def delete_asset(self, asset_id: str) -> bool:
        """删除素材

        Args:
            asset_id: 素材 ID

        Returns:
            是否成功
        """
        if asset_id not in self.index:
            return False

        asset_data = self.index[asset_id]
        file_path = Path(asset_data["file_path"])

        # 删除文件
        if file_path.exists():
            file_path.unlink()

        # 删除索引
        del self.index[asset_id]
        self._save_index()

        logger.info(f"素材删除: {asset_id}")
        return True

    def record_usage(self, asset_id: str):
        """记录素材使用

        Args:
            asset_id: 素材 ID
        """
        if asset_id not in self.index:
            return

        self.index[asset_id]["use_count"] += 1
        self.index[asset_id]["last_used"] = datetime.utcnow().isoformat()
        self._save_index()

    def get_stats(self) -> Dict[str, Any]:
        """获取素材库统计

        Returns:
            统计信息
        """
        stats = {
            "total_count": len(self.index),
            "by_type": {},
            "total_size": 0,
            "most_used": [],
        }

        for asset_id, data in self.index.items():
            file_type = data.get("file_type", "unknown")
            stats["by_type"][file_type] = stats["by_type"].get(file_type, 0) + 1
            stats["total_size"] += data.get("size", 0)

        # 最常用素材
        sorted_assets = sorted(
            self.index.items(),
            key=lambda x: x[1].get("use_count", 0),
            reverse=True
        )
        stats["most_used"] = [
            {"asset_id": a[0], "filename": a[1].get("filename"), "use_count": a[1].get("use_count")}
            for a in sorted_assets[:5]
        ]

        return stats


# 全局实例
_asset_manager = None


def get_asset_manager() -> AssetManager:
    """获取素材管理器实例"""
    global _asset_manager
    if _asset_manager is None:
        _asset_manager = AssetManager()
    return _asset_manager


def upload_asset(file_path: str, user_tags: List[str] = None) -> UserAsset:
    """上传素材（便捷函数）"""
    return get_asset_manager().upload_asset(file_path, user_tags)


def search_assets(tags: List[str] = None, file_type: str = None, keyword: str = None) -> List[UserAsset]:
    """搜索素材（便捷函数）"""
    return get_asset_manager().search_assets(tags, file_type, keyword)


def match_assets(visual_keywords: List[str], preferred_type: str = "video") -> List[UserAsset]:
    """匹配素材（便捷函数）"""
    return get_asset_manager().match_assets(visual_keywords, preferred_type)