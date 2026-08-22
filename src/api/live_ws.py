"""
Live Tutoring WebSocket Endpoint

JSON protocol for the EduLens student app (Android phone as camera):

Client -> Server (JSON text frames):
  {"type": "frame", "data": "<base64 JPEG>", "width": 640, "height": 480}
  {"type": "query", "text": "Help me with this problem"}
  {"type": "start_observation"}                     # begin continuous watching
  {"type": "stop_observation"}                      # pause continuous watching
  {"type": "config", "config": {"child_name": "...", "child_age": 8,
                                "observation_interval_s": 12}}
  {"type": "ping"}

Server -> Client (JSON text frames):
  {"type": "connected", "payload": {...}}
  {"type": "observation_started" | "observation_stopped", "payload": {...}}
  {"type": "observation", "payload": {scene, struggle_detected, intervention, ...}}
  {"type": "tutor_response", "payload": {question, text, model, usage}}
  {"type": "error", "payload": {"message": "..."}}
  {"type": "pong", "payload": {...}}

Author: EduLens AI Team
Version: 1.0.0
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.ai.llm_service import LLMService
from src.api.live_tutor import LiveTutorConfig, LiveTutorSession

logger = logging.getLogger(__name__)

router = APIRouter()

# Active live sessions keyed by session_id
live_sessions: Dict[str, LiveTutorSession] = {}

# Lazily-created shared LLM service (provider/model from environment)
_llm_service: Optional[LLMService] = None


def get_live_llm_service() -> LLMService:
    """Create the shared LLM service on first use."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService.from_env()
    return _llm_service


@router.websocket("/ws/live/{session_id}")
async def live_tutor_websocket(websocket: WebSocket, session_id: str) -> None:
    """
    Live camera tutoring socket for the student app.

    The client streams base64 JPEG frames and may ask questions; the backend
    runs continuous struggle detection and pushes interventions.
    """
    await websocket.accept()

    async def emit(event: Dict[str, Any]) -> None:
        """Send a JSON event to the student device."""
        try:
            await websocket.send_json(event)
        except Exception:  # noqa: BLE001 - connection may be closing
            logger.debug("Emit failed (connection closed) for %s", session_id)

    config = LiveTutorConfig()
    session = LiveTutorSession(
        session_id=session_id,
        llm_service=get_live_llm_service(),
        emit=emit,
        config=config,
    )
    live_sessions[session_id] = session

    await emit({
        "type": "connected",
        "payload": {
            "session_id": session_id,
            "message": "Live tutor ready. Send frames, then start_observation.",
            "vision_model": getattr(
                get_live_llm_service()._provider, "vision_model", None
            ),
        },
    })

    try:
        while True:
            message = await websocket.receive_json()

            msg_type = message.get("type")

            if msg_type == "frame":
                try:
                    ack = await session.ingest_frame(
                        data_b64=message.get("data", ""),
                        width=message.get("width"),
                        height=message.get("height"),
                    )
                    # Lightweight ack; not sent every frame to save bandwidth.
                    if session.frames_received % 50 == 0:
                        await emit({"type": "frames_ack", "payload": ack})
                except ValueError as exc:
                    await emit({"type": "error", "payload": {"message": str(exc)}})

            elif msg_type == "query":
                # Run concurrently so frame ingestion continues while thinking
                asyncio.create_task(session.handle_query(message.get("text", "")))

            elif msg_type == "start_observation":
                await session.start()
                await emit({
                    "type": "observation_started",
                    "payload": {"interval_s": config.observation_interval_s},
                })

            elif msg_type == "stop_observation":
                await session.stop()
                await emit({"type": "observation_stopped", "payload": {}})

            elif msg_type == "config":
                cfg = message.get("config", {})
                if "child_name" in cfg:
                    config.child_name = str(cfg["child_name"])[:40]
                if "child_age" in cfg:
                    try:
                        config.child_age = max(4, min(14, int(cfg["child_age"])))
                    except (TypeError, ValueError):
                        pass
                if "observation_interval_s" in cfg:
                    try:
                        config.observation_interval_s = max(5.0, min(120.0, float(cfg["observation_interval_s"])))
                    except (TypeError, ValueError):
                        pass
                await emit({
                    "type": "config_applied",
                    "payload": {
                        "child_name": config.child_name,
                        "child_age": config.child_age,
                        "observation_interval_s": config.observation_interval_s,
                    },
                })

            elif msg_type == "ping":
                await emit({
                    "type": "pong",
                    "payload": {"stats": session.get_stats()},
                })

            else:
                await emit({
                    "type": "error",
                    "payload": {"message": f"Unknown message type: {msg_type}"},
                })

    except WebSocketDisconnect:
        logger.info("Live tutor WebSocket disconnected: %s", session_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("Live tutor WebSocket error (%s): %s", session_id, exc)
    finally:
        # Always stop the AI loop and drop buffered frames (privacy)
        await session.stop()
        live_sessions.pop(session_id, None)


@router.get("/api/v1/live/sessions")
async def list_live_sessions() -> Dict[str, Any]:
    """List active live tutoring sessions with stats."""
    return {
        "active_sessions": [s.get_stats() for s in live_sessions.values()],
        "count": len(live_sessions),
    }
