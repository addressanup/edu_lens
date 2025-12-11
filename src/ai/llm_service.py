"""
EduLens LLM Service - Multi-Provider AI Integration

Supports multiple cloud AI providers with a unified interface:
- Anthropic Claude
- OpenAI GPT
- Google Gemini
- Azure OpenAI
- AWS Bedrock
- Custom/Local models

Author: EduLens AI Team
Version: 1.0.0
"""

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    DEEPSEEK = "deepseek"
    AZURE_OPENAI = "azure_openai"
    AWS_BEDROCK = "aws_bedrock"
    OLLAMA = "ollama"  # Local models
    CUSTOM = "custom"


@dataclass
class LLMConfig:
    """Configuration for LLM service."""
    provider: LLMProvider = LLMProvider.ANTHROPIC
    model: str = "claude-sonnet-4-20250514"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 1024
    temperature: float = 0.7
    timeout: int = 30
    max_retries: int = 3

    # Provider-specific settings
    azure_endpoint: Optional[str] = None
    azure_deployment: Optional[str] = None
    aws_region: Optional[str] = None

    # Safety settings for child content
    safety_filter: bool = True
    max_response_length: int = 500  # Words, for child-appropriate responses

    def __post_init__(self):
        """Load API keys from environment if not provided."""
        if self.api_key is None:
            env_keys = {
                LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
                LLMProvider.OPENAI: "OPENAI_API_KEY",
                LLMProvider.GOOGLE: "GOOGLE_API_KEY",
                LLMProvider.DEEPSEEK: "DEEPSEEK_API_KEY",
                LLMProvider.AZURE_OPENAI: "AZURE_OPENAI_API_KEY",
            }
            env_key = env_keys.get(self.provider)
            if env_key:
                self.api_key = os.getenv(env_key)


@dataclass
class LLMMessage:
    """A message in a conversation."""
    role: str  # "system", "user", "assistant"
    content: str
    name: Optional[str] = None


