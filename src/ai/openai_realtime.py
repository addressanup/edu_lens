"""
OpenAI Realtime API Service for EduLens

Provides native voice conversation capabilities using GPT-4o's
Realtime API with WebSocket-based bidirectional audio streaming.

Benefits:
- Native voice generation (no separate TTS needed)
- Low latency (~300ms response time)
- Natural conversational flow
- Voice Activity Detection (VAD) built-in
- Emotional expression in speech

Protocol:
- WebSocket connection to wss://api.openai.com/v1/realtime
- Audio format: 16kHz/24kHz mono PCM16
- Event-driven JSON protocol with binary audio chunks
"""

import asyncio
import base64
import json
import logging
import os
import struct
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

# Import prompt builder for dynamic child-adaptive prompts
from src.ai.prompt_builder import (
    ChildProfile,
    build_voice_system_prompt,
    get_default_edulens_prompt,
)

logger = logging.getLogger(__name__)


class RealtimeEventType(Enum):
    """OpenAI Realtime API event types."""

    # Session events
    SESSION_CREATE = "session.create"
    SESSION_UPDATE = "session.update"
    SESSION_CREATED = "session.created"
    SESSION_UPDATED = "session.updated"

    # Input audio events
    INPUT_AUDIO_BUFFER_APPEND = "input_audio_buffer.append"
    INPUT_AUDIO_BUFFER_COMMIT = "input_audio_buffer.commit"
    INPUT_AUDIO_BUFFER_CLEAR = "input_audio_buffer.clear"
    INPUT_AUDIO_BUFFER_COMMITTED = "input_audio_buffer.committed"
    INPUT_AUDIO_BUFFER_CLEARED = "input_audio_buffer.cleared"
    INPUT_AUDIO_BUFFER_SPEECH_STARTED = "input_audio_buffer.speech_started"
    INPUT_AUDIO_BUFFER_SPEECH_STOPPED = "input_audio_buffer.speech_stopped"

    # Conversation events
    CONVERSATION_ITEM_CREATE = "conversation.item.create"
    CONVERSATION_ITEM_CREATED = "conversation.item.created"
    CONVERSATION_ITEM_TRUNCATE = "conversation.item.truncate"
    CONVERSATION_ITEM_DELETE = "conversation.item.delete"
    CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_COMPLETED = (
        "conversation.item.input_audio_transcription.completed"
    )

    # Response events
    RESPONSE_CREATE = "response.create"
    RESPONSE_CREATED = "response.created"
    RESPONSE_DONE = "response.done"
    RESPONSE_CANCEL = "response.cancel"
    RESPONSE_OUTPUT_ITEM_ADDED = "response.output_item.added"
    RESPONSE_OUTPUT_ITEM_DONE = "response.output_item.done"
    RESPONSE_CONTENT_PART_ADDED = "response.content_part.added"
    RESPONSE_CONTENT_PART_DONE = "response.content_part.done"
    RESPONSE_TEXT_DELTA = "response.text.delta"
    RESPONSE_TEXT_DONE = "response.text.done"
    RESPONSE_AUDIO_DELTA = "response.audio.delta"
    RESPONSE_AUDIO_DONE = "response.audio.done"
    RESPONSE_AUDIO_TRANSCRIPT_DELTA = "response.audio_transcript.delta"
    RESPONSE_AUDIO_TRANSCRIPT_DONE = "response.audio_transcript.done"
    RESPONSE_FUNCTION_CALL_ARGUMENTS_DELTA = "response.function_call_arguments.delta"
    RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE = "response.function_call_arguments.done"

    # Rate limit events
    RATE_LIMITS_UPDATED = "rate_limits.updated"

    # Error events
    ERROR = "error"


