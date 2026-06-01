#!/usr/bin/env python3
"""
Web API 服务 — 为前端提供视频生产接口

支持：
1. 同步生产（原有）
2. 异步生产（Celery）
3. WebSocket 进度推送
4. Skill 管理
5. 风格迁移
"""

import json
import os
import tempfile
import uuid
from pathlib import Path

from flask import Flask, request, jsonify, send_file, send_from_directory
from pathlib import Path
import json

app = Flask(__name__)

# 配置
UPLOAD_DIR = Path(tempfile.gettempdir()) / "emotion-video-uploads"
OUTPUT_DIR = Path(tempfile.gettempdir()) / "emotion-video-output"
CONFIG_DIR = Path.home() / ".emotion-video-producer"
CONFIG_FILE = CONFIG_DIR / "config.json"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
CONFIG_DIR.mkdir(exist_ok=True)

# 设置 API Keys
os.environ["PEXELS_API_KEY"] = os.environ.get("PEXELS_API_KEY", "")
os.environ["PIXABAY_API_KEY"] = os.environ.get("PIXABAY_API_KEY", "")
os.environ["DASHSCOPE_API_KEY"] = os.environ.get("DASHSCOPE_API_KEY", "")
os.environ["MOSS_API_KEY"] = os.environ.get("MOSS_API_KEY", "")

# 导入核心模块
from core.producer import produce_video
from core.logging_config import get_logger

logger = get_logger("web_api")

# 设置 WebSocket
from websocket_service import setup_websocket
setup_websocket(app)


# ── 静态文件 ──

@app.route("/")
def index():
    return send_from_directory("web", "index.html")


@app.route("/web/<path:path>")
def static_files(path):
    return send_from_directory("web", path)


# ── 配置 API ──

