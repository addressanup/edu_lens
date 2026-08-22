"""Tests for the LiveTutorSession (continuous observation + queries)."""

import asyncio
import base64
import json
from typing import Any, Dict, List

import pytest

from src.ai.llm_service import LLMResponse, LLMProvider, LLMService
from src.api.live_tutor import (
    LiveTutorConfig,
    LiveTutorSession,
    _parse_json_loose,
)

# 1x1 white JPEG, valid base64
TINY_JPEG_B64 = base64.b64encode(
    bytes.fromhex(
        "ffd8ffe000104a46494600010100000100010000ffdb004300ffffffffffffffff"
        "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        "ffffffffffffffffffffffffffffffffffffffffffffffc0001108000100010301"
        "2200021101031101ffc4001f000001050101010101010000000000000000010203"
        "0405060708090a0bffc400b5100002010303020403050504040000017d01020300"
        "041105122131410613516107227114328191a1082342b1c11552d1f024336272820"
        "0a16203438425163737475778394254365778495a2b33628494a4c4d4e4f5660710"
        "ffda0008010100003f00fbfa"
    )
).decode()


class FakeLLM:
    """Records generate_with_image calls and returns scripted responses."""

    def __init__(self):
        self.vision_model = "deepseek-v4-flash-vision-exp"
        self.calls: List[Dict[str, Any]] = []
        self.responses: List[str] = []

    async def generate_with_image(self, **kwargs):
        self.calls.append(kwargs)
        content = (
            self.responses.pop(0) if self.responses else '{"scene": "none"}'
        )
        return LLMResponse(
            content=content,
            model=self.vision_model,
            provider=LLMProvider.DEEPSEEK,
        )


@pytest.fixture
def session():
    """A LiveTutorSession with fake LLM and recorded emissions."""
    emitted: List[Dict[str, Any]] = []

    async def emit(event: Dict[str, Any]) -> None:
        emitted.append(event)

    llm = FakeLLM()
    config = LiveTutorConfig(observation_interval_s=0.05)
    sess = LiveTutorSession("test-session", llm, emit, config)
    sess.emitted = emitted
    sess.llm = llm
    return sess


class TestParseJsonLoose:
    def test_plain_json(self):
        assert _parse_json_loose('{"a": 1}') == {"a": 1}

    def test_markdown_fenced(self):
        text = '```json\n{"struggle_detected": true}\n```'
        assert _parse_json_loose(text)["struggle_detected"] is True

    def test_embedded_in_prose(self):
        assert _parse_json_loose('Sure! {"b": 2} hope that helps') == {"b": 2}

    def test_garbage_returns_none(self):
        assert _parse_json_loose("no json here") is None
        assert _parse_json_loose("") is None


class TestFrameIngestion:
    @pytest.mark.asyncio
    async def test_ingest_frame_buffers(self, session):
        ack = await session.ingest_frame(TINY_JPEG_B64)
        assert ack["buffered"] is True
        assert session.frames_received == 1
        assert session.get_stats()["has_buffered_frame"] is True

    @pytest.mark.asyncio
    async def test_oversized_frame_rejected(self, session):
        session.config.max_frame_bytes = 10
        with pytest.raises(ValueError, match="too large"):
            await session.ingest_frame("x" * 100)

    @pytest.mark.asyncio
    async def test_stop_clears_frames(self, session):
        await session.ingest_frame(TINY_JPEG_B64)
        await session.stop()
        assert session.get_stats()["has_buffered_frame"] is False