class ConnectionState(Enum):
    """WebSocket connection states."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    READY = "ready"
    LISTENING = "listening"
    RESPONDING = "responding"
    ERROR = "error"


@dataclass
class RealtimeConfig:
    """Configuration for OpenAI Realtime API."""

    api_key: Optional[str] = None
    model: str = "gpt-4o-realtime-preview-2024-12-17"

    # Audio settings
    input_audio_format: str = "pcm16"  # pcm16 or g711_ulaw or g711_alaw
    output_audio_format: str = "pcm16"
    sample_rate: int = 24000  # 24kHz for high quality

    # Voice settings (alloy, echo, fable, onyx, nova, shimmer)
    voice: str = "nova"  # Nova is friendly and warm

    # VAD settings
    turn_detection_type: str = "server_vad"  # server_vad or none
    vad_threshold: float = 0.5
    vad_prefix_padding_ms: int = 300
    vad_silence_duration_ms: int = 500

    # Conversation settings
    system_prompt: str = ""
    temperature: float = 0.7
    max_response_tokens: int = 1024

    # Transcription
    input_audio_transcription_model: str = "whisper-1"

    def __post_init__(self):
        """Load API key from environment if not provided."""
        if self.api_key is None:
            self.api_key = os.getenv("OPENAI_API_KEY")


@dataclass
class AudioChunk:
    """Audio data chunk."""

    data: bytes
    sample_rate: int = 24000
    channels: int = 1
    timestamp: float = field(default_factory=time.time)


@dataclass
class TranscriptEvent:
    """Transcription event."""

    text: str
    is_final: bool = False
    role: str = "user"  # user or assistant
    timestamp: float = field(default_factory=time.time)


@dataclass
class ResponseEvent:
    """Response event from the model."""

    text: str
    audio_data: Optional[bytes] = None
    is_complete: bool = False
    timestamp: float = field(default_factory=time.time)


class OpenAIRealtimeService:
    """
    OpenAI Realtime API service for native voice conversation.

    Provides:
    - WebSocket connection management
    - Audio streaming (send/receive)
    - Event handling
    - Conversation state management
    """

    WEBSOCKET_URL = "wss://api.openai.com/v1/realtime"

    def __init__(
        self,
        config: Optional[RealtimeConfig] = None,
        on_transcript: Optional[Callable[[TranscriptEvent], Awaitable[None]]] = None,
        on_audio: Optional[Callable[[AudioChunk], Awaitable[None]]] = None,
        on_response: Optional[Callable[[ResponseEvent], Awaitable[None]]] = None,
        on_state_change: Optional[Callable[[ConnectionState], Awaitable[None]]] = None,
    ):
        """
        Initialize the Realtime service.

        Args:
            config: Service configuration
            on_transcript: Callback for transcription events
            on_audio: Callback for audio output chunks
            on_response: Callback for response events
            on_state_change: Callback for state changes
        """
        self.config = config or RealtimeConfig()
        self.on_transcript = on_transcript
        self.on_audio = on_audio
        self.on_response = on_response
        self.on_state_change = on_state_change

        self.websocket = None
        self.state = ConnectionState.DISCONNECTED
        self._receive_task: Optional[asyncio.Task] = None
        self._audio_buffer: List[bytes] = []
        self._response_text: str = ""
        self._response_audio: List[bytes] = []
        self.session_id: Optional[str] = None

        # Statistics
        self.connected_at: Optional[float] = None
        self.audio_chunks_sent: int = 0
        self.audio_chunks_received: int = 0
        self.responses_received: int = 0

    async def _set_state(self, state: ConnectionState) -> None:
        """Update state and notify callback."""
        self.state = state
        if self.on_state_change:
            try:
                await self.on_state_change(state)
            except Exception as e:
                logger.warning(f"State change callback error: {e}")

    async def connect(self) -> bool:
        """
        Connect to the OpenAI Realtime API.

        Returns:
            True if connection successful
        """
        if not self.config.api_key:
            logger.error("No OpenAI API key configured")
            return False

        await self._set_state(ConnectionState.CONNECTING)

        try:
            import websockets

            url = f"{self.WEBSOCKET_URL}?model={self.config.model}"
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "OpenAI-Beta": "realtime=v1",
            }

            logger.info(f"Connecting to OpenAI Realtime API...")
            self.websocket = await websockets.connect(
                url,
                extra_headers=headers,
                ping_interval=30,
                ping_timeout=10,
            )

            await self._set_state(ConnectionState.CONNECTED)
            self.connected_at = time.time()

            # Start receive loop
            self._receive_task = asyncio.create_task(self._receive_loop())

            # Configure session
            await self._configure_session()

            logger.info("Connected to OpenAI Realtime API")
            return True

        except ImportError:
            logger.error("websockets package not installed. Run: pip install websockets")
            await self._set_state(ConnectionState.ERROR)
            return False

        except Exception as e:
            logger.error(f"Failed to connect to Realtime API: {e}")
            await self._set_state(ConnectionState.ERROR)
            return False

    async def _configure_session(self) -> None:
        """Configure the realtime session with our settings."""
        session_config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "voice": self.config.voice,
                "input_audio_format": self.config.input_audio_format,
                "output_audio_format": self.config.output_audio_format,
                "input_audio_transcription": {"model": self.config.input_audio_transcription_model},
                "turn_detection": {
                    "type": self.config.turn_detection_type,
                    "threshold": self.config.vad_threshold,
                    "prefix_padding_ms": self.config.vad_prefix_padding_ms,
                    "silence_duration_ms": self.config.vad_silence_duration_ms,
                },
                "temperature": self.config.temperature,
                "max_response_output_tokens": self.config.max_response_tokens,
            },
        }

        # Add system prompt if configured
        if self.config.system_prompt:
            session_config["session"]["instructions"] = self.config.system_prompt

        await self._send_event(session_config)
        logger.debug("Session configured")

    async def _send_event(self, event: Dict[str, Any]) -> None:
        """Send a JSON event to the WebSocket."""
        if not self.websocket:
            raise RuntimeError("Not connected")

        await self.websocket.send(json.dumps(event))

    async def _receive_loop(self) -> None:
        """Main loop for receiving events from the API."""
        try:
            async for message in self.websocket:
                if isinstance(message, str):
                    await self._handle_event(json.loads(message))
                else:
                    # Binary message (shouldn't happen with this API)
                    logger.warning(f"Received unexpected binary message: {len(message)} bytes")

        except asyncio.CancelledError:
            logger.debug("Receive loop cancelled")

        except Exception as e:
            error_msg = str(e).lower()
            if "close" in error_msg or "disconnect" in error_msg:
                logger.info("WebSocket connection closed")
            else:
                logger.error(f"Receive loop error: {e}")
            await self._set_state(ConnectionState.ERROR)

    async def _handle_event(self, event: Dict[str, Any]) -> None:
        """Handle an event from the API."""
        event_type = event.get("type", "")

        try:
            # Session events
            if event_type == "session.created":
                self.session_id = event.get("session", {}).get("id")
                await self._set_state(ConnectionState.READY)
                logger.info(f"Session created: {self.session_id}")

            elif event_type == "session.updated":
                logger.debug("Session updated")

            # Input audio events
            elif event_type == "input_audio_buffer.speech_started":
                await self._set_state(ConnectionState.LISTENING)
                logger.debug("Speech started")

            elif event_type == "input_audio_buffer.speech_stopped":
                logger.debug("Speech stopped")

            elif event_type == "input_audio_buffer.committed":
                logger.debug("Audio buffer committed")

            # Transcription events
            elif event_type == "conversation.item.input_audio_transcription.completed":
                transcript = event.get("transcript", "")
                if transcript and self.on_transcript:
                    await self.on_transcript(
                        TranscriptEvent(text=transcript, is_final=True, role="user")
                    )

            # Response events
            elif event_type == "response.created":
                self._response_text = ""
                self._response_audio = []
                await self._set_state(ConnectionState.RESPONDING)
                logger.debug("Response started")

            elif event_type == "response.audio.delta":
                # Decode base64 audio chunk
                audio_b64 = event.get("delta", "")
                if audio_b64:
                    audio_data = base64.b64decode(audio_b64)
                    self._response_audio.append(audio_data)
                    self.audio_chunks_received += 1

                    if self.on_audio:
                        await self.on_audio(
                            AudioChunk(data=audio_data, sample_rate=self.config.sample_rate)
                        )

            elif event_type == "response.audio_transcript.delta":
                delta = event.get("delta", "")
                self._response_text += delta

            elif event_type == "response.audio_transcript.done":
                transcript = event.get("transcript", self._response_text)
                if self.on_transcript:
                    await self.on_transcript(
                        TranscriptEvent(text=transcript, is_final=True, role="assistant")
                    )

            elif event_type == "response.done":
                self.responses_received += 1

                # Combine all audio chunks
                full_audio = b"".join(self._response_audio) if self._response_audio else None

                if self.on_response:
                    await self.on_response(
                        ResponseEvent(
                            text=self._response_text, audio_data=full_audio, is_complete=True
                        )
                    )

                await self._set_state(ConnectionState.READY)
                logger.debug(f"Response complete: {len(self._response_text)} chars")

            elif event_type == "response.text.delta":
                delta = event.get("delta", "")
                self._response_text += delta

            elif event_type == "response.text.done":
                text = event.get("text", self._response_text)
                if self.on_response and not self._response_audio:
                    # Text-only response
                    await self.on_response(ResponseEvent(text=text, is_complete=True))

            # Error events
            elif event_type == "error":
                error = event.get("error", {})
                logger.error(f"Realtime API error: {error}")
                await self._set_state(ConnectionState.ERROR)

            # Rate limits
            elif event_type == "rate_limits.updated":
                logger.debug(f"Rate limits: {event.get('rate_limits', [])}")

            else:
                logger.debug(f"Unhandled event: {event_type}")

        except Exception as e:
            logger.error(f"Error handling event {event_type}: {e}")

    async def send_audio(self, audio_data: bytes) -> None:
        """
        Send audio data to the API.

        Args:
            audio_data: PCM16 audio data at configured sample rate
        """
        if self.state not in (ConnectionState.READY, ConnectionState.LISTENING):
            logger.warning(f"Cannot send audio in state: {self.state}")
            return

        # Encode audio as base64
        audio_b64 = base64.b64encode(audio_data).decode("utf-8")

        await self._send_event({"type": "input_audio_buffer.append", "audio": audio_b64})

        self.audio_chunks_sent += 1

    async def commit_audio(self) -> None:
        """Commit the audio buffer to trigger processing."""
        await self._send_event({"type": "input_audio_buffer.commit"})

    async def clear_audio_buffer(self) -> None:
        """Clear the audio input buffer."""
        await self._send_event({"type": "input_audio_buffer.clear"})

    async def send_text(self, text: str) -> None:
        """
        Send a text message to get a voice response.

        Args:
            text: Text message to send
        """
        if self.state != ConnectionState.READY:
            logger.warning(f"Cannot send text in state: {self.state}")
            return

        # Create conversation item with user message
        await self._send_event(
            {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": text}],
                },
            }
        )

        # Request response
        await self._send_event({"type": "response.create"})

    async def cancel_response(self) -> None:
        """Cancel the current response generation."""
        if self.state == ConnectionState.RESPONDING:
            await self._send_event({"type": "response.cancel"})

    async def disconnect(self) -> None:
        """Disconnect from the API."""
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        if self.websocket:
            try:
                await self.websocket.close()
            except Exception:
                pass

        self.websocket = None
        await self._set_state(ConnectionState.DISCONNECTED)
        logger.info("Disconnected from OpenAI Realtime API")

    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            "state": self.state.value,
            "session_id": self.session_id,
            "connected_at": self.connected_at,
            "uptime_seconds": time.time() - self.connected_at if self.connected_at else 0,
            "audio_chunks_sent": self.audio_chunks_sent,
            "audio_chunks_received": self.audio_chunks_received,
            "responses_received": self.responses_received,
        }


class RealtimeVoiceConversation:
    """
    High-level voice conversation manager using OpenAI Realtime API.

    Provides a simple interface for:
    - Starting voice conversations
    - Sending audio from microphone
    - Playing audio responses
    - Getting transcripts
    """

    def __init__(
        self,
        system_prompt: str = "",
        voice: str = "nova",
        on_assistant_speaking: Optional[Callable[[str, bytes], Awaitable[None]]] = None,
        on_user_transcript: Optional[Callable[[str], Awaitable[None]]] = None,
    ):
        """
        Initialize voice conversation.

        Args:
            system_prompt: System instructions for the assistant
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
            on_assistant_speaking: Callback when assistant speaks (text, audio_data)
            on_user_transcript: Callback when user speech is transcribed
        """
        self.system_prompt = system_prompt
        self.voice = voice
        self.on_assistant_speaking = on_assistant_speaking
        self.on_user_transcript = on_user_transcript

        self._service: Optional[OpenAIRealtimeService] = None
        self._audio_queue: asyncio.Queue = asyncio.Queue()
        self._is_running = False

    async def start(self) -> bool:
        """Start the voice conversation."""
        config = RealtimeConfig(
            voice=self.voice,
            system_prompt=self.system_prompt,
            sample_rate=24000,
        )

        self._service = OpenAIRealtimeService(
            config=config,
            on_transcript=self._handle_transcript,
            on_audio=self._handle_audio,
            on_response=self._handle_response,
        )

        if await self._service.connect():
            self._is_running = True
            return True
        return False

    async def _handle_transcript(self, event: TranscriptEvent) -> None:
        """Handle transcription events."""
        if event.role == "user" and self.on_user_transcript:
            await self.on_user_transcript(event.text)

    async def _handle_audio(self, chunk: AudioChunk) -> None:
        """Handle audio output chunks."""
        await self._audio_queue.put(chunk)

    async def _handle_response(self, event: ResponseEvent) -> None:
        """Handle response completion."""
        if event.is_complete and self.on_assistant_speaking:
            await self.on_assistant_speaking(event.text, event.audio_data)

    async def send_audio_chunk(self, audio_data: bytes) -> None:
        """Send an audio chunk from the microphone."""
        if self._service and self._is_running:
            await self._service.send_audio(audio_data)

    async def get_audio_chunk(self, timeout: float = 0.1) -> Optional[AudioChunk]:
        """Get the next audio chunk to play."""
        try:
            return await asyncio.wait_for(self._audio_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    async def send_text(self, text: str) -> None:
        """Send text and get voice response."""
        if self._service:
            await self._service.send_text(text)

    async def stop(self) -> None:
        """Stop the conversation."""
        self._is_running = False
        if self._service:
            await self._service.disconnect()
            self._service = None

    @property
    def is_ready(self) -> bool:
        """Check if ready for conversation."""
        return self._service is not None and self._service.state == ConnectionState.READY


# Default system prompt for EduLens
EDULENS_SYSTEM_PROMPT = """You are EduLens, a friendly and encouraging AI tutor integrated into smart glasses for children aged 5-12.