@dataclass
class LLMResponse:
    """Response from LLM."""
    content: str
    model: str
    provider: LLMProvider
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: LLMConfig):
        self.config = config

    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> LLMResponse:
        """Generate a response from the LLM."""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response from the LLM."""
        pass

    def _apply_safety_filter(
        self,
        messages: List[LLMMessage],
        child_profile: Optional[Dict[str, Any]] = None,
        context: Optional[str] = None,
    ) -> List[LLMMessage]:
        """
        Add safety instructions for child-appropriate content.

        Uses the dynamic prompt builder when a child profile is provided
        to create age-appropriate, personalized system prompts.

        Args:
            messages: List of messages to process
            child_profile: Optional child profile dict with name, age, grade, etc.
            context: Optional context string (e.g., current subject)

        Returns:
            Messages with safety/personalized system prompt prepended
        """
        if not self.config.safety_filter:
            return messages

        # Try to use dynamic prompt builder if child profile is available
        if child_profile:
            try:
                from src.ai.prompt_builder import build_prompt_from_db_child
                system_content = build_prompt_from_db_child(
                    child_data=child_profile,
                    context=context,
                    voice_mode=False,
                )
            except ImportError:
                # Fallback to default if prompt_builder not available
                system_content = self._get_default_safety_prompt()
        else:
            system_content = self._get_default_safety_prompt()

        safety_system = LLMMessage(role="system", content=system_content)

        # Prepend safety system message
        if messages and messages[0].role == "system":
            messages[0].content = safety_system.content + "\n\n" + messages[0].content
            return messages
        else:
            return [safety_system] + messages

    def _get_default_safety_prompt(self) -> str:
        """Get default safety prompt for when no child profile is available."""
        return (
            "You are EduLens, a friendly and encouraging AI tutor for children.\n\n"
            "PERSONALITY:\n"
            "- Warm, patient, and encouraging\n"
            "- Speaks in a way appropriate for elementary school children (ages 6-12)\n"
            "- Uses simple, clear language\n"
            "- Makes learning feel like an adventure\n\n"
            "RESPONSE STYLE:\n"
            "- Keep responses short (2-3 sentences)\n"
            "- Use age-appropriate vocabulary\n"
            "- Ask engaging questions\n"
            "- Celebrate curiosity and effort\n\n"
            "CRITICAL SAFETY RULES:\n"
            "1. Never provide inappropriate, violent, or adult content\n"
            "2. Never ask for or reference personal information\n"
            "3. Use age-appropriate language and explanations\n"
            "4. Be encouraging, patient, and supportive\n"
            "5. Use the Socratic method - guide to answers, don't give them directly\n"
            "6. Keep responses concise and engaging\n"
            "7. If asked about inappropriate topics, redirect to learning\n"
        )


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.config.api_key)
            except ImportError:
                raise ImportError("anthropic package required. Install with: pip install anthropic")
        return self._client

    async def generate(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> LLMResponse:
        client = self._get_client()
        messages = self._apply_safety_filter(messages)

        # Separate system message from conversation
        system_content = ""
        conversation = []
        for msg in messages:
            if msg.role == "system":
                system_content += msg.content + "\n"
            else:
                conversation.append({"role": msg.role, "content": msg.content})

        response = client.messages.create(
            model=kwargs.get("model", self.config.model),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
            system=system_content.strip() if system_content else None,
            messages=conversation
        )

        return LLMResponse(
            content=response.content[0].text,
            model=response.model,
            provider=LLMProvider.ANTHROPIC,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            },
            finish_reason=response.stop_reason
        )

    async def generate_stream(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        client = self._get_client()
        messages = self._apply_safety_filter(messages)

        system_content = ""
        conversation = []
        for msg in messages:
            if msg.role == "system":
                system_content += msg.content + "\n"
            else:
                conversation.append({"role": msg.role, "content": msg.content})

        with client.messages.stream(
            model=kwargs.get("model", self.config.model),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
            system=system_content.strip() if system_content else None,
            messages=conversation
        ) as stream:
            for text in stream.text_stream:
                yield text


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.config.api_key,
                    base_url=self.config.base_url
                )
            except ImportError:
                raise ImportError("openai package required. Install with: pip install openai")
        return self._client

    async def generate(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> LLMResponse:
        client = self._get_client()
        messages = self._apply_safety_filter(messages)

        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        response = client.chat.completions.create(
            model=kwargs.get("model", self.config.model),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
            messages=openai_messages
        )

        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            provider=LLMProvider.OPENAI,
            usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens
            },
            finish_reason=response.choices[0].finish_reason
        )

    async def generate_stream(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        client = self._get_client()
        messages = self._apply_safety_filter(messages)

        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        stream = client.chat.completions.create(
            model=kwargs.get("model", self.config.model),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
            messages=openai_messages,
            stream=True
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek provider (OpenAI-compatible API)."""

    DEEPSEEK_BASE_URL = "https://api.deepseek.com"

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.config.api_key,
                    base_url=self.config.base_url or self.DEEPSEEK_BASE_URL
                )
            except ImportError:
                raise ImportError("openai package required for DeepSeek. Install with: pip install openai")
        return self._client

    async def generate(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> LLMResponse:
        client = self._get_client()
        messages = self._apply_safety_filter(messages)

        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        response = client.chat.completions.create(
            model=kwargs.get("model", self.config.model),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
            messages=openai_messages
        )

        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            provider=LLMProvider.DEEPSEEK,
            usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens
            },
            finish_reason=response.choices[0].finish_reason
        )

    async def generate_stream(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        client = self._get_client()
        messages = self._apply_safety_filter(messages)

        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        stream = client.chat.completions.create(
            model=kwargs.get("model", self.config.model),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
            messages=openai_messages,
            stream=True
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class GoogleProvider(BaseLLMProvider):
    """Google Gemini provider."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.config.api_key)
                self._client = genai.GenerativeModel(self.config.model)
            except ImportError:
                raise ImportError("google-generativeai package required. Install with: pip install google-generativeai")
        return self._client

    async def generate(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> LLMResponse:
        client = self._get_client()
        messages = self._apply_safety_filter(messages)

        # Convert to Gemini format
        history = []
        system_instruction = ""

        for msg in messages:
            if msg.role == "system":
                system_instruction += msg.content + "\n"
            elif msg.role == "user":
                history.append({"role": "user", "parts": [msg.content]})
            elif msg.role == "assistant":
                history.append({"role": "model", "parts": [msg.content]})

        # Start chat with history
        chat = client.start_chat(history=history[:-1] if history else [])

        # Get last user message
        last_message = history[-1]["parts"][0] if history else ""
        if system_instruction:
            last_message = f"{system_instruction}\n\n{last_message}"

        response = chat.send_message(
            last_message,
            generation_config={
                "max_output_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "temperature": kwargs.get("temperature", self.config.temperature),
            }
        )

        return LLMResponse(
            content=response.text,
            model=self.config.model,
            provider=LLMProvider.GOOGLE,
            usage={},
            finish_reason="stop"
        )

    async def generate_stream(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        client = self._get_client()
        messages = self._apply_safety_filter(messages)

        history = []
        system_instruction = ""

        for msg in messages:
            if msg.role == "system":
                system_instruction += msg.content + "\n"
            elif msg.role == "user":
                history.append({"role": "user", "parts": [msg.content]})
            elif msg.role == "assistant":
                history.append({"role": "model", "parts": [msg.content]})

        chat = client.start_chat(history=history[:-1] if history else [])
        last_message = history[-1]["parts"][0] if history else ""
        if system_instruction:
            last_message = f"{system_instruction}\n\n{last_message}"

        response = chat.send_message(
            last_message,
            generation_config={
                "max_output_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "temperature": kwargs.get("temperature", self.config.temperature),
            },
            stream=True
        )

        for chunk in response:
            if chunk.text:
                yield chunk.text


class OllamaProvider(BaseLLMProvider):
    """Ollama local model provider."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.base_url or "http://localhost:11434"

    async def generate(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> LLMResponse:
        import httpx

        messages = self._apply_safety_filter(messages)

        ollama_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": kwargs.get("model", self.config.model),
                    "messages": ollama_messages,
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", self.config.temperature),
                        "num_predict": kwargs.get("max_tokens", self.config.max_tokens),
                    }
                },
                timeout=self.config.timeout
            )
            data = response.json()

        return LLMResponse(
            content=data["message"]["content"],
            model=data.get("model", self.config.model),
            provider=LLMProvider.OLLAMA,
            usage={
                "input_tokens": data.get("prompt_eval_count", 0),
                "output_tokens": data.get("eval_count", 0)
            },
            finish_reason="stop"
        )

    async def generate_stream(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        import httpx

        messages = self._apply_safety_filter(messages)

        ollama_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": kwargs.get("model", self.config.model),
                    "messages": ollama_messages,
                    "stream": True,
                    "options": {
                        "temperature": kwargs.get("temperature", self.config.temperature),
                        "num_predict": kwargs.get("max_tokens", self.config.max_tokens),
                    }
                },
                timeout=self.config.timeout
            ) as response:
                import json
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            yield data["message"]["content"]


