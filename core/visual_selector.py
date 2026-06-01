#!/usr/bin/env python3
"""
视觉选择器模块 — 根据情感能量选择视频素材类型

支持两种模式：
1. 动态模式：根据每段能量选择不同素材类型（默认）
2. 统一风格模式：所有片段使用同一风格素材（适合抖音等平台）

情感 → 素材类型映射：
- high_energy → 运动、人群、光效、动态、都市夜景
- medium_energy → 城市、建筑、交通、街道行走
- low_energy → 风景、空镜、自然、日出日落、水面

用法:
    python3 -m core.visual_selector --analysis analysis.json --output visuals.json
    python3 -m core.visual_selector --analysis analysis.json --unified-style city --output visuals.json
"""

import argparse
import json
import random
from typing import Dict, List, Optional

from config import DEFAULT_WIDTH, DEFAULT_HEIGHT, DEFAULT_FPS


# ── 情感能量 → 素材类型映射 ──
# 注意：避免清晰个人面部肖像，但允许人群远景/模糊人群
# 每个能量级别有多个关键词变体，增加素材多样性

ENERGY_TO_VISUAL = {
    "high": {
        "keywords": [
            # 城市夜景
            "neon lights night city",
            "urban night dynamic skyline",
            "light trails night traffic highway",
            "city skyline night lights aerial",
            "building lights night downtown",
            # 光效/动感
            "fireworks sky explosion colorful",
            "lightning storm sky dramatic",
            "aurora borealis sky northern lights",
            # 交通动感
            "fast motion traffic night",
            "cars highway night lights",
            "train tunnel motion lights",
            # 人群远景（模糊/远景，无清晰面部）
            "crowd distant aerial view",
            "busy street aerial view night",
            "festival crowd aerial lights",
            # 自然高能量
            "waterfall powerful flow",
            "ocean waves crashing sunset",
            "storm clouds dramatic sky",
        ],
        "desc_zh_candidates": [
            "霓虹闪烁、城市夜景",
            "烟花绽放、光影璀璨",
            "光轨流动、都市夜色",
            "人群远景、动感氛围",
            "瀑布奔腾、气势磅礴",
        ],
    },
    "medium": {
        "keywords": [
            # 建筑城市
            "architecture building modern glass",
            "skyscraper tower city skyline",
            "urban downtown aerial view",
            "bridge cityscape river skyline",
            "metro subway station modern",
            # 交通流动
            "traffic urban motion highway aerial",
            "train metro moving tunnel lights",
            "cars highway motion daytime",
            "airport terminal modern",
            # 人群远景（允许远景人群）
            "busy street aerial view daytime",
            "people walking distant view street",
            "crowd blur motion urban",
            "market street aerial view",
            # 城市细节
            "city lights evening skyline sunset",
            "urban street night lights",
            "office building glass reflection",
        ],
        "desc_zh_candidates": [
            "现代建筑、城市轮廓",
            "车流穿梭、都市节奏",
            "人群远景、街头氛围",
            "桥梁天际、城市风貌",
            "地铁穿行、隧道光影",
        ],
    },
    "low": {
        "keywords": [
            # 天空/云层
            "sky clouds sunset golden hour",
            "sunrise dawn peaceful orange sky",
            "moon night stars sky clear",
            "sunset clouds dramatic orange",
            "blue sky clouds peaceful",
            # 自然风景
            "nature forest peaceful green",
            "mountain landscape scenic view",
            "water lake reflection calm",
            "ocean waves beach sunset peaceful",
            "river flowing gentle forest",
            # 花卉/细节
            "flower blooming garden colorful",
            "rain window gentle drops",
            "autumn leaves falling peaceful",
            "snow winter forest quiet",
            # 空旷场景
            "empty street quiet night",
            "desert landscape empty scenic",
            "meadow grass peaceful sunset",
        ],
        "desc_zh_candidates": [
            "天空云层、日落时分",
            "自然森林、宁静悠远",
            "湖面倒影、平静如镜",
            "月亮星空、夜色温柔",
            "日出晨曦、宁静开始",
        ],
    },
}