Your personality:
- Warm, patient, and enthusiastic
- Use simple, age-appropriate language
- Celebrate effort and progress, not just correct answers
- Ask guiding questions using the Socratic method
- Never give answers directly - help children discover them

Guidelines:
- Keep responses short (1-2 sentences) for natural conversation
- Use encouraging phrases like "Great thinking!" or "You're on the right track!"
- If a child is struggling, break down the problem into smaller steps
- Make learning fun with relatable examples and gentle humor
- Always prioritize the child's emotional wellbeing

Remember: You're speaking through smart glasses, so be conversational and natural."""


def create_edulens_voice_service(
    on_assistant_speaking: Optional[Callable[[str, bytes], Awaitable[None]]] = None,
    on_user_transcript: Optional[Callable[[str], Awaitable[None]]] = None,
    child_profile: Optional[Dict[str, Any]] = None,
    context: Optional[str] = None,
) -> RealtimeVoiceConversation:
    """
    Create an EduLens voice conversation service with dynamic child-adaptive prompts.

    Args:
        on_assistant_speaking: Callback when assistant speaks
        on_user_transcript: Callback when user speech is transcribed
        child_profile: Optional child profile dict for personalization
            Expected keys: name, age, grade, language, interests, learning_style, special_needs
        context: Optional context string (e.g., current subject being studied)

    Returns:
        Configured RealtimeVoiceConversation instance with personalized prompts
    """
    # Generate dynamic system prompt based on child profile
    if child_profile:
        try:
            system_prompt = build_voice_system_prompt(
                child_profile=ChildProfile.from_dict(child_profile),
                context=context,
            )
            logger.info(
                f"Created personalized voice prompt for {child_profile.get('name', 'child')}, age {child_profile.get('age', 'unknown')}"
            )
        except Exception as e:
            logger.warning(f"Failed to build personalized prompt: {e}, using default")
            system_prompt = get_default_edulens_prompt()
    else:
        # Use the default prompt when no profile is provided
        system_prompt = get_default_edulens_prompt()

    return RealtimeVoiceConversation(
        system_prompt=system_prompt,
        voice="nova",  # Warm and friendly
        on_assistant_speaking=on_assistant_speaking,
        on_user_transcript=on_user_transcript,
    )


# Exports
__all__ = [
    "OpenAIRealtimeService",
    "RealtimeConfig",
    "RealtimeVoiceConversation",
    "ConnectionState",
    "AudioChunk",
    "TranscriptEvent",
    "ResponseEvent",
    "create_edulens_voice_service",
    "EDULENS_SYSTEM_PROMPT",
    "ChildProfile",  # Re-exported for convenience
]
