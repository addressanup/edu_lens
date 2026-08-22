"""
Live Tutor Session for EduLens

Manages a single live camera-tutoring session over WebSocket:
- Receives base64 JPEG frames streamed from the student's device (Android phone
  acting as the EduLens camera).
- Runs a continuous observation loop: periodically sends the latest frame to
  the DeepSeek vision model to assess the scene and detect struggle.
- When struggle is detected, proactively pushes an intervention event with a
  short, Socratic, age-appropriate message.
- Handles on-demand questions from the child ("help me with this problem")
  by attaching the latest frame to the query.

Privacy notes (COPPA-aligned):
- Frames are held in memory only, for the lifetime of the session.
- Only the latest frame (plus optional small history) is ever sent to the LLM.
- Nothing is persisted to disk.

Author: EduLens AI Team
Version: 1.0.0
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

from src.ai.llm_service import LLMMessage, LLMService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

OBSERVER_SYSTEM_PROMPT = """You are the observation module of EduLens, an AI tutor \
for children aged 6-12. You receive one camera frame from the child's learning \
device showing their homework or learning material.

Analyze the frame and assess how the child is doing. Respond with ONLY a JSON \
object, no markdown fences, no extra text, using exactly this schema:

{
  "scene": "one short sentence describing what is visible",
  "subject": "math" | "reading" | "science" | "social_studies" | "other",
  "child_present": true | false,
  "engagement": "active" | "stuck" | "distracted" | "absent",
  "struggle_detected": true | false,
  "confidence": <float 0.0-1.0>,
  "intervention_message": "<string or null>"
}

Rules for intervention_message:
- Provide it ONLY when struggle_detected is true AND confidence >= 0.6.
- It must be a warm, encouraging hint that guides the child toward the next \
step - NEVER the final answer (Socratic method).
- Maximum 2 short sentences, simple vocabulary for the child's age.
- If the frame is unclear, or no struggle is visible, use null."""

TUTOR_SYSTEM_PROMPT = """You are EduLens, a warm and encouraging AI tutor for \
children aged 6-12. The child is doing homework in front of a camera; you can \
see their work in the image provided with each question.