# ── 统一风格预设 ──
# 抖音等平台推荐使用统一风格，视频更协调
# 注意：避免清晰个人面部肖像，但允许人群远景/模糊人群
# 每个风格有多个关键词变体，增加素材多样性

UNIFIED_STYLES = {
    "city": {
        "name": "城市风格",
        "keywords": [
            # 建筑天际
            "architecture building modern glass",
            "skyscraper tower city skyline",
            "urban downtown aerial view",
            "bridge cityscape river skyline",
            # 交通夜景
            "traffic urban motion highway aerial",
            "city lights evening skyline sunset",
            "urban street night lights",
            "light trails night traffic highway",
            # 人群远景（模糊/远景）
            "busy street aerial view daytime",
            "people walking distant view street",
            "crowd blur motion urban",
            "market street aerial view",
            # 城市细节
            "metro subway station modern",
            "office building glass reflection",
        ],
        "desc": "现代都市、建筑街景",
        "energy_match": "medium",
    },
    "nature": {
        "name": "自然风格",
        "keywords": [
            # 森林山川
            "nature forest peaceful green",
            "mountain landscape scenic view",
            "autumn forest colorful leaves",
            "snow winter forest quiet",
            # 水域风景
            "water lake reflection calm",
            "ocean waves beach sunset peaceful",
            "river flowing gentle forest",
            "waterfall scenic nature",
            # 天空云层
            "sky clouds sunset golden hour",
            "sunrise dawn peaceful orange sky",
            "sunset clouds dramatic orange",
            # 花卉草地
            "flower blooming garden colorful",
            "meadow grass peaceful sunset",
            "rain window gentle drops",
        ],
        "desc": "自然风光、宁静治愈",
        "energy_match": "low",
    },
    "night": {
        "name": "夜景风格",
        "keywords": [
            # 霓虹都市
            "neon lights night city",
            "urban night dynamic skyline",
            "city skyline night lights aerial",
            "building lights night downtown",
            # 光轨动感
            "light trails night traffic highway",
            "fast motion traffic night",
            "cars highway night lights",
            # 人群夜景（远景/模糊）
            "busy street aerial view night",
            "crowd distant aerial view lights",
            "festival crowd aerial lights",
            # 夜空烟花
            "fireworks sky explosion colorful",
            "moon night stars sky clear",
            "bridge night lights reflection",
        ],
        "desc": "霓虹夜景、都市繁华",
        "energy_match": "high",
    },
    "cinematic": {
        "name": "电影风格",
        "keywords": [
            # 电影风景
            "slow motion cinematic landscape",
            "cinematic shot landscape dramatic",
            "film grain aesthetic mood",
            "dramatic lighting building sunset",
            # 光影氛围
            "silhouette sunset sky dramatic",
            "fog mystery atmosphere forest",
            "golden hour lighting city warm",
            "moody atmospheric sky clouds",
            # 电影城市（允许远景人群）
            "cinematic aerial city view",
            "dramatic sky sunset landscape",
            "cinematic street aerial view",
            "film look urban landscape",
        ],
        "desc": "电影质感、氛围感",
        "energy_match": "medium",
    },
    "travel": {
        "name": "旅行风格",
        "keywords": [
            # 交通旅行
            "airplane window clouds sky view",
            "train travel scenic view window",
            "road highway driving view scenic",
            "harbor port ships scenic",
            # 目的地风景
            "beach ocean scenic sunset",
            "mountain scenic landscape travel",
            "city aerial skyline travel view",
            "island ocean aerial view",
            # 旅行元素
            "airport terminal modern",
            "lighthouse ocean scenic view",
            "bridge river scenic travel",
            "coastal road scenic view",
        ],
        "desc": "旅行探索、自由冒险",
        "energy_match": "medium",
    },
}