class LLMService:
    """
    Main LLM service providing a unified interface for all providers.

    Usage:
        # Using environment variables for API keys
        service = LLMService(provider="anthropic", model="claude-sonnet-4-20250514")

        # Or with explicit config
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4",
            api_key="sk-..."
        )
        service = LLMService(config=config)

        # Generate response
        response = await service.generate([
            LLMMessage(role="user", content="What is 2+2?")
        ])
        print(response.content)
    """

    PROVIDER_MAP = {
        LLMProvider.ANTHROPIC: AnthropicProvider,
        LLMProvider.OPENAI: OpenAIProvider,
        LLMProvider.GOOGLE: GoogleProvider,
        LLMProvider.DEEPSEEK: DeepSeekProvider,
        LLMProvider.OLLAMA: OllamaProvider,
    }

    def __init__(
        self,
        config: Optional[LLMConfig] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize LLM service.

        Args:
            config: Full LLMConfig object
            provider: Provider name (anthropic, openai, google, ollama)
            model: Model name
            api_key: API key (or use environment variable)
            **kwargs: Additional config options
        """
        if config:
            self.config = config
        else:
            provider_enum = LLMProvider(provider) if provider else LLMProvider.ANTHROPIC
            self.config = LLMConfig(
                provider=provider_enum,
                model=model or self._default_model(provider_enum),
                api_key=api_key,
                **kwargs
            )

        provider_class = self.PROVIDER_MAP.get(self.config.provider)
        if not provider_class:
            raise ValueError(f"Unsupported provider: {self.config.provider}")

        self._provider = provider_class(self.config)
        logger.info(f"Initialized LLM service with {self.config.provider.value}/{self.config.model}")

    def _default_model(self, provider: LLMProvider) -> str:
        """Get default model for provider."""
        defaults = {
            LLMProvider.ANTHROPIC: "claude-sonnet-4-20250514",
            LLMProvider.OPENAI: "gpt-4o",
            LLMProvider.GOOGLE: "gemini-1.5-flash",
            LLMProvider.DEEPSEEK: "deepseek-chat",
            LLMProvider.OLLAMA: "llama3.2:3b",
        }
        return defaults.get(provider, "default")

    async def generate(
        self,
        messages: Union[List[LLMMessage], List[Dict[str, str]], str],
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            messages: Either:
                - List of LLMMessage objects
                - List of dicts with 'role' and 'content'
                - Single string (converted to user message)
            **kwargs: Override config (model, temperature, max_tokens, etc.)

        Returns:
            LLMResponse with content and metadata
        """
        # Normalize messages
        if isinstance(messages, str):
            messages = [LLMMessage(role="user", content=messages)]
        elif messages and isinstance(messages[0], dict):
            messages = [LLMMessage(**m) for m in messages]

        return await self._provider.generate(messages, **kwargs)

    async def generate_stream(
        self,
        messages: Union[List[LLMMessage], List[Dict[str, str]], str],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response."""
        if isinstance(messages, str):
            messages = [LLMMessage(role="user", content=messages)]
        elif messages and isinstance(messages[0], dict):
            messages = [LLMMessage(**m) for m in messages]

        async for chunk in self._provider.generate_stream(messages, **kwargs):
            yield chunk

    def generate_sync(
        self,
        messages: Union[List[LLMMessage], List[Dict[str, str]], str],
        **kwargs
    ) -> LLMResponse:
        """Synchronous wrapper for generate()."""
        return asyncio.run(self.generate(messages, **kwargs))

    @classmethod
    def from_env(cls, provider: Optional[str] = None) -> "LLMService":
        """
        Create LLM service from environment variables.

        Environment variables:
            LLM_PROVIDER: anthropic, openai, google, ollama
            LLM_MODEL: Model name
            ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY: API keys
        """
        provider = provider or os.getenv("LLM_PROVIDER", "anthropic")
        model = os.getenv("LLM_MODEL")

        return cls(provider=provider, model=model)


# Convenience function for quick usage
async def generate_response(
    prompt: str,
    provider: str = "anthropic",
    model: Optional[str] = None,
    **kwargs
) -> str:
    """
    Quick function to generate a response.

    Args:
        prompt: User prompt
        provider: LLM provider name
        model: Model name (uses default if not specified)
        **kwargs: Additional options

    Returns:
        Generated text response
    """
    service = LLMService(provider=provider, model=model)
    response = await service.generate(prompt, **kwargs)
    return response.content


# Export all public classes
__all__ = [
    "LLMProvider",
    "LLMConfig",
    "LLMMessage",
    "LLMResponse",
    "LLMService",
    "generate_response",
    "BaseLLMProvider",
    "AnthropicProvider",
    "OpenAIProvider",
    "GoogleProvider",
    "DeepSeekProvider",
    "OllamaProvider",
]
