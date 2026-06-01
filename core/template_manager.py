#!/usr/bin/env python3
"""
视频模板系统 — 预定义模板一键套用

支持：
1. list_templates — 列出所有模板
2. load_template — 加载模板
3. apply_template — 应用模板到 Session
4. create_template — 创建自定义模板
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from core.logging_config import get_logger
from core.exceptions import TemplateNotFoundError

logger = get_logger("template_manager")


TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


# 预定义模板
PREDEFINED_TEMPLATES = {
    # 节日模板
    "春节": {
        "name": "春节祝福",
        "category": "节日",
        "description": "适合春节祝福视频，红色喜庆风格",
        "style": "欢快",
        "visual_keywords": ["春节", "烟花", "灯笼", "红包", "团圆"],
        "transition_params": {
            "avg_duration": 0.15,
            "transition_type": "xfade",
        },
        "subtitle_style": {
            "fontsize": 48,
            "fontcolor": "red",
            "borderw": 2,
            "bold": False,
        },
        "music_tags": ["Happy", "Chinese Style", "Festival"],
        "default_bgm": "bgm_festival_01.mp3",
        "example_narration": "新春快乐，万事如意，阖家团圆，龙年大吉！",
    },
    "中秋": {
        "name": "中秋团圆",
        "category": "节日",
        "description": "适合中秋节祝福视频，温馨月光风格",
        "style": "治愈",
        "visual_keywords": ["月亮", "团圆", "月光", "月饼", "桂花"],
        "transition_params": {
            "avg_duration": 0.35,
            "transition_type": "fade",
        },
        "subtitle_style": {
            "fontsize": 36,
            "fontcolor": "white@0.9",
            "borderw": 1,
            "bold": False,
        },
        "music_tags": ["Calm", "Chinese Style", "Festival"],
        "default_bgm": "bgm_moon_01.mp3",
        "example_narration": "月圆人团圆，中秋佳节，祝您阖家幸福，美满团圆。",
    },
    "生日": {
        "name": "生日祝福",
        "category": "节日",
        "description": "适合生日祝福视频，欢乐温馨风格",
        "style": "欢快",
        "visual_keywords": ["生日蛋糕", "蜡烛", "礼物", "祝福", "欢笑"],
        "transition_params": {
            "avg_duration": 0.18,
            "transition_type": "xfade",
        },
        "subtitle_style": {
            "fontsize": 44,
            "fontcolor": "yellow",
            "borderw": 2,
            "bold": False,
        },
        "music_tags": ["Happy", "Birthday", "Celebration"],
        "default_bgm": "bgm_birthday_01.mp3",
        "example_narration": "生日快乐！愿你每一天都充满欢笑和幸福。",
    },

    # 商业模板
    "产品发布": {
        "name": "产品发布",
        "category": "商业",
        "description": "适合产品发布宣传视频，专业现代风格",
        "style": "励志",
        "visual_keywords": ["产品", "科技", "现代", "设计", "创新"],
        "transition_params": {
            "avg_duration": 0.20,
            "transition_type": "xfade",
        },
        "subtitle_style": {
            "fontsize": 42,
            "fontcolor": "white",
            "borderw": 2,
            "bold": True,
        },
        "music_tags": ["Dynamic", "Modern", "Electronic"],
        "default_bgm": "bgm_product_01.mp3",
        "example_narration": "创新设计，引领未来，为您呈现全新体验。",
    },
    "品牌故事": {
        "name": "品牌故事",
        "category": "商业",
        "description": "适合品牌故事宣传视频，大气叙事风格",
        "style": "文艺",
        "visual_keywords": ["品牌", "故事", "历程", "匠心", "传承"],
        "transition_params": {
            "avg_duration": 0.40,
            "transition_type": "fade",
        },
        "subtitle_style": {
            "fontsize": 38,
            "fontcolor": "white@0.85",
            "borderw": 1,
            "bold": False,
        },
        "music_tags": ["Calm", "Inspirational", "Corporate"],
        "default_bgm": "bgm_brand_01.mp3",
        "example_narration": "十年匠心，百年传承，用故事诠释品牌的温度。",
    },

    # 情感模板
    "表白": {
        "name": "表白告白",
        "category": "情感",
        "description": "适合表白告白视频，浪漫温馨风格",
        "style": "治愈",
        "visual_keywords": ["浪漫", "花朵", "日落", "心形", "温暖"],
        "transition_params": {
            "avg_duration": 0.35,
            "transition_type": "fade",
        },
        "subtitle_style": {
            "fontsize": 36,
            "fontcolor": "pink",
            "borderw": 1,
            "bold": False,
        },
        "music_tags": ["Calm", "Romantic", "Love"],
        "default_bgm": "bgm_love_01.mp3",
        "example_narration": "遇见你，是最美的意外。愿与你共度余生。",
    },
    "毕业": {
        "name": "毕业纪念",
        "category": "情感",
        "description": "适合毕业纪念视频，青春热血风格",
        "style": "热血",
        "visual_keywords": ["校园", "青春", "毕业", "梦想", "未来"],
        "transition_params": {
            "avg_duration": 0.12,
            "transition_type": "xfade",
        },
        "subtitle_style": {
            "fontsize": 52,
            "fontcolor": "white",
            "borderw": 3,
            "bold": True,
        },
        "music_tags": ["Dynamic", "Youth", "Graduation"],
        "default_bgm": "bgm_graduation_01.mp3",
        "example_narration": "青春不散场，梦想正启航。毕业不是终点，是新篇章的开始。",
    },

    # 生活模板
    "旅行": {
        "name": "旅行记录",
        "category": "生活",
        "description": "适合旅行记录视频，自由探索风格",
        "style": "欢快",
        "visual_keywords": ["旅行", "风景", "探索", "自由", "城市"],
        "transition_params": {
            "avg_duration": 0.18,
            "transition_type": "xfade",
        },
        "subtitle_style": {
            "fontsize": 40,
            "fontcolor": "cyan",
            "borderw": 2,
            "bold": False,
        },
        "music_tags": ["Happy", "Chill", "Travel"],
        "default_bgm": "bgm_travel_01.mp3",
        "example_narration": "每一次出发，都是一场新的冒险。记录旅途中的每一刻。",
    },
    "美食": {
        "name": "美食分享",
        "category": "生活",
        "description": "适合美食分享视频，温馨生活风格",
        "style": "欢快",
        "visual_keywords": ["美食", "烹饪", "食材", "餐厅", "味道"],
        "transition_params": {
            "avg_duration": 0.15,
            "transition_type": "xfade",
        },
        "subtitle_style": {
            "fontsize": 44,
            "fontcolor": "orange",
            "borderw": 2,
            "bold": False,
        },
        "music_tags": ["Happy", "Chill", "Lifestyle"],
        "default_bgm": "bgm_food_01.mp3",
        "example_narration": "美食治愈心灵，每一道菜都是一份用心。",
    },
}


class TemplateManager:
    """模板管理器"""

    def __init__(self, templates_dir: str = None):
        """初始化

        Args:
            templates_dir: 模板存储目录
        """
        self.templates_dir = Path(templates_dir) if templates_dir else TEMPLATES_DIR
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    def list_templates(self, category: str = None) -> List[Dict[str, Any]]:
        """列出所有模板

        Args:
            category: 模板类别（可选）

        Returns:
            模板列表
        """
        templates = []

        # 预定义模板
        for name, template in PREDEFINED_TEMPLATES.items():
            if category and template.get("category") != category:
                continue
            templates.append({
                "name": name,
                "display_name": template.get("name", name),
                "category": template.get("category", ""),
                "description": template.get("description", ""),
                "style": template.get("style", ""),
            })

        # 自定义模板
        for file_path in self.templates_dir.glob("*.template.json"):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if category and data.get("category") != category:
                    continue
                templates.append({
                    "name": data.get("name", ""),
                    "display_name": data.get("display_name", data.get("name", "")),
                    "category": data.get("category", ""),
                    "description": data.get("description", ""),
                    "style": data.get("style", ""),
                    "custom": True,
                })

        return templates

    def load_template(self, name: str) -> Dict[str, Any]:
        """加载模板

        Args:
            name: 模板名称

        Returns:
            模板配置

        Raises:
            TemplateNotFoundError: 模板不存在
        """
        # 先检查预定义模板
        if name in PREDEFINED_TEMPLATES:
            return PREDEFINED_TEMPLATES[name]

        # 检查自定义模板
        file_path = self.templates_dir / f"{name}.template.json"
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)

        raise TemplateNotFoundError(f"模板不存在: {name}")

    def apply_template(
        self,
        template_name: str,
        session_id: str,
        customizations: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """应用模板到 Session

        Args:
            template_name: 模板名称
            session_id: Session ID
            customizations: 自定义覆盖（可选）

        Returns:
            应用后的配置
        """
        template = self.load_template(template_name)

        # 基础配置
        config = {
            "style": template.get("style", "励志"),
            "visual_keywords": template.get("visual_keywords", []),
            "transition_params": template.get("transition_params", {}),
            "subtitle_style": template.get("subtitle_style", {}),
            "music_tags": template.get("music_tags", []),
        }

        # 应用自定义覆盖
        if customizations:
            for key, value in customizations.items():
                if key in config:
                    config[key] = value

        # 更新 Session
        from agent.session_store import get_session_store
        store = get_session_store()

        updates = {
            "style": config["style"],
            "visual_keywords": config["visual_keywords"],
        }

        store.update_session(session_id, updates)

        logger.info(f"模板应用: {template_name} → session={session_id}")
        return config

    def create_template(
        self,
        name: str,
        category: str,
        description: str,
        style: str,
        visual_keywords: List[str],
        transition_params: Dict[str, Any],
        subtitle_style: Dict[str, Any],
        music_tags: List[str],
        example_narration: str = None
    ) -> Dict[str, Any]:
        """创建自定义模板

        Args:
            各种模板参数

        Returns:
            创建的模板
        """
        template = {
            "name": name,
            "display_name": name,
            "category": category,
            "description": description,
            "style": style,
            "visual_keywords": visual_keywords,
            "transition_params": transition_params,
            "subtitle_style": subtitle_style,
            "music_tags": music_tags,
            "example_narration": example_narration or "",
            "created_at": datetime.utcnow().isoformat(),
        }

        # 保存到文件
        file_path = self.templates_dir / f"{name}.template.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(template, f, ensure_ascii=False, indent=2)

        logger.info(f"模板创建: {name}")
        return template

    def get_template_categories(self) -> List[str]:
        """获取所有模板类别

        Returns:
            类别列表
        """
        categories = set()

        for template in PREDEFINED_TEMPLATES.values():
            categories.add(template.get("category", ""))

        for file_path in self.templates_dir.glob("*.template.json"):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                categories.add(data.get("category", ""))

        return sorted(list(categories))


# 全局实例
_manager = None


def get_template_manager() -> TemplateManager:
    """获取模板管理器实例"""
    global _manager
    if _manager is None:
        _manager = TemplateManager()
    return _manager


def list_templates(category: str = None) -> List[Dict[str, Any]]:
    """列出模板（便捷函数）"""
    return get_template_manager().list_templates(category)


def load_template(name: str) -> Dict[str, Any]:
    """加载模板（便捷函数）"""
    return get_template_manager().load_template(name)


def apply_template(template_name: str, session_id: str, customizations: Dict = None) -> Dict[str, Any]:
    """应用模板（便捷函数）"""
    return get_template_manager().apply_template(template_name, session_id, customizations)


def create_template(**kwargs) -> Dict[str, Any]:
    """创建模板（便捷函数）"""
    return get_template_manager().create_template(**kwargs)