def select_visuals(analysis: Dict, segment_count: int = 7,
                   output_json: str = None,
                   unified_style: str = None,
                   max_segment_duration: float = 3.0) -> List[Dict]:
    """根据情感分析选择视觉素材

    Args:
        analysis: 音乐情感分析结果
        segment_count: 目标片段数量（如果为None，根据max_segment_duration自动计算）
        output_json: 输出 JSON 文件路径（可选）
        unified_style: 统一风格名称 (city/nature/night/cinematic/travel)
                       None 表示动态模式（根据能量变化素材类型）
        max_segment_duration: 每个片段最大时长（秒），用于自动计算片段数

    Returns:
        list: 视觉素材描述列表
    """
    print(f"[visual_selector] 选择视觉素材")

    duration = analysis.get("duration", 20)

    # 如果未指定片段数，根据最大片段时长自动计算
    if segment_count is None or segment_count <= 0:
        segment_count = max(int(duration / max_segment_duration), 5)
        print(f"  自动计算片段数: {segment_count} (时长{duration}s, 每片段≤{max_segment_duration}s)")

    # 确保每片段不超过最大时长
    avg_segment_duration = duration / segment_count
    if avg_segment_duration > max_segment_duration:
        # 重新计算更多片段
        segment_count = int(duration / max_segment_duration) + 1
        print(f"  调整片段数: {segment_count} (确保每片段≤{max_segment_duration}s)")

    print(f"  目标片段数: {segment_count}, 平均时长: {duration/segment_count:.1f}s")

    if unified_style:
        print(f"  统一风格模式: {unified_style}")
        return _select_unified_visuals(analysis, segment_count, unified_style, output_json)
    else:
        print(f"  动态风格模式")
        return _select_dynamic_visuals(analysis, segment_count, output_json)


def _select_unified_visuals(analysis: Dict, segment_count: int,
                            style_name: str, output_json: str = None) -> List[Dict]:
    """统一风格素材选择 - 所有片段使用同一类型素材"""

    style = UNIFIED_STYLES.get(style_name)
    if not style:
        print(f"[Warning] 未知的风格 '{style_name}'，使用 city", file=sys.stderr)
        style = UNIFIED_STYLES["city"]

    structure = analysis.get("structure", [])
    duration = analysis.get("duration", 20)

    # 生成片段时间划分
    if len(structure) < segment_count:
        segment_duration = duration / segment_count
        segments = []
        for i in range(segment_count):
            segments.append({
                "id": f"S{i + 1}",
                "start": round(i * segment_duration, 2),
                "end": round((i + 1) * segment_duration, 2),
            })
    else:
        segments = []
        for i, seg in enumerate(structure[:segment_count]):
            segments.append({
                "id": f"S{i + 1}",
                "start": seg["start"],
                "end": seg["end"],
            })

    # 使用统一风格的关键词（不重复）
    keywords = style["keywords"].copy()
    random.shuffle(keywords)  # 随机顺序

    # 生成视觉素材
    visuals = []
    for i, seg in enumerate(segments):
        # 循环使用关键词（如果片段数多于关键词数）
        keyword = keywords[i % len(keywords)]

        visuals.append({
            "id": seg["id"],
            "start": seg["start"],
            "end": seg["end"],
            "duration": round(seg["end"] - seg["start"], 2),
            "energy": style["energy_match"],
            "keyword": keyword,
            "desc_zh": style["desc"],
            "width": DEFAULT_WIDTH,
            "height": DEFAULT_HEIGHT,
            "fps": DEFAULT_FPS,
        })

    print(f"  生成 {len(visuals)} 个视觉片段（风格: {style['name']}）")

    if output_json:
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(visuals, f, ensure_ascii=False, indent=2)
        print(f"  输出已保存: {output_json}")

    return visuals