Guidelines:
- Use the Socratic method: guide with hints and questions, never give the \
final answer directly.
- Keep responses to 2-4 short sentences of simple, age-appropriate language.
- Be patient, positive, and celebrate effort.
- If the image is unclear, ask the child to hold the page steadier or move \
closer.
- Never discuss topics unsuitable for children; gently redirect to learning."""


def _parse_json_loose(text: str) -> Optional[Dict[str, Any]]:
    """Defensively parse a JSON object out of a model response."""
    if not text:
        return None
    cleaned = text.strip()
    # Strip markdown fences if present
    if cleaned.startswith("```"):
        first_newline = cleaned.find("\n")
        if first_newline != -1:
            cleaned = cleaned[first_newline + 1:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
    try:
        obj = json.loads(cleaned)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        # Last resort: grab the outermost {...} block
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end > start:
            try:
                obj = json.loads(cleaned[start:end + 1])
                return obj if isinstance(obj, dict) else None
            except json.JSONDecodeError:
                return None
    return None


# ---------------------------------------------------------------------------
# Session configuration
# ---------------------------------------------------------------------------

@dataclass
class LiveTutorConfig:
    """Tunables for a live tutoring session."""
    observation_interval_s: float = field(
        default_factory=lambda: float(os.getenv("EDULENS_OBSERVATION_INTERVAL", "12"))
    )
    intervention_cooldown_s: float = field(
        default_factory=lambda: float(os.getenv("EDULENS_INTERVENTION_COOLDOWN", "45"))
    )
    min_struggle_confidence: float = 0.6
    max_history_messages: int = 8
    max_frame_bytes: int = 3 * 1024 * 1024  # reject absurd frames early
    child_name: str = "friend"
    child_age: int = 8
    image_detail: str = "low"  # "low" downscales to 512px -> cheaper/faster


@dataclass
class LiveFrame:
    """A single received camera frame."""
    data_b64: str
    received_at: float
    width: Optional[int] = None
    height: Optional[int] = None

    def hash(self) -> str:
        return hashlib.sha256(self.data_b64.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Live tutor session
# ---------------------------------------------------------------------------

class LiveTutorSession:
    """
    State machine + AI logic for one live tutoring connection.

    The WebSocket layer feeds frames/queries in via `ingest_frame()` /
    `handle_query()` and forwards outgoing events via the `emit` callback.
    """

    def __init__(
        self,
        session_id: str,
        llm_service: LLMService,
        emit: Callable[[Dict[str, Any]], Awaitable[None]],
        config: Optional[LiveTutorConfig] = None,
    ) -> None:
        self.session_id = session_id
        self.llm = llm_service
        self.emit = emit
        self.config = config or LiveTutorConfig()

        # Latest frame state
        self._latest_frame: Optional[LiveFrame] = None
        self._last_analyzed_frame_hash: Optional[str] = None

        # Conversation memory (text-only summaries kept small)
        self._history: List[LLMMessage] = []

        # Observation loop
        self._observation_task: Optional[asyncio.Task] = None
        self._last_intervention_at: float = 0.0

        # Stats
        self.frames_received = 0
        self.observations_run = 0
        self.interventions_sent = 0
        self.queries_answered = 0
        self.started_at = time.time()
        self.active = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the continuous observation loop."""
        if self._observation_task and not self._observation_task.done():
            return
        self.active = True
        self._observation_task = asyncio.create_task(self._observation_loop())
        logger.info(
            "Live tutor session %s started (interval=%.1fs)",
            self.session_id, self.config.observation_interval_s,
        )

    async def stop(self) -> None:
        """Stop the observation loop and release frame data immediately."""
        self.active = False
        if self._observation_task:
            self._observation_task.cancel()
            try:
                await self._observation_task
            except asyncio.CancelledError:
                pass
            self._observation_task = None
        # Privacy: drop frames as soon as the session ends
        self._latest_frame = None
        self._history.clear()
        logger.info("Live tutor session %s stopped", self.session_id)

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    async def ingest_frame(self, data_b64: str, width: Optional[int] = None,
                           height: Optional[int] = None) -> Dict[str, Any]:
        """
        Store an incoming base64 JPEG frame. Returns a small ack payload.

        Frames are kept in memory only and replaced by newer ones.
        """
        if len(data_b64) > self.config.max_frame_bytes:
            raise ValueError(f"Frame too large: {len(data_b64)} bytes")

        self._latest_frame = LiveFrame(
            data_b64=data_b64,
            received_at=time.time(),
            width=width,
            height=height,
        )
        self.frames_received += 1
        return {
            "frames_received": self.frames_received,
            "buffered": True,
        }

    async def handle_query(self, text: str) -> Dict[str, Any]:
        """
        Handle an on-demand question from the child, attaching the latest
        camera frame so the tutor can see what the child sees.
        """
        text = (text or "").strip()
        if not text:
            await self.emit({
                "type": "error",
                "payload": {"message": "Empty question."},
            })
            return {"answered": False}

        prompt = (
            f"The child ({self.config.child_name}, age {self.config.child_age}) "
            f"asks: \"{text}\"\n\n"
            "Look at the attached image of their homework and answer following "
            "your tutoring guidelines."
        )

        try:
            response = await self._vision_call(prompt, speak_friendly=True)
        except Exception as exc:  # noqa: BLE001 - surfaced to client
            logger.error("Query failed in session %s: %s", self.session_id, exc)
            await self.emit({
                "type": "error",
                "payload": {"message": "I had trouble seeing that. Please try again."},
            })
            return {"answered": False}

        answer = response.content.strip()
        self.queries_answered += 1
        self._append_history(LLMMessage(role="user", content=text),
                             LLMMessage(role="assistant", content=answer))

        await self.emit({
            "type": "tutor_response",
            "payload": {
                "question": text,
                "text": answer,
                "model": response.model,
                "usage": response.usage,
            },
        })
        return {"answered": True}

    # ------------------------------------------------------------------
    # Observation loop
    # ------------------------------------------------------------------

    async def _observation_loop(self) -> None:
        """Periodically analyze the latest frame for struggle detection."""
        while self.active:
            try:
                await asyncio.sleep(self.config.observation_interval_s)
                if not self.active or self._latest_frame is None:
                    continue
                # Skip if we've already analyzed this exact frame
                frame_hash = self._latest_frame.hash()
                if frame_hash == self._last_analyzed_frame_hash:
                    continue
                await self._run_observation()
                self._last_analyzed_frame_hash = frame_hash
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - keep loop alive
                logger.error(
                    "Observation error in session %s: %s", self.session_id, exc
                )
                await asyncio.sleep(2.0)

    async def _run_observation(self) -> None:
        """One observation pass: vision call -> parse -> maybe intervene."""
        assert self._latest_frame is not None
        self.observations_run += 1

        response = await self._vision_call(
            OBSERVER_SYSTEM_PROMPT, speak_friendly=False,
            system="You are a precise classroom observer. Output strict JSON only.",
        )
        assessment = _parse_json_loose(response.content)

        if assessment is None:
            logger.warning(
                "Session %s: unparseable observation response: %.200s",
                self.session_id, response.content,
            )
            return

        struggling = bool(assessment.get("struggle_detected", False))
        confidence = float(assessment.get("confidence", 0.0))
        message = assessment.get("intervention_message")

        should_intervene = (
            struggling
            and confidence >= self.config.min_struggle_confidence
            and isinstance(message, str)
            and message.strip() != ""
            and (time.time() - self._last_intervention_at)
            >= self.config.intervention_cooldown_s
        )

        event: Dict[str, Any] = {
            "type": "observation",
            "payload": {
                "scene": assessment.get("scene"),
                "subject": assessment.get("subject"),
                "child_present": assessment.get("child_present"),
                "engagement": assessment.get("engagement"),
                "struggle_detected": struggling,
                "confidence": confidence,
                "intervention": message if should_intervene else None,
                "observations_run": self.observations_run,
            },
        }
        await self.emit(event)

        if should_intervene:
            self._last_intervention_at = time.time()
            self.interventions_sent += 1
            logger.info(
                "Session %s: intervention #%d sent (conf=%.2f)",
                self.session_id, self.interventions_sent, confidence,
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _vision_call(self, prompt: str, speak_friendly: bool,
                           system: Optional[str] = None):
        """Call the vision model with the latest frame + conversation history.

        Falls back to a text-only call when no frame is buffered (e.g. camera
        unavailable, covered lens, or simulator) so the tutor always answers.
        """
        if speak_friendly:
            persona = (
                f"The child's name is {self.config.child_name} and they are "
                f"{self.config.child_age} years old. Address them warmly by "
                "name occasionally."
            )
            prompt = f"{prompt}\n\n{persona}"

        max_tokens = 1000 if speak_friendly else 700

        if self._latest_frame is None:
            messages: List[LLMMessage] = []
            if system:
                messages.append(LLMMessage(role="system", content=system))
            messages.append(LLMMessage(role="user", content=prompt))
            return await self.llm.generate(
                messages,
                max_tokens=max_tokens,
                temperature=0.6,
            )

        return await self.llm.generate_with_image(
            prompt=prompt,
            image_base64=self._latest_frame.data_b64,
            image_mime="image/jpeg",
            history=list(self._history),
            system=system,
            detail=self.config.image_detail,
            # The vision model is a thinking model: reasoning tokens count
            # against max_tokens, so budget generously above the visible answer.
            max_tokens=max_tokens,
            temperature=0.6,
        )

    def _append_history(self, user_msg: LLMMessage, assistant_msg: LLMMessage) -> None:
        """Keep a bounded, text-only conversation memory."""
        self._history.append(user_msg)
        self._history.append(assistant_msg)
        excess = len(self._history) - self.config.max_history_messages
        if excess > 0:
            del self._history[:excess]

    def get_stats(self) -> Dict[str, Any]:
        """Session statistics for monitoring endpoints."""
        return {
            "session_id": self.session_id,
            "active": self.active,
            "uptime_s": round(time.time() - self.started_at, 1),
            "frames_received": self.frames_received,
            "observations_run": self.observations_run,
            "interventions_sent": self.interventions_sent,
            "queries_answered": self.queries_answered,
            "has_buffered_frame": self._latest_frame is not None,
            "config": {
                "observation_interval_s": self.config.observation_interval_s,
                "intervention_cooldown_s": self.config.intervention_cooldown_s,
                "image_detail": self.config.image_detail,
            },
        }
