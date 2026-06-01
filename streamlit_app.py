#!/usr/bin/env python3
"""
Streamlit Web UI — Emotion Video Producer

功能：
- 侧边栏：系统配置、素材管理、模板选择
- 主界面：内容输入、语音设置、视觉设置
- 实时进度显示
- 历史记录页面
- 模板预览

用法:
    streamlit run streamlit_app.py
"""

import os
import sys
import json
import tempfile
import uuid
from pathlib import Path
from datetime import datetime

import streamlit as st

# 设置页面配置
st.set_page_config(
    page_title="Emotion Video Producer",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    DASHSCOPE_API_KEY,
    PEXELS_API_KEY,
    PIXABAY_API_KEY,
    DEFAULT_TTS_PROVIDER,
    DEFAULT_VOICE,
    DEFAULT_TTS_SPEED,
    SUBTITLE_STYLE_LIST,
    SUBTITLE_STYLES,
)
from config import TEMPLATE_DIR as config_template_dir
from core.template_engine import list_templates, get_template_config, TEMPLATE_DIR
from core.tts_provider import get_tts_provider, EdgeTTSProvider, DashscopeTTSProvider
from core.style_presets import STYLE_PRESETS, get_style_preset


# ── Session State 初始化 ──

if "history" not in st.session_state:
    st.session_state.history = []

if "current_progress" not in st.session_state:
    st.session_state.current_progress = 0

if "current_step" not in st.session_state:
    st.session_state.current_step = ""

if "uploaded_assets" not in st.session_state:
    st.session_state.uploaded_assets = []

if "selected_subtitle_style" not in st.session_state:
    st.session_state.selected_subtitle_style = "impact"


# ── 配置持久化 ──

CONFIG_FILE = Path.home() / ".emotion-video-producer" / "config.json"