def _select_dynamic_visuals(analysis: Dict, segment_count: int,
                            output_json: str = None) -> List[Dict]:
    """动态风格素材选择 - 根据能量变化素材类型"""

    structure = analysis.get("structure", [])
    duration = analysis.get("duration", 20)

    # 如果结构段数不够，均匀划分
    if len(structure) < segment_count:
        segment_duration = duration / segment_count
        segments = []
        for i in range(segment_count):
            # 根据位置分配能量
            if i < segment_count * 0.2:  # 开场
                energy = "low"
            elif i > segment_count * 0.8:  # 收尾
                energy = "low"
            elif i > segment_count * 0.4 and i < segment_count * 0.7:  # 中间高潮区
                energy = "high"
            else:
                energy = "medium"

            segments.append({
                "id": f"S{i + 1}",
                "start": round(i * segment_duration, 2),
                "end": round((i + 1) * segment_duration, 2),
                "energy": energy,
            })
    else:
        # 使用分析结果的能量
        segments = []
        for i, seg in enumerate(structure[:segment_count]):
            segments.append({
                "id": f"S{i + 1}",
                "start": seg["start"],
                "end": seg["end"],
                "energy": seg["energy"],
            })

    # 记录每个能量级别已使用的关键词，避免重复
    used_keywords = {"high": set(), "medium": set(), "low": set()}

    # 为每个片段选择视觉类型
    visuals = []
    for seg in segments:
        energy = seg["energy"]
        visual_type = ENERGY_TO_VISUAL.get(energy, ENERGY_TO_VISUAL["medium"])

        # 获取可用关键词（排除已使用的）
        available_keywords = [k for k in visual_type["keywords"] if k not in used_keywords[energy]]

        # 如果所有关键词都用完了，重置并重新选择
        if not available_keywords:
            used_keywords[energy] = set()
            available_keywords = visual_type["keywords"]

        # 随机选择关键词
        keyword = random.choice(available_keywords)
        used_keywords[energy].add(keyword)

        # 随机选择中文描述
        desc_zh = random.choice(visual_type["desc_zh_candidates"])

        visuals.append({
            "id": seg["id"],
            "start": seg["start"],
            "end": seg["end"],
            "duration": round(seg["end"] - seg["start"], 2),
            "energy": energy,
            "keyword": keyword,
            "desc_zh": desc_zh,
            "width": DEFAULT_WIDTH,
            "height": DEFAULT_HEIGHT,
            "fps": DEFAULT_FPS,
        })

    print(f"  生成 {len(visuals)} 个视觉片段")

    # 保存 JSON
    if output_json:
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(visuals, f, ensure_ascii=False, indent=2)
        print(f"  输出已保存: {output_json}")

    return visuals


def get_available_styles() -> List[Dict]:
    """获取可用的统一风格列表"""
    return [
        {"name": name, "display": style["name"], "desc": style["desc"]}
        for name, style in UNIFIED_STYLES.items()
    ]


def main():
    parser = argparse.ArgumentParser(description="视觉选择器模块")
    parser.add_argument("--analysis", required=True, help="音乐情感分析 JSON")
    parser.add_argument("--segments", type=int, default=7, help="片段数量")
    parser.add_argument("--unified-style", choices=list(UNIFIED_STYLES.keys()),
                        help="统一风格模式 (city/nature/night/cinematic/travel)")
    parser.add_argument("--output", default=None, help="输出 JSON 文件路径")
    parser.add_argument("--list-styles", action="store_true", help="列出可用风格")
    args = parser.parse_args()

    if args.list_styles:
        print("可用统一风格:")
        for name, style in UNIFIED_STYLES.items():
            print(f"  {name}: {style['name']} - {style['desc']}")
        return

    with open(args.analysis, "r", encoding="utf-8") as f:
        analysis = json.load(f)

    visuals = select_visuals(analysis, args.segments, args.unified_style, args.output)

    if args.output is None:
        print(json.dumps(visuals, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()