class TestObservationLoop:
    @pytest.mark.asyncio
    async def test_intervention_emitted_on_struggle(self, session):
        observation = json.dumps({
            "scene": "math worksheet",
            "subject": "math",
            "child_present": True,
            "engagement": "stuck",
            "struggle_detected": True,
            "confidence": 0.9,
            "intervention_message": "Try counting the apples one by one!",
        })
        session.llm.responses.append(observation)

        await session.ingest_frame(TINY_JPEG_B64)
        await session.start()
        # Wait for at least one observation pass
        for _ in range(40):
            if session.observations_run > 0:
                break
            await asyncio.sleep(0.05)
        await session.stop()

        assert session.observations_run >= 1
        obs_events = [e for e in session.emitted if e["type"] == "observation"]
        assert len(obs_events) >= 1
        payload = obs_events[0]["payload"]
        assert payload["struggle_detected"] is True
        assert payload["intervention"] == "Try counting the apples one by one!"
        assert session.interventions_sent == 1

    @pytest.mark.asyncio
    async def test_no_intervention_below_confidence(self, session):
        observation = json.dumps({
            "scene": "worksheet",
            "struggle_detected": True,
            "confidence": 0.3,
            "intervention_message": "hint",
        })
        session.llm.responses.append(observation)

        await session.ingest_frame(TINY_JPEG_B64)
        await session.start()
        for _ in range(40):
            if session.observations_run > 0:
                break
            await asyncio.sleep(0.05)
        await session.stop()

        obs_events = [e for e in session.emitted if e["type"] == "observation"]
        assert obs_events[0]["payload"]["intervention"] is None
        assert session.interventions_sent == 0

    @pytest.mark.asyncio
    async def test_cooldown_prevents_spam(self, session):
        observation = json.dumps({
            "scene": "worksheet",
            "struggle_detected": True,
            "confidence": 0.95,
            "intervention_message": "hint",
        })
        session.llm.responses = [observation] * 10
        session.config.intervention_cooldown_s = 60.0

        await session.ingest_frame(TINY_JPEG_B64)
        await session.start()
        for _ in range(60):
            if session.observations_run >= 3:
                break
            await asyncio.sleep(0.05)
        await session.stop()

        assert session.interventions_sent == 1

    @pytest.mark.asyncio
    async def test_unparseable_response_does_not_crash_loop(self, session):
        session.llm.responses.append("I am sorry, I cannot comply.")
        await session.ingest_frame(TINY_JPEG_B64)
        await session.start()
        for _ in range(40):
            if session.observations_run > 0:
                break
            await asyncio.sleep(0.05)
        # Loop should still be alive and no crash propagated
        assert session.active or not session._observation_task.done()


class TestQueryHandling:
    @pytest.mark.asyncio
    async def test_query_attaches_latest_frame_and_emits_response(self, session):
        session.llm.responses.append("Count the tens first!")
        await session.ingest_frame(TINY_JPEG_B64)
        await session.handle_query("I am stuck on problem 3")

        call = session.llm.calls[0]
        assert "problem 3" in call["prompt"]
        assert call["image_base64"] == TINY_JPEG_B64

        responses = [e for e in session.emitted if e["type"] == "tutor_response"]
        assert len(responses) == 1
        assert responses[0]["payload"]["text"] == "Count the tens first!"
        assert session.queries_answered == 1

    @pytest.mark.asyncio
    async def test_empty_query_emits_error(self, session):
        await session.handle_query("   ")
        errors = [e for e in session.emitted if e["type"] == "error"]
        assert len(errors) == 1

    @pytest.mark.asyncio
    async def test_llm_failure_emits_friendly_error(self, session):
        async def boom(**kwargs):
            raise RuntimeError("api down")

        session.llm.generate_with_image = boom
        await session.ingest_frame(TINY_JPEG_B64)
        await session.handle_query("help")
        errors = [e for e in session.emitted if e["type"] == "error"]
        assert len(errors) == 1
        assert "try again" in errors[0]["payload"]["message"].lower()

    @pytest.mark.asyncio
    async def test_history_bounded(self, session):
        session.llm.responses = ["ok"] * 20
        await session.ingest_frame(TINY_JPEG_B64)
        for i in range(10):
            await session.handle_query(f"q{i}")
        assert len(session._history) <= session.config.max_history_messages
