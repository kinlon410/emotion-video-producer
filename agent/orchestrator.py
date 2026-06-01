#!/usr/bin/env python3
"""
Agent Orchestrator — 多步骤流程编排

支持：
1. run_pipeline — 完整流程执行
2. redo_from_step — 从指定步骤重新执行
3. interrupt_and_continue — 中断后继续
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

from agent.schemas import SessionState
from agent.session_store import get_session_store, SessionStore
from agent.steps import (
    step1_analyze, step2_narrative, step3_visual_select, step4_transition,
    step5_subtitle, step6_tts, step7_asr, step8_visual_download, step9_render,
    STEP_NAMES, TOTAL_STEPS
)
from core.logging_config import get_logger
from core.exceptions import RenderError, SessionNotFoundError
from config import DEFAULT_OUTPUT_DIR, DEFAULT_VOICE, DEFAULT_TTS_SPEED

logger = get_logger("orchestrator")


class AgentOrchestrator:
    """Agent 流程编排器"""

    def __init__(self, session_store: SessionStore = None):
        """初始化 Orchestrator

        Args:
            session_store: Session Store 实例
        """
        self.store = session_store or get_session_store()
        self.step_handlers = {
            1: step1_analyze,
            2: step2_narrative,
            3: step3_visual_select,
            4: step4_transition,
            5: step5_subtitle,
            6: step6_tts,
            7: step7_asr,
            8: step8_visual_download,
            9: step9_render,
        }

    def create_session(
        self,
        theme: str,
        bgm_path: str,
        style: str = None,
        output_path: str = None
    ) -> str:
        """创建新 Session

        Args:
            theme: 视频主题
            bgm_path: BGM 路径
            style: 风格预设
            output_path: 输出路径（可选）

        Returns:
            Session ID
        """
        session_id = self.store.create_session(theme, bgm_path, style)

        # 生成默认输出路径
        if not output_path:
            output_path = f"{DEFAULT_OUTPUT_DIR}/{theme.replace(' ', '_')}.mp4"

        # 保存输出路径
        self.store.update_session(session_id, {"output_path": output_path})

        return session_id

    def run_pipeline(
        self,
        session_id: str,
        start_step: int = 1,
        end_step: int = TOTAL_STEPS,
        voice: str = DEFAULT_VOICE,
        tts_speed: float = DEFAULT_TTS_SPEED,
        visual_mode: str = "auto",
        style_profile: Dict[str, Any] = None,
        progress_callback: Callable[[int, str, Dict], None] = None
    ) -> Dict[str, Any]:
        """执行流程（可从指定步骤开始）

        Args:
            session_id: Session ID
            start_step: 起始步骤编号
            end_step: 结束步骤编号
            voice: TTS 语音
            tts_speed: TTS 语速
            visual_mode: 素材获取模式
            style_profile: 风格分析结果（可选）
            progress_callback: 进度回调函数

        Returns:
            最终结果字典
        """
        state = self.store.get_session(session_id)
        work_dir = self.store.get_work_dir(session_id)

        # 加载已完成的 Checkpoint 结果
        for step in state.completed_steps:
            if step < start_step:
                checkpoint = self.store.get_checkpoint(session_id, step)
                if checkpoint:
                    self._inject_checkpoint_result(state, step, checkpoint.result)

        # 执行步骤
        for step in range(start_step, end_step + 1):
            step_name = STEP_NAMES.get(step, f"step{step}")
            logger.info(f"执行步骤 {step}: {step_name}")

            try:
                result = self._execute_step(
                    step, state, work_dir, voice, tts_speed, visual_mode, style_profile
                )

                # 保存 Checkpoint
                self.store.save_checkpoint(session_id, step, step_name, result)

                # 注入结果到 Session
                self._inject_result(state, step, result)

                # 更新 Session
                self.store.update_session(session_id, {
                    "current_step": step,
                    **self._get_state_updates(step, result)
                })

                # 进度回调
                if progress_callback:
                    progress_callback(step, step_name, result)

            except Exception as e:
                logger.error(f"步骤 {step} 失败: {e}")
                raise

        return {
            "session_id": session_id,
            "output_path": state.output_path,
            "theme": state.theme,
            "style": state.style,
        }

    async def run_pipeline_async(
        self,
        session_id: str,
        start_step: int = 1,
        end_step: int = TOTAL_STEPS,
        voice: str = DEFAULT_VOICE,
        tts_speed: float = DEFAULT_TTS_SPEED,
        visual_mode: str = "auto",
        style_profile: Dict[str, Any] = None,
        progress_callback: Callable[[int, str, Dict], None] = None
    ) -> Dict[str, Any]:
        """异步执行流程（async 步骤）

        Args:
            同 run_pipeline

        Returns:
            最终结果字典
        """
        state = self.store.get_session(session_id)
        work_dir = self.store.get_work_dir(session_id)

        # 加载已完成的 Checkpoint 结果
        for step in state.completed_steps:
            if step < start_step:
                checkpoint = self.store.get_checkpoint(session_id, step)
                if checkpoint:
                    self._inject_checkpoint_result(state, step, checkpoint.result)

        # 执行步骤
        for step in range(start_step, end_step + 1):
            step_name = STEP_NAMES.get(step, f"step{step}")
            logger.info(f"执行步骤 {step}: {step_name}")

            try:
                if step == 8:
                    # async 步骤
                    result = await self._execute_step_async(
                        step, state, work_dir, visual_mode
                    )
                else:
                    result = self._execute_step(
                        step, state, work_dir, voice, tts_speed, visual_mode, style_profile
                    )

                # 保存 Checkpoint
                self.store.save_checkpoint(session_id, step, step_name, result)

                # 注入结果
                self._inject_result(state, step, result)

                # 更新 Session
                self.store.update_session(session_id, {
                    "current_step": step,
                    **self._get_state_updates(step, result)
                })

                # 进度回调
                if progress_callback:
                    progress_callback(step, step_name, result)

            except Exception as e:
                logger.error(f"步骤 {step} 失败: {e}")
                raise

        return {
            "session_id": session_id,
            "output_path": state.output_path,
            "theme": state.theme,
            "style": state.style,
        }

    def redo_from_step(
        self,
        session_id: str,
        target_step: int,
        voice: str = DEFAULT_VOICE,
        tts_speed: float = DEFAULT_TTS_SPEED,
        visual_mode: str = "auto",
        style_profile: Dict[str, Any] = None,
        progress_callback: Callable[[int, str, Dict], None] = None
    ) -> Dict[str, Any]:
        """从指定步骤重新执行

        Args:
            session_id: Session ID
            target_step: 目标步骤（从该步骤开始重新执行）
            其他参数同 run_pipeline

        Returns:
            最终结果字典
        """
        state = self.store.get_session(session_id)

        # 验证 target_step 在已完成范围内
        if target_step > state.current_step + 1:
            logger.warning(f"target_step={target_step} 超过当前进度，从头开始")
            target_step = 1

        logger.info(f"从步骤 {target_step} 重新执行")

        return self.run_pipeline(
            session_id,
            start_step=target_step,
            voice=voice,
            tts_speed=tts_speed,
            visual_mode=visual_mode,
            style_profile=style_profile,
            progress_callback=progress_callback
        )

    async def redo_from_step_async(
        self,
        session_id: str,
        target_step: int,
        voice: str = DEFAULT_VOICE,
        tts_speed: float = DEFAULT_TTS_SPEED,
        visual_mode: str = "auto",
        style_profile: Dict[str, Any] = None,
        progress_callback: Callable[[int, str, Dict], None] = None
    ) -> Dict[str, Any]:
        """异步从指定步骤重新执行

        Args:
            同 redo_from_step

        Returns:
            最终结果字典
        """
        return await self.run_pipeline_async(
            session_id,
            start_step=target_step,
            voice=voice,
            tts_speed=tts_speed,
            visual_mode=visual_mode,
            style_profile=style_profile,
            progress_callback=progress_callback
        )

    def _execute_step(
        self,
        step: int,
        state: SessionState,
        work_dir: Path,
        voice: str,
        tts_speed: float,
        visual_mode: str,
        style_profile: Dict[str, Any] = None
    ) -> Any:
        """执行单个步骤"""

        output_json = str(work_dir / f"{STEP_NAMES.get(step, f'step{step}')}.json")

        if step == 1:
            return step1_analyze(state.bgm_path, output_json)

        elif step == 2:
            return step2_narrative(
                state.theme, state.analysis, state.style,
                output_json, style_profile
            )

        elif step == 3:
            return step3_visual_select(state.analysis, 7, output_json)

        elif step == 4:
            return step4_transition(state.analysis, state.visuals, output_json)

        elif step == 5:
            narration_duration = None
            if state.narration_audio:
                from core.tts import get_audio_duration
                narration_duration = get_audio_duration(state.narration_audio)
            return step5_subtitle(
                state.analysis, state.narrative, output_json,
                narration_duration, state.asr_result
            )

        elif step == 6:
            narration_script = state.narrative.get("narration_script", "")
            narration_path = str(work_dir / "narration.wav")
            return step6_tts(narration_script, narration_path, voice, tts_speed)

        elif step == 7:
            if state.narration_audio:
                return step7_asr(state.narration_audio, "zh", output_json)
            return None

        elif step == 9:
            title_text = state.narrative.get("title_text", state.theme)
            return step9_render(
                title_text, state.bgm_path, state.narration_audio,
                state.clips, state.transitions, state.subtitles,
                state.output_path
            )

        raise RenderError(f"未知步骤: {step}")

    async def _execute_step_async(
        self,
        step: int,
        state: SessionState,
        work_dir: Path,
        visual_mode: str
    ) -> Any:
        """执行异步步骤"""

        if step == 8:
            clips_dir = str(work_dir / "clips")
            visual_queries = []
            for v in state.visuals:
                visual_queries.append({
                    "id": v["id"],
                    "keyword": v["keyword"],
                    "duration": v["duration"],
                })
            return await step8_visual_download(visual_queries, clips_dir, visual_mode)

        raise RenderError(f"步骤 {step} 不是异步步骤")

    def _inject_checkpoint_result(
        self,
        state: SessionState,
        step: int,
        result: Dict[str, Any]
    ):
        """从 Checkpoint 注入结果到 state"""
        if step == 1:
            state.analysis = result
        elif step == 2:
            state.narrative = result
        elif step == 3:
            state.visuals = result
        elif step == 4:
            state.transitions = result
        elif step == 5:
            state.subtitles = result
        elif step == 6:
            state.narration_audio = result
        elif step == 7:
            state.asr_result = result
        elif step == 8:
            state.clips = result

    def _inject_result(self, state: SessionState, step: int, result: Any):
        """注入结果到 state"""
        self._inject_checkpoint_result(state, step, result)

    def _get_state_updates(self, step: int, result: Any) -> Dict[str, Any]:
        """获取 Session 更新字段"""
        updates = {}
        if step == 1:
            updates["analysis"] = result
        elif step == 2:
            updates["narrative"] = result
        elif step == 3:
            updates["visuals"] = result
        elif step == 4:
            updates["transitions"] = result
        elif step == 5:
            updates["subtitles"] = result
        elif step == 6:
            updates["narration_audio"] = result
        elif step == 7:
            updates["asr_result"] = result
        elif step == 8:
            updates["clips"] = result
        return updates


# 全局 Orchestrator 实例
_orchestrator = None


def get_orchestrator() -> AgentOrchestrator:
    """获取 Orchestrator 实例"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator