#!/usr/bin/env python3
"""
Emotion Video Producer - Core Modules
"""

from .music_analyzer import analyze_music
from .narrative_generator import generate_narrative
from .visual_selector import select_visuals
from .transition_mapper import map_transitions
from .subtitle_sync import sync_subtitles
from .style_presets import get_style_preset
from .producer import produce_video
from .video_renderer import render_video, get_clip_info
from .multi_source_visual import download_from_multi_sources
from .music_selector import MusicSelector, get_music_selector, search_music, recommend_music
from .font_selector import FontSelector, get_font_selector, recommend_font
from .style_analyzer import StyleAnalyzer, get_style_analyzer, analyze_reference_style, generate_style_transfer_prompt
from .smart_recommender import SmartRecommender, get_smart_recommender, recommend_config
from .template_manager import TemplateManager, get_template_manager, list_templates, load_template, apply_template, create_template
from .asset_manager import AssetManager, get_asset_manager, upload_asset, search_assets, match_assets
from .multilingual_narrative import MultilingualNarrativeGenerator, get_multilingual_generator, generate_multilingual_narrative, translate_subtitle

__all__ = [
    "analyze_music",
    "generate_narrative",
    "select_visuals",
    "map_transitions",
    "sync_subtitles",
    "get_style_preset",
    "produce_video",
    "render_video",
    "get_clip_info",
    "download_from_multi_sources",
    "MusicSelector",
    "get_music_selector",
    "search_music",
    "recommend_music",
    "FontSelector",
    "get_font_selector",
    "recommend_font",
    "StyleAnalyzer",
    "get_style_analyzer",
    "analyze_reference_style",
    "generate_style_transfer_prompt",
    "SmartRecommender",
    "get_smart_recommender",
    "recommend_config",
    "TemplateManager",
    "get_template_manager",
    "list_templates",
    "load_template",
    "apply_template",
    "create_template",
    "AssetManager",
    "get_asset_manager",
    "upload_asset",
    "search_assets",
    "match_assets",
    "MultilingualNarrativeGenerator",
    "get_multilingual_generator",
    "generate_multilingual_narrative",
    "translate_subtitle",
]