@app.route("/api/config/save", methods=["POST"])
def save_config():
    """保存 API 配置到文件"""
    data = request.json

    config = {
        "DASHSCOPE_API_KEY": data.get("DASHSCOPE_API_KEY", ""),
        "MOSS_API_KEY": data.get("MOSS_API_KEY", ""),
        "PEXELS_API_KEY": data.get("PEXELS_API_KEY", ""),
        "PIXABAY_API_KEY": data.get("PIXABAY_API_KEY", ""),
    }

    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        # 同时设置环境变量
        os.environ["DASHSCOPE_API_KEY"] = config["DASHSCOPE_API_KEY"]
        os.environ["MOSS_API_KEY"] = config["MOSS_API_KEY"]
        os.environ["PEXELS_API_KEY"] = config["PEXELS_API_KEY"]
        os.environ["PIXABAY_API_KEY"] = config["PIXABAY_API_KEY"]

        return jsonify({"success": True, "message": "配置已保存"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/config/load", methods=["GET"])
def load_config():
    """加载已保存的配置"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)

            # 设置环境变量
            os.environ["DASHSCOPE_API_KEY"] = config.get("DASHSCOPE_API_KEY", "")
            os.environ["MOSS_API_KEY"] = config.get("MOSS_API_KEY", "")
            os.environ["PEXELS_API_KEY"] = config.get("PEXELS_API_KEY", "")
            os.environ["PIXABAY_API_KEY"] = config.get("PIXABAY_API_KEY", "")

            return jsonify({"success": True, "config": config})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    return jsonify({"success": True, "config": {}})


# ── API 接口 ──

@app.route("/api/upload", methods=["POST"])
def upload_file():
    """上传音频文件"""

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    # 保存文件
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1]
    file_path = UPLOAD_DIR / f"{file_id}{ext}"
    file.save(file_path)

    return jsonify({
        "success": True,
        "file_id": file_id,
        "file_path": str(file_path),
        "filename": file.filename
    })


@app.route("/api/narrative/generate", methods=["POST"])
def generate_narrative_preview():
    """生成叙事文案预览（不执行完整生产）"""

    data = request.json
    theme = data.get("theme", "")
    bgm_path = data.get("bgm_path", "")
    style = data.get("style", "励志")

    if not theme:
        return jsonify({"error": "请输入视频主题"}), 400

    if not bgm_path or not os.path.exists(bgm_path):
        return jsonify({"error": "请上传背景音乐"}), 400

    from core.music_analyzer import analyze_music
    from core.narrative_generator import generate_narrative as _generate_narrative
    from core.style_presets import apply_preset_to_analysis
    import tempfile

    try:
        # 音乐分析
        analysis = analyze_music(bgm_path)
        if analysis is None:
            return jsonify({"error": "音乐分析失败"}), 500

        # 应用风格预设
        if style:
            analysis = apply_preset_to_analysis(analysis, style)

        # 生成叙事
        narrative = _generate_narrative(theme, analysis, style)
        if narrative is None:
            return jsonify({"error": "叙事生成失败"}), 500

        return jsonify({
            "success": True,
            "narrative": {
                "title_text": narrative.get("title_text", theme),
                "narration_script": narrative.get("narration_script", ""),
                "segments": narrative.get("segments", []),
            },
            "analysis": {
                "duration": analysis.get("duration", 0),
                "recommended_style": analysis.get("recommended_style", ""),
                "energy_peaks": analysis.get("energy_peaks", []),
            }
        })
    except Exception as e:
        logger.error(f"文案生成失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/tts/generate", methods=["POST"])
def generate_tts_preview():
    """生成 TTS 语音预览"""

    data = request.json
    text = data.get("text", "")
    voice = data.get("voice", "longxiaochun")
    tts_provider = data.get("tts_provider", "moss")
    tts_instruction = data.get("tts_instruction", "")

    if not text:
        return jsonify({"error": "请提供文本"}), 400

    from core.tts import text_to_speech, get_audio_duration
    import tempfile

    try:
        # 生成音频文件（保存到 OUTPUT_DIR）
        audio_id = str(uuid.uuid4())
        audio_path = str(OUTPUT_DIR / f"tts_preview_{audio_id}.wav")

        result = text_to_speech(text, audio_path, voice, 1.0, tts_provider, tts_instruction)

        if result:
            duration = get_audio_duration(audio_path)
            # 返回预览 URL
            return jsonify({
                "success": True,
                "audio_id": audio_id,
                "duration": duration,
                "preview_url": f"/api/tts/preview/{audio_id}"
            })
        else:
            return jsonify({"error": "TTS 生成失败"}), 500
    except Exception as e:
        logger.error(f"TTS 生成失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/tts/preview/<audio_id>")
def preview_tts(audio_id):
    """预览 TTS 音频"""

    audio_path = OUTPUT_DIR / f"tts_preview_{audio_id}.wav"

    if not audio_path.exists():
        return jsonify({"error": "音频文件不存在"}), 404

    return send_file(str(audio_path), mimetype="audio/wav")


@app.route("/api/music/energy-preview", methods=["POST"])
def energy_preview():
    """快速能量分析预览"""

    data = request.json
    bgm_path = data.get("bgm_path", "")
    duration_limit = data.get("duration_limit", 30)
    mode = data.get("mode", "short")

    if not bgm_path:
        return jsonify({"error": "缺少 BGM 文件路径"}), 400

    try:
        from core.music_analyzer import analyze_music

        # 快速分析（不保存完整结果）
        analysis = analyze_music(bgm_path, None)

        if analysis:
            # 简化返回数据
            result = {
                "duration": min(analysis.get("duration", 30), duration_limit),
                "energy_level": analysis.get("energy_level", "medium"),
                "energy_peaks": analysis.get("energy_peaks", [])[:5],  # 只返回前5个峰值
                "recommended_style": analysis.get("recommended_style", "励志"),
                "segment_count_estimate": int(min(analysis.get("duration", 30), duration_limit) / 2),
            }

            return jsonify({"success": True, "analysis": result})
        else:
            return jsonify({"error": "音乐分析失败"}), 500

    except Exception as e:
        logger.error(f"能量分析预览失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/produce", methods=["POST"])
def produce():
    """生产视频（同步，带进度推送）"""

    data = request.json

    theme = data.get("theme", "")
    bgm_path = data.get("bgm_path", "")
    style = data.get("style", "励志")
    voice = data.get("voice", "longxiaochun")
    tts_provider = data.get("tts_provider", "moss")  # 默认使用 MOSS-TTS
    tts_instruction = data.get("tts_instruction", "")  # MOSS-TTS 语音指令
    visual_mode = data.get("visual_mode", "auto")
    subtitle_style = data.get("subtitle_style", "impact")  # 字幕样式参数
    ratio = data.get("ratio", "16:9")  # 视频比例参数
    session_id = data.get("session_id", None)  # 前端传来的 session_id

    # 30s 短视频参数
    mode = data.get("mode", "normal")  # normal/short
    duration_limit = data.get("duration_limit", None)  # 时长限制 (秒)
    transition_intensity = data.get("transition_intensity", "normal")  # normal/fast/cinematic
    segment_count = data.get("segment_count", None)  # 片段数量

    # 用户确认的文案参数（优先使用）
    title_text = data.get("title_text", None)  # 用户确认的标题
    narration_script = data.get("narration_script", None)  # 用户确认的旁白

    if not theme:
        return jsonify({"error": "请输入视频主题"}), 400

    if not bgm_path:
        return jsonify({"error": "请上传背景音乐"}), 400

    if not os.path.exists(bgm_path):
        return jsonify({"error": "音乐文件不存在"}), 400

    # 根据比例计算尺寸
    if ratio == "9:16":
        width, height = 1080, 1920  # 竖版视频
    else:
        width, height = 1920, 1080  # 横版视频（默认 16:9）

    # 生成输出路径和 session_id
    output_id = session_id or str(uuid.uuid4())
    output_path = OUTPUT_DIR / f"{output_id}.mp4"

    # 调用生产流水线（带进度推送）
    try:
        result = produce_video(
            theme=theme,
            bgm_path=bgm_path,
            style=style,
            voice=voice,
            tts_provider=tts_provider,
            tts_instruction=tts_instruction,  # MOSS-TTS 语音指令
            visual_mode=visual_mode,
            subtitle_style=subtitle_style,  # 添加字幕样式参数
            width=width,
            height=height,
            session_id=output_id,  # 用于进度推送
            output_path=str(output_path),
            keep_temp=False,
            # 30s 短视频参数
            mode=mode,
            duration_limit=duration_limit,
            transition_intensity=transition_intensity,
            segment_count=segment_count,
            # 用户确认的文案（优先使用）
            title_text=title_text,
            narration_script=narration_script,
        )

        if result:
            return jsonify({
                "success": True,
                "output_id": output_id,
                "output_path": str(output_path),
                "download_url": f"/api/download/{output_id}"
            })
        else:
            return jsonify({"error": "视频生产失败"}), 500

    except Exception as e:
        logger.error(f"生产失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/produce_async", methods=["POST"])
def produce_async():
    """生产视频（异步 Celery 任务）"""

    data = request.json

    theme = data.get("theme", "")
    bgm_path = data.get("bgm_path", "")
    style = data.get("style", "励志")
    voice = data.get("voice", "longxiaochun")
    tts_speed = data.get("tts_speed", 1.0)
    visual_mode = data.get("visual_mode", "auto")
    style_profile = data.get("style_profile", None)

    if not theme:
        return jsonify({"error": "请输入视频主题"}), 400

    if not bgm_path:
        return jsonify({"error": "请上传背景音乐"}), 400

    if not os.path.exists(bgm_path):
        return jsonify({"error": "音乐文件不存在"}), 400

    # 生成输出路径
    output_id = str(uuid.uuid4())
    output_path = str(OUTPUT_DIR / f"{output_id}.mp4")

    # 调用 Celery 任务
    from tasks import produce_video_task

    task = produce_video_task.delay(
        theme=theme,
        bgm_path=bgm_path,
        output_path=output_path,
        style=style,
        voice=voice,
        tts_speed=tts_speed,
        visual_mode=visual_mode,
        style_profile=style_profile
    )

    logger.info(f"异步任务启动: task_id={task.id}")

    return jsonify({
        "success": True,
        "task_id": task.id,
        "output_id": output_id,
        "ws_url": f"/ws/progress/{task.id}"  # WebSocket 进度推送
    })


@app.route("/api/task_status/<task_id>")
def task_status(task_id):
    """查询异步任务状态"""

    from tasks import get_task_status

    status = get_task_status(task_id)

    return jsonify(status)


@app.route("/api/download/<output_id>")
def download(output_id):
    """下载视频"""

    output_path = OUTPUT_DIR / f"{output_id}.mp4"

    if not output_path.exists():
        return jsonify({"error": "视频不存在"}), 404

    return send_file(output_path, as_attachment=True, download_name="output.mp4")


@app.route("/api/status/<output_id>")
def status(output_id):
    """查询生产状态"""

    output_path = OUTPUT_DIR / f"{output_id}.mp4"

    if output_path.exists():
        size = output_path.stat().st_size
        return jsonify({
            "status": "completed",
            "size": size,
            "download_url": f"/api/download/{output_id}"
        })
    else:
        return jsonify({"status": "pending"})


# ── Skill 管理 ──

@app.route("/api/skills", methods=["GET"])
def list_skills():
    """列出所有 Skills"""

    from skills.serializer import list_skills

    skills = list_skills()

    return jsonify({
        "success": True,
        "skills": skills
    })


@app.route("/api/skills/<name>", methods=["GET"])
def get_skill(name):
    """获取 Skill 详情"""

    from skills.serializer import load_skill

    try:
        skill = load_skill(name)
        return jsonify({
            "success": True,
            "skill": skill.dict()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 404


@app.route("/api/sessions/<session_id>/save_skill", methods=["POST"])
def save_session_as_skill(session_id):
    """将 Session workflow 保存为 Skill"""

    data = request.json
    name = data.get("name", "")
    description = data.get("description", "")

    if not name:
        return jsonify({"error": "请输入 Skill 名称"}), 400

    from skills.serializer import save_workflow_as_skill

    try:
        skill = save_workflow_as_skill(session_id, name, description)
        return jsonify({
            "success": True,
            "skill": skill.dict()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sessions/<session_id>/apply_skill/<skill_name>", methods=["POST"])
def apply_skill_to_session(session_id, skill_name):
    """将 Skill 应用到 Session"""

    from skills.serializer import get_skill_serializer

    try:
        serializer = get_skill_serializer()
        state = serializer.apply_skill_to_session(skill_name, session_id)
        return jsonify({
            "success": True,
            "session": state.dict()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── 风格迁移 ──

@app.route("/api/style/analyze", methods=["POST"])
def analyze_style():
    """分析参考文本风格"""

    data = request.json
    text = data.get("text", "")

    if not text:
        return jsonify({"error": "请输入参考文本"}), 400

    from core.style_analyzer import analyze_reference_style

    try:
        profile = analyze_reference_style(text)
        return jsonify({
            "success": True,
            "style_profile": profile.to_dict()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/voice/recommend", methods=["POST"])
def recommend_voice():
    """根据文案推荐音色"""

    data = request.json
    narrative = data.get("narrative", "")
    style = data.get("style", None)
    music_analysis = data.get("music_analysis", None)

    if not narrative:
        return jsonify({"error": "请提供文案"}), 400

    from core.voice_selector import select_voice

    try:
        result = select_voice(narrative, style, music_analysis)
        return jsonify({
            "success": True,
            "recommendation": result
        })
    except Exception as e:
        logger.error(f"音色推荐失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/voice/templates", methods=["GET"])
def get_voice_templates():
    """获取 MOSS-TTS 模板列表"""

    from core.voice_selector import MOSS_TTS_TEMPLATES

    return jsonify({
        "success": True,
        "templates": MOSS_TTS_TEMPLATES
    })


@app.route("/api/voice/library", methods=["GET"])
def get_voice_library():
    """获取音色库列表"""

    from core.voice_selector import VOICE_LIBRARY

    voices = [
        {
            "voice_id": v.voice_id,
            "gender": v.gender,
            "age": v.age,
            "tone": v.tone,
            "language": v.language,
            "description": v.description,
            "tts_instruction": v.tts_instruction,
        }
        for v in VOICE_LIBRARY.values()
    ]

    return jsonify({
        "success": True,
        "voices": voices
    })


@app.route("/api/voice/generate-instruction", methods=["POST"])
def generate_voice_instruction():
    """生成自定义 MOSS-TTS 指令"""

    data = request.json
    voice_id = data.get("voice_id", "")
    speed_template = data.get("speed_template", None)
    pause_template = data.get("pause_template", None)
    emotion_template = data.get("emotion_template", None)

    from core.voice_selector import VOICE_LIBRARY, generate_custom_instruction

    voice_profile = VOICE_LIBRARY.get(voice_id)
    if not voice_profile:
        return jsonify({"error": "音色不存在"}), 400

    instruction = generate_custom_instruction(
        voice_profile,
        speed_template,
        pause_template,
        emotion_template
    )

    return jsonify({
        "success": True,
        "instruction": instruction
    })


@app.route("/api/music/search", methods=["GET"])
def search_music():
    """搜索音乐"""

    mood = request.args.get("mood", "")
    scene = request.args.get("scene", "")
    genre = request.args.get("genre", "")
    bpm_min = request.args.get("bpm_min", type=int)
    bpm_max = request.args.get("bpm_max", type=int)

    from core.music_selector import search_music

    results = search_music(mood, scene, genre, bpm_min, bpm_max)

    return jsonify({
        "success": True,
        "results": results
    })


@app.route("/api/music/recommend", methods=["GET"])
def recommend_music():
    """推荐音乐"""

    style = request.args.get("style", "励志")
    count = request.args.get("count", default=3, type=int)

    from core.music_selector import recommend_music

    results = recommend_music(style, None, count)

    return jsonify({
        "success": True,
        "results": results
    })


@app.route("/api/font/recommend", methods=["GET"])
def recommend_font():
    """推荐字体"""

    style = request.args.get("style", "励志")

    from core.font_selector import recommend_font

    results = recommend_font(style)

    return jsonify({
        "success": True,
        "results": results
    })


# ── 智能推荐 ──

@app.route("/api/recommend", methods=["POST"])
def recommend_config():
    """智能推荐配置"""

    data = request.json
    theme = data.get("theme", "")
    music_analysis = data.get("music_analysis", None)

    if not theme:
        return jsonify({"error": "请输入视频主题"}), 400

    from core.smart_recommender import recommend_config

    config = recommend_config(theme, music_analysis)

    return jsonify({
        "success": True,
        "recommendation": config.to_dict()
    })


# ── 模板管理 ──

@app.route("/api/templates", methods=["GET"])
def list_templates():
    """列出模板"""

    category = request.args.get("category", None)

    from core.template_manager import list_templates

    templates = list_templates(category)

    return jsonify({
        "success": True,
        "templates": templates
    })


@app.route("/api/templates/<name>", methods=["GET"])
def get_template(name):
    """获取模板详情"""

    from core.template_manager import load_template

    try:
        template = load_template(name)
        return jsonify({
            "success": True,
            "template": template
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 404


@app.route("/api/templates/<name>/apply", methods=["POST"])
def apply_template_to_session(name):
    """应用模板"""

    data = request.json
    session_id = data.get("session_id", "")
    customizations = data.get("customizations", None)

    if not session_id:
        return jsonify({"error": "请提供 session_id"}), 400

    from core.template_manager import apply_template

    try:
        config = apply_template(name, session_id, customizations)
        return jsonify({
            "success": True,
            "config": config
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/templates", methods=["POST"])
def create_template():
    """创建自定义模板"""

    data = request.json

    from core.template_manager import create_template

    try:
        template = create_template(**data)
        return jsonify({
            "success": True,
            "template": template
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── 素材管理 ──

@app.route("/api/assets", methods=["POST"])
def upload_asset():
    """上传素材"""

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    user_tags = request.form.getlist("tags") if "tags" in request.form else None

    # 保存临时文件
    temp_path = UPLOAD_DIR / f"asset_{uuid.uuid4()}"
    file.save(temp_path)

    from core.asset_manager import upload_asset

    try:
        asset = upload_asset(str(temp_path), user_tags)
        return jsonify({
            "success": True,
            "asset": asset.to_dict()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/assets", methods=["GET"])
def search_assets():
    """搜索素材"""

    tags = request.args.getlist("tags")
    file_type = request.args.get("file_type", None)
    keyword = request.args.get("keyword", None)

    from core.asset_manager import search_assets

    assets = search_assets(tags, file_type, keyword)

    return jsonify({
        "success": True,
        "assets": [a.to_dict() for a in assets]
    })


@app.route("/api/assets/<asset_id>", methods=["GET"])
def get_asset(asset_id):
    """获取素材详情"""

    from core.asset_manager import get_asset_manager

    manager = get_asset_manager()

    try:
        asset = manager.get_asset(asset_id)
        return jsonify({
            "success": True,
            "asset": asset.to_dict()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 404


@app.route("/api/assets/<asset_id>", methods=["DELETE"])
def delete_asset(asset_id):
    """删除素材"""

    from core.asset_manager import get_asset_manager

    manager = get_asset_manager()

    try:
        success = manager.delete_asset(asset_id)
        return jsonify({
            "success": success
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/assets/stats", methods=["GET"])
def get_asset_stats():
    """获取素材库统计"""

    from core.asset_manager import get_asset_manager

    manager = get_asset_manager()

    stats = manager.get_stats()

    return jsonify({
        "success": True,
        "stats": stats
    })


# ── 用户素材上传与分析 ──

@app.route("/api/user-assets/upload", methods=["POST"])
def upload_user_asset():
    """上传用户自定义素材（图片/视频）"""

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    # 判断文件类型
    ext = os.path.splitext(file.filename)[1].lower()
    if ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
        asset_type = "image"
    elif ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
        asset_type = "video"
    else:
        return jsonify({"error": f"Unsupported file type: {ext}"}), 400

    # 保存文件
    asset_id = str(uuid.uuid4())
    asset_path = UPLOAD_DIR / f"user_asset_{asset_id}{ext}"
    file.save(asset_path)

    # 获取时长（视频）
    duration = 0.0
    if asset_type == "video":
        import subprocess
        cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(asset_path)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                duration = float(result.stdout.strip())
        except Exception:
            pass

    return jsonify({
        "success": True,
        "asset_id": asset_id,
        "asset_type": asset_type,
        "asset_path": str(asset_path),
        "filename": file.filename,
        "duration": duration,
    })


@app.route("/api/user-assets/analyze", methods=["POST"])
def analyze_user_asset():
    """AI 分析用户素材，生成脚本建议"""

    data = request.json
    asset_path = data.get("asset_path", "")
    theme = data.get("theme", "")

    if not asset_path or not os.path.exists(asset_path):
        return jsonify({"error": "素材文件不存在"}), 400

    from core.user_asset_analyzer import analyze_image, analyze_video, AssetAnalysis
    from dataclasses import asdict

    # 判断素材类型
    ext = os.path.splitext(asset_path)[1].lower()
    try:
        if ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
            analysis = analyze_image(asset_path)
        elif ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
            analysis = analyze_video(asset_path)
        else:
            return jsonify({"error": f"Unsupported file type: {ext}"}), 400

        return jsonify({
            "success": True,
            "analysis": asdict(analysis),
        })

    except Exception as e:
        logger.error(f"素材分析失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/user-assets/generate-script", methods=["POST"])
def generate_script_from_user_assets():
    """根据多个用户素材生成完整脚本"""

    data = request.json
    asset_paths = data.get("asset_paths", [])
    theme = data.get("theme", "")

    if not asset_paths:
        return jsonify({"error": "请提供素材列表"}), 400

    if not theme:
        return jsonify({"error": "请提供视频主题"}), 400

    from core.user_asset_analyzer import analyze_image, analyze_video, generate_script_from_assets

    try:
        # 分析所有素材
        analyses = []
        for path in asset_paths:
            if not os.path.exists(path):
                continue

            ext = os.path.splitext(path)[1].lower()
            if ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
                analysis = analyze_image(path)
            elif ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
                analysis = analyze_video(path)
            else:
                continue

            analyses.append(analysis)

        if not analyses:
            return jsonify({"error": "无有效素材"}), 400

        # 生成脚本
        script = generate_script_from_assets(analyses, theme)

        return jsonify({
            "success": True,
            "script": script,
            "analyses_count": len(analyses),
        })

    except Exception as e:
        logger.error(f"脚本生成失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/user-assets/list", methods=["GET"])
def list_user_assets():
    """列出已上传的用户素材"""

    # 简单实现：列出 UPLOAD_DIR 中的用户素材
    assets = []

    for f in UPLOAD_DIR.glob("user_asset_*"):
        ext = f.suffix.lower()
        if ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
            asset_type = "image"
        elif ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
            asset_type = "video"
        else:
            continue

        assets.append({
            "name": f.name,
            "path": str(f),
            "type": asset_type,
            "size": f.stat().st_size,
        })

    return jsonify({
        "success": True,
        "assets": assets,
    })


# ── 多语言叙事 ──

@app.route("/api/narrative/multilingual", methods=["POST"])
def generate_multilingual():
    """生成多语言叙事"""

    data = request.json
    theme = data.get("theme", "")
    analysis = data.get("analysis", {})
    style = data.get("style", None)
    languages = data.get("languages", ["zh", "en"])

    if not theme:
        return jsonify({"error": "请输入视频主题"}), 400

    from core.multilingual_narrative import generate_multilingual_narrative

    try:
        narrative = generate_multilingual_narrative(theme, analysis, style, languages)
        return jsonify({
            "success": True,
            "narrative": narrative.to_dict()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/subtitle/translate", methods=["POST"])
def translate_subtitles():
    """翻译字幕"""

    data = request.json
    subtitles = data.get("subtitles", [])
    from_lang = data.get("from_lang", "zh")
    to_lang = data.get("to_lang", "en")

    from core.multilingual_narrative import translate_subtitle

    try:
        translated = translate_subtitle(subtitles, from_lang, to_lang)
        return jsonify({
            "success": True,
            "subtitles": translated
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Session 管理 ──

@app.route("/api/sessions/<session_id>", methods=["GET"])
def get_session(session_id):
    """获取 Session 状态"""

    from agent.session_store import get_session_store

    store = get_session_store()

    try:
        state = store.get_session(session_id)
        return jsonify({
            "success": True,
            "session": state.dict()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 404


@app.route("/api/sessions/<session_id>/redo/<target_step>", methods=["POST"])
def redo_from_step(session_id, target_step):
    """从指定步骤重新执行"""

    data = request.json
    voice = data.get("voice", "longxiaochun")
    tts_speed = data.get("tts_speed", 1.0)
    visual_mode = data.get("visual_mode", "auto")
    style_profile = data.get("style_profile", None)

    target_step = int(target_step)

    from tasks import redo_from_step_task

    task = redo_from_step_task.delay(
        session_id=session_id,
        target_step=target_step,
        voice=voice,
        tts_speed=tts_speed,
        visual_mode=visual_mode,
        style_profile=style_profile
    )

    return jsonify({
        "success": True,
        "task_id": task.id,
        "ws_url": f"/ws/progress/{session_id}"
    })


# ── 入口 ──

if __name__ == "__main__":
    logger.info("Starting Emotion Video Producer Web API...")
    logger.info("Open http://localhost:5001 in your browser")
    app.run(host="0.0.0.0", port=5001, debug=True)