def _load_config_from_file():
    """从文件加载持久化配置"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config
        except Exception:
            pass
    return {}


def _save_config_to_file(dashscope_key: str, pexels_key: str, pixabay_key: str):
    """保存配置到文件"""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    config = {
        "DASHSCOPE_API_KEY": dashscope_key,
        "PEXELS_API_KEY": pexels_key,
        "PIXABAY_API_KEY": pixabay_key,
    }
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"配置保存失败: {e}")


# 启动时加载持久化配置
_saved_config = _load_config_from_file()
if _saved_config:
    os.environ["DASHSCOPE_API_KEY"] = _saved_config.get("DASHSCOPE_API_KEY", "")
    os.environ["PEXELS_API_KEY"] = _saved_config.get("PEXELS_API_KEY", "")
    os.environ["PIXABAY_API_KEY"] = _saved_config.get("PIXABAY_API_KEY", "")


# ── 侧边栏 ──

with st.sidebar:
    st.title("⚙️ 配置")

    # ── 系统配置 ──
    with st.expander("🔑 API 配置", expanded=False):
        dashscope_key = st.text_input(
            "Dashscope API Key",
            value=DASHSCOPE_API_KEY or "",
            type="password",
            help="用于 AI 文案生成和视觉分析",
        )

        pexels_key = st.text_input(
            "Pexels API Key",
            value=PEXELS_API_KEY or "",
            type="password",
            help="用于视频素材下载",
        )

        pixabay_key = st.text_input(
            "Pixabay API Key",
            value=PIXABAY_API_KEY or "",
            type="password",
            help="用于视频素材备选下载",
        )

        if st.button("保存配置"):
            os.environ["DASHSCOPE_API_KEY"] = dashscope_key
            os.environ["PEXELS_API_KEY"] = pexels_key
            os.environ["PIXABAY_API_KEY"] = pixabay_key
            # 持久化保存配置
            _save_config_to_file(dashscope_key, pexels_key, pixabay_key)
            st.success("配置已保存并持久化")

    # ── 字幕样式配置 ──
    with st.expander("📝 字幕样式", expanded=False):
        subtitle_style_options = [s["name"] for s in SUBTITLE_STYLE_LIST]
        subtitle_style_descriptions = {s["name"]: s["description"] for s in SUBTITLE_STYLE_LIST}

        selected_subtitle_style = st.selectbox(
            "字幕样式",
            options=subtitle_style_options,
            index=0,
            help="选择字幕显示样式",
        )

        st.caption(subtitle_style_descriptions.get(selected_subtitle_style, ""))

        # 字幕预览
        st.markdown(f"""
        <div style="background:#000;padding:20px;text-align:center;border-radius:8px;">
            <span style="font-size:24px;color:{SUBTITLE_STYLES[selected_subtitle_style]['fontcolor']};">
                字幕样式预览
            </span>
        </div>
        """, unsafe_allow_html=True)

    # ── TTS 配置 ──
    with st.expander("🎤 TTS 配置", expanded=False):
        tts_provider = st.selectbox(
            "TTS 提供者",
            options=["edge", "dashscope", "cosyvoice"],
            index=0 if DEFAULT_TTS_PROVIDER == "edge" else (1 if DEFAULT_TTS_PROVIDER == "dashscope" else 2),
            help="Edge-TTS 免费，Dashscope 需付费，CosyVoice 本地模型",
        )

        # 获取可用语音
        tts = get_tts_provider(tts_provider)
        voices = tts.get_available_voices()

        voice_options = [v["name"] for v in voices]
        voice_descriptions = {v["name"]: v["description"] for v in voices}

        selected_voice = st.selectbox(
            "语音选择",
            options=voice_options,
            index=0,
            help="选择旁白音色",
        )

        st.caption(voice_descriptions.get(selected_voice, ""))

        tts_speed = st.slider(
            "语速",
            min_value=0.5,
            max_value=2.0,
            value=1.0,
            step=0.1,
        )

        # TTS 预览
        preview_text = st.text_input("预览文本", value="这是一段测试语音")
        if st.button("🔊 试听语音"):
            with st.spinner("生成语音..."):
                try:
                    temp_audio = tempfile.mktemp(suffix=".mp3")
                    result = tts.synthesize(preview_text, temp_audio, selected_voice, tts_speed)
                    if result:
                        st.audio(temp_audio)
                        os.remove(temp_audio)
                    else:
                        st.error("语音生成失败")
                except Exception as e:
                    st.error(f"错误: {e}")

    # ── 模板选择 ──
    with st.expander("🎨 模板选择", expanded=False):
        template_category = st.selectbox(
            "模板类型",
            options=["全部", "static", "image", "video"],
            index=0,
        )

        # 获取模板列表
        templates = list_templates(
            category=template_category if template_category != "全部" else None
        )

        template_names = [t["name"] for t in templates]
        selected_template = st.selectbox(
            "选择模板",
            options=template_names,
            index=0,
        )

        # 模板信息
        template_info = next((t for t in templates if t["name"] == selected_template), None)
        if template_info:
            st.caption(f"类型: {template_info['type']}")
            st.caption(f"转场: {template_info['transition_type']} ({template_info['transition_duration']}s)")

        # 模板预览按钮
        if st.button("👁️ 预览模板"):
            st.session_state.show_template_preview = True

    # ── 素材管理 ──
    with st.expander("📁 用户素材", expanded=False):
        st.caption("上传自己的图片/视频，AI 将智能分析生成脚本")

        uploaded_files = st.file_uploader(
            "上传素材",
            type=["jpg", "jpeg", "png", "webp", "mp4", "mov"],
            accept_multiple_files=True,
        )

        if uploaded_files:
            st.session_state.uploaded_assets = []

            for f in uploaded_files:
                # 保存临时文件
                temp_path = tempfile.mktemp(suffix=f.name)
                with open(temp_path, "wb") as out:
                    out.write(f.read())

                st.session_state.uploaded_assets.append({
                    "name": f.name,
                    "path": temp_path,
                    "type": "image" if f.name.endswith((".jpg", ".jpeg", ".png", ".webp")) else "video",
                })

            st.success(f"已上传 {len(uploaded_files)} 个素材")

            # 显示已上传素材
            for asset in st.session_state.uploaded_assets:
                st.text(f"• {asset['name']} ({asset['type']})")

        # 分析素材按钮
        if st.session_state.uploaded_assets and st.button("🤖 AI 分析素材"):
            st.session_state.show_asset_analysis = True

    # ── 历史记录 ──
    with st.expander("📜 历史记录", expanded=False):
        if st.session_state.history:
            for record in st.session_state.history[-5:]:
                st.text(f"{record['time']}: {record['theme']}")
        else:
            st.text("暂无历史记录")


# ── 主界面 ──

st.title("🎬 Emotion Video Producer")
st.markdown("情感驱动视频生产系统 — 根据音乐情感自动生成短视频")

# ── 模板预览弹窗 ──

if st.session_state.get("show_template_preview"):
    with st.container():
        st.subheader(f"模板预览: {selected_template}")

        # 获取模板配置
        template_config = get_template_config(selected_template)

        col1, col2 = st.columns(2)

        with col1:
            st.json(template_config.get("ffmpeg_params", {}))

        with col2:
            # 模板预览 HTML
            template_path = Path(TEMPLATE_DIR) / f"{selected_template}.html"
            if template_path.exists():
                with open(template_path, "r", encoding="utf-8") as f:
                    html_content = f.read()

                # 显示模板 HTML（简化）
                st.markdown("**CSS 变量:**")
                css_vars = template_config
                for key, value in css_vars.items():
                    if not key.startswith("_") and not isinstance(value, dict):
                        st.text(f"--{key}: {value}")

        if st.button("关闭预览"):
            st.session_state.show_template_preview = False
            st.rerun()

# ── 素材分析弹窗 ──

if st.session_state.get("show_asset_analysis"):
    with st.container():
        st.subheader("🤖 AI 素材分析结果")

        from core.user_asset_analyzer import analyze_image, analyze_video, AssetAnalysis
        from dataclasses import asdict

        analyses = []
        progress_bar = st.progress(0)

        for i, asset in enumerate(st.session_state.uploaded_assets):
            progress_bar.progress((i + 1) / len(st.session_state.uploaded_assets))

            with st.spinner(f"分析 {asset['name']}..."):
                try:
                    if asset["type"] == "image":
                        analysis = analyze_image(asset["path"])
                    else:
                        analysis = analyze_video(asset["path"])

                    analyses.append(analysis)

                    st.json(asdict(analysis))
                except Exception as e:
                    st.error(f"分析失败: {e}")

        progress_bar.empty()

        if analyses:
            st.success(f"分析完成: {len(analyses)} 个素材")

            # 显示建议
            suggested_style = analyses[0].suggested_style
            st.info(f"建议风格: {suggested_style}")

        if st.button("关闭分析"):
            st.session_state.show_asset_analysis = False
            st.rerun()


# ── 内容输入 ──

st.header("01 / 内容输入")

col1, col2 = st.columns(2)

with col1:
    theme = st.text_input(
        "视频主题",
        value="东京夜行",
        help="输入视频主题关键词",
    )

with col2:
    style_preset = st.selectbox(
        "风格预设",
        options=list(STYLE_PRESETS.keys()),
        index=1,  # 默认励志
    )

    preset_info = STYLE_PRESETS[style_preset]
    st.caption(preset_info["description"])

# BGM 上传
bgm_file = st.file_uploader(
    "背景音乐",
    type=["mp3", "wav", "m4a", "aac"],
    help="上传背景音乐文件",
)

if bgm_file:
    st.audio(bgm_file)
    st.caption(f"已上传: {bgm_file.name}")

# 自定义文案（可选）
use_custom_narration = st.checkbox("使用自定义文案")
narration_text = ""

if use_custom_narration:
    narration_text = st.text_area(
        "旁白文案",
        value="",
        help="输入自定义旁白文案，每行一段",
        height=150,
    )


# ── 视觉设置 ──

st.header("02 / 视觉设置")

col1, col2, col3, col4 = st.columns(4)

with col1:
    use_user_assets = st.checkbox(
        "使用用户素材",
        value=len(st.session_state.uploaded_assets) > 0,
        disabled=len(st.session_state.uploaded_assets) == 0,
    )

with col2:
    visual_mode = st.selectbox(
        "素材来源",
        options=["auto", "pexels", "generate"],
        index=0,
        help="auto: 自动选择，pexels: 从素材库下载，generate: AI 生成背景",
    )

with col3:
    # 统一风格选择（抖音推荐）
    unified_style = st.selectbox(
        "素材风格",
        options=["动态（根据能量变化）", "城市风格", "自然风格", "夜景风格", "电影风格", "旅行风格"],
        index=0,
        help="统一风格：所有素材同类型（推荐抖音）；动态：根据音乐能量变化素材类型",
    )

with col4:
    video_size = st.selectbox(
        "视频尺寸",
        options=["横屏 1920x1080", "竖屏 1080x1920", "方形 1080x1080"],
        index=0,
    )

# 解析风格
style_map = {
    "动态（根据能量变化）": None,
    "城市风格": "city",
    "自然风格": "nature",
    "夜景风格": "night",
    "电影风格": "cinematic",
    "旅行风格": "travel",
}
unified_style_value = style_map[unified_style]

# 尺寸解析
size_map = {
    "横屏 1920x1080": (1920, 1080),
    "竖屏 1080x1920": (1080, 1920),
    "方形 1080x1080": (1080, 1080),
}
width, height = size_map[video_size]


# ── 生产视频 ──

st.header("03 / 开始生产")

st.markdown("点击按钮开始生产视频，进度将实时显示")

if st.button("🎬 生成视频", type="primary"):
    if not theme:
        st.error("请输入视频主题")
    elif not bgm_file:
        st.error("请上传背景音乐")
    else:
        # 保存 BGM
        bgm_path = tempfile.mktemp(suffix=".mp3")
        with open(bgm_path, "wb") as f:
            f.write(bgm_file.read())

        # 创建输出目录
        output_dir = Path(tempfile.gettempdir()) / "emotion-video-output"
        output_dir.mkdir(exist_ok=True)

        output_path = str(output_dir / f"{theme}_{uuid.uuid4()}.mp4")

        # 进度显示
        progress_bar = st.progress(0)
        status_text = st.empty()

        steps = [
            ("音乐分析", 10),
            ("AI 叙事", 20),
            ("视觉素材", 40),
            ("转场映射", 50),
            ("字幕同步", 60),
            ("TTS 生成", 70),
            ("素材下载", 85),
            ("视频渲染", 100),
        ]

        try:
            from core.producer import produce_video

            # 模拟进度更新（实际应该在 producer 中实现）
            for step_name, progress in steps:
                status_text.text(f"正在执行: {step_name}")
                progress_bar.progress(progress)

            # 获取模板配置
            template_styles = None
            if selected_template:
                template_config = get_template_config(selected_template)
                template_styles = template_config.get("ffmpeg_params")

            # 调用生产函数
            result = produce_video(
                theme=theme,
                bgm_path=bgm_path,
                output_path=output_path,
                style=style_preset,
                voice=selected_voice,
                tts_speed=tts_speed,
                tts_provider=tts_provider,
                visual_mode=visual_mode,
                unified_style=unified_style_value,
                subtitle_style=selected_subtitle_style,  # 添加字幕样式参数
            )

            progress_bar.progress(100)
            status_text.text("✅ 完成!")

            if result:
                # 记录历史
                st.session_state.history.append({
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "theme": theme,
                    "style": style_preset,
                    "output": result,
                })

                # 显示输出
                st.success("视频生成成功!")

                st.video(result)

                # 下载按钮
                with open(result, "rb") as f:
                    st.download_button(
                        "📥 下载视频",
                        f,
                        file_name=f"{theme}.mp4",
                        mime="video/mp4",
                    )
            else:
                st.error("视频生成失败")

        except Exception as e:
            st.error(f"生产错误: {e}")
            progress_bar.empty()
            status_text.empty()

        finally:
            # 清理临时 BGM
            try:
                os.remove(bgm_path)
            except Exception:
                pass


# ── 页脚 ──

st.markdown("---")
st.markdown(
    "Emotion Video Producer — 情感驱动视频生产系统 | "
    "[GitHub](https://github.com/anthropics/claude-code) | "
    "Powered by Claude Code"
)