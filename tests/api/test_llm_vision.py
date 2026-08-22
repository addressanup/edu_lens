"""Tests for multimodal LLM service support (DeepSeek vision)."""

import pytest

from src.ai.llm_service import (
    DeepSeekProvider,
    LLMConfig,
    LLMMessage,
    LLMProvider,
    LLMResponse,
    LLMService,
)


def make_image_message() -> LLMMessage:
    return LLMMessage(
        role="user",
        content=[
            {"type": "text", "text": "What is this?"},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,QUJD"}},
        ],
    )


class TestLLMMessageMultimodal:
    def test_text_only_message(self):
        msg = LLMMessage(role="user", content="hello")
        assert not msg.has_image()
        assert msg.text == "hello"
        assert msg.to_api_dict() == {"role": "user", "content": "hello"}

    def test_multimodal_message_helpers(self):
        msg = make_image_message()
        assert msg.has_image()
        assert msg.text == "What is this?"

    def test_multimodal_serialization_preserves_blocks(self):
        d = make_image_message().to_api_dict()
        assert d["role"] == "user"
        assert isinstance(d["content"], list)
        assert d["content"][1]["image_url"]["url"] == "data:image/jpeg;base64,QUJD"

    def test_name_field_serialized(self):
        msg = LLMMessage(role="user", content="hi", name="child")
        assert msg.to_api_dict()["name"] == "child"


class TestGenerateWithImage:
    @pytest.fixture
    def capturing_service(self):
        """LLMService whose provider records calls instead of hitting network."""
        svc = LLMService(provider="deepseek")
        captured = {}

        class FakeProvider:
            vision_model = DeepSeekProvider.VISION_MODEL

            async def generate(self, messages, **kwargs):
                captured["messages"] = messages
                captured["model"] = kwargs.get("model")
                return LLMResponse(
                    content="ok",
                    model=kwargs.get("model"),
                    provider=LLMProvider.DEEPSEEK,
                )

        svc._provider = FakeProvider()
        svc.captured = captured
        return svc

    @pytest.mark.asyncio
    async def test_builds_vision_payload(self, capturing_service):
        resp = await capturing_service.generate_with_image(
            prompt="describe",
            image_base64="QUJD",
            detail="low",
        )
        assert resp.content == "ok"
        assert capturing_service.captured["model"] == "deepseek-v4-flash-vision-exp"

        blocks = capturing_service.captured["messages"][-1].content
        assert blocks[0] == {"type": "text", "text": "describe"}
        url = blocks[1]["image_url"]["url"]
        assert url.startswith("data:image/jpeg;base64,")
        assert url.endswith("QUJD")
        assert blocks[1]["image_url"]["detail"] == "low"

    @pytest.mark.asyncio
    async def test_system_message_prepended(self, capturing_service):
        await capturing_service.generate_with_image(
            prompt="q", image_base64="QUJD", system="strict json"
        )
        messages = capturing_service.captured["messages"]
        assert messages[0].role == "system"
        assert messages[0].content == "strict json"
        assert messages[-1].role == "user"

    @pytest.mark.asyncio
    async def test_history_included_before_user(self, capturing_service):
        history = [
            LLMMessage(role="user", content="hi"),
            LLMMessage(role="assistant", content="hello!"),
        ]
        await capturing_service.generate_with_image(
            prompt="q", image_base64="QUJD", history=history
        )
        messages = capturing_service.captured["messages"]
        assert len(messages) == 3
        assert messages[0].content == "hi"
        assert messages[1].content == "hello!"

    @pytest.mark.asyncio
    async def test_rejects_non_vision_provider(self):
        svc = LLMService(provider="anthropic")

        class NoVision:
            pass

        svc._provider = NoVision()
        with pytest.raises(ValueError, match="does not support vision"):
            await svc.generate_with_image(prompt="q", image_base64="QUJD")


class TestSafetyFilterWithImages:
    @pytest.mark.asyncio
    async def test_system_prompt_added_without_breaking_image_blocks(self):
        config = LLMConfig(provider=LLMProvider.DEEPSEEK, safety_filter=True)
        provider = DeepSeekProvider(config)

        messages = [make_image_message()]
        filtered = provider._apply_safety_filter(messages)

        assert filtered[0].role == "system"
        assert filtered[1].has_image()
