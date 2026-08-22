"""
Session Broadcaster for EduLens Live Parent Monitoring

Manages multi-client streaming - forwards glasses camera frames and
observation events to connected parent apps, and routes parent messages
back to the glasses.
"""

import asyncio
import io
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

try:
    from PIL import Image
except ImportError:
    Image = None

from .websocket_handler import (
    FrameMessage,
    GlassesWebSocketHandler,
    MessageType,
    ObservationEvent,
)

logger = logging.getLogger(__name__)


class StreamQuality(Enum):
    """Stream quality presets."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class QualitySettings:
    """Quality settings for a stream level."""

    fps: int
    jpeg_quality: int
    max_width: int


class AdaptiveQualityManager:
    """
    Manages adaptive streaming quality based on network conditions.

    Auto-adjusts frame rate and quality based on:
    - Network bandwidth estimates
    - Frame delivery latency
    - Client connection stability
    """

    # Quality presets
    PRESETS = {
        StreamQuality.LOW: QualitySettings(fps=1, jpeg_quality=40, max_width=320),
        StreamQuality.MEDIUM: QualitySettings(fps=2, jpeg_quality=60, max_width=480),
        StreamQuality.HIGH: QualitySettings(fps=5, jpeg_quality=85, max_width=640),
    }

    # Bandwidth thresholds (in Kbps)
    BANDWIDTH_THRESHOLDS = {
        StreamQuality.HIGH: 1000,  # >= 1 Mbps
        StreamQuality.MEDIUM: 300,  # >= 300 Kbps
        StreamQuality.LOW: 0,  # < 300 Kbps
    }

    def __init__(self):
        self.current_quality = StreamQuality.MEDIUM
        self.bandwidth_samples: List[float] = []
        self.latency_samples: List[float] = []
        self.last_adjustment = time.time()
        self.min_adjustment_interval = 5.0  # Minimum seconds between adjustments

    def record_bandwidth(self, bandwidth_kbps: float) -> None:
        """Record a bandwidth measurement."""
        self.bandwidth_samples.append(bandwidth_kbps)
        # Keep last 10 samples
        if len(self.bandwidth_samples) > 10:
            self.bandwidth_samples.pop(0)

    def record_latency(self, latency_ms: float) -> None:
        """Record a latency measurement."""
        self.latency_samples.append(latency_ms)
        if len(self.latency_samples) > 10:
            self.latency_samples.pop(0)

    def get_quality_for_bandwidth(self, bandwidth_kbps: float) -> StreamQuality:
        """Determine quality level for given bandwidth."""
        for quality in [StreamQuality.HIGH, StreamQuality.MEDIUM, StreamQuality.LOW]:
            if bandwidth_kbps >= self.BANDWIDTH_THRESHOLDS[quality]:
                return quality
        return StreamQuality.LOW

    def adjust_quality(self) -> Optional[StreamQuality]:
        """
        Adjust quality based on recent measurements.

        Returns new quality level if changed, None otherwise.
        """
        if time.time() - self.last_adjustment < self.min_adjustment_interval:
            return None

        if not self.bandwidth_samples:
            return None

        avg_bandwidth = sum(self.bandwidth_samples) / len(self.bandwidth_samples)
        new_quality = self.get_quality_for_bandwidth(avg_bandwidth)

        if new_quality != self.current_quality:
            self.current_quality = new_quality
            self.last_adjustment = time.time()
            logger.info(
                f"Quality adjusted to {new_quality.value} (bandwidth: {avg_bandwidth:.0f} Kbps)"
            )
            return new_quality

        return None

    def get_settings(self) -> QualitySettings:
        """Get current quality settings."""
        return self.PRESETS[self.current_quality]

    def should_send_frame(self, frame_count: int) -> bool:
        """Determine if this frame should be sent based on FPS target."""
        settings = self.get_settings()
        # Assuming source is 5 FPS, skip frames to match target
        source_fps = 5
        skip_rate = source_fps / settings.fps
        return frame_count % int(skip_rate) == 0


@dataclass
class ParentMessage:
    """Message from parent to child via glasses."""

    message_type: str  # "voice" | "text" | "encouragement" | "control"
    content: str  # Text or base64 audio
    language: str = "en"
    timestamp: float = field(default_factory=time.time)
    sender_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ParentMessage":
        """Create from dictionary."""
        return cls(
            message_type=data.get("type", "text"),
            content=data.get("content", ""),
            language=data.get("language", "en"),
            timestamp=data.get("timestamp", time.time()),
            sender_id=data.get("sender_id"),
        )


class ParentWebSocketHandler:
    """
    Handles WebSocket connection with parent mobile app.

    Receives: JPEG frames (quality-adjusted) + observation events
    Sends: Voice messages, text guidance, control commands
    """

    def __init__(
        self,
        parent_id: str,
        session_id: str,
        notify_child: bool = True,
    ):
        """
        Initialize parent handler.

        Args:
            parent_id: Parent user ID
            session_id: Observation session ID
            notify_child: Whether to notify child when parent connects
        """
        self.parent_id = parent_id
        self.session_id = session_id
        self.notify_child = notify_child

        self.websocket = None
        self.quality_manager = AdaptiveQualityManager()
        self.connected_at: Optional[float] = None
        self.frame_count = 0
        self.event_count = 0
        self.message_count = 0
        self.last_frame_at: Optional[float] = None

        self._receive_task: Optional[asyncio.Task] = None
        self._connected = False

        # Callbacks
        self.on_message: Optional[Callable[[ParentMessage], Awaitable[None]]] = None
        self.on_disconnect: Optional[Callable[[], Awaitable[None]]] = None

    async def connect(self, websocket) -> None:
        """
        Accept and initialize WebSocket connection.

        Args:
            websocket: FastAPI WebSocket instance
        """
        from fastapi import WebSocket

        self.websocket = websocket

        try:
            await websocket.accept()
            self._connected = True
            self.connected_at = time.time()

            logger.info(f"Parent {self.parent_id} connected to session {self.session_id}")

            # Send welcome message
            await self.send_event(
                {
                    "type": "connected",
                    "session_id": self.session_id,
                    "quality": self.quality_manager.current_quality.value,
                    "notify_child": self.notify_child,
                }
            )

            # Start receiving messages
            self._receive_task = asyncio.create_task(self._receive_loop())

        except Exception as e:
            self._connected = False
            logger.error(f"Parent connection failed: {e}")
            raise

    async def _receive_loop(self) -> None:
        """Receive and process messages from parent app."""
        from fastapi import WebSocketDisconnect

        try:
            while self._connected:
                try:
                    message = await self.websocket.receive()

                    if "text" in message:
                        # JSON message
                        import json

                        data = json.loads(message["text"])
                        await self._handle_message(data)

                    elif "bytes" in message:
                        # Binary message (e.g., voice audio)
                        await self._handle_binary(message["bytes"])

                except WebSocketDisconnect:
                    logger.info(f"Parent {self.parent_id} disconnected")
                    break
                except RuntimeError as e:
                    # WebSocket closed - "Cannot call receive once disconnect received"
                    if "disconnect" in str(e).lower():
                        logger.info(f"Parent {self.parent_id} WebSocket closed")
                        break
                    logger.error(f"Error receiving parent message: {e}")
                    break
                except Exception as e:
                    error_msg = str(e).lower()
                    if "disconnect" in error_msg or "closed" in error_msg:
                        logger.info(f"Parent {self.parent_id} connection closed")
                        break
                    logger.error(f"Error receiving parent message: {e}")
                    break

        finally:
            self._connected = False
            if self.on_disconnect:
                await self.on_disconnect()

    async def _handle_message(self, data: Dict[str, Any]) -> None:
        """Handle JSON message from parent."""
        msg_type = data.get("type")

        if msg_type in ("voice_message", "text_message", "encouragement", "control"):
            parent_msg = ParentMessage.from_dict(data)
            parent_msg.sender_id = self.parent_id
            self.message_count += 1

            if self.on_message:
                await self.on_message(parent_msg)

        elif msg_type == "quality":
            # Quality setting change
            quality_str = data.get("quality", "medium")
            try:
                self.quality_manager.current_quality = StreamQuality(quality_str)
                logger.info(f"Parent quality set to {quality_str}")
            except ValueError:
                pass

        elif msg_type == "ping":
            # Latency measurement
            await self.send_event({"type": "pong", "timestamp": time.time()})

        elif msg_type == "bandwidth":
            # Bandwidth report from client
            bandwidth = data.get("bandwidth_kbps", 500)
            self.quality_manager.record_bandwidth(bandwidth)
            self.quality_manager.adjust_quality()

    async def _handle_binary(self, data: bytes) -> None:
        """Handle binary message (voice audio)."""
        # Treat as voice message
        parent_msg = ParentMessage(
            message_type="voice_message",
            content="",  # Binary audio, not base64
            sender_id=self.parent_id,
        )
        parent_msg._audio_data = data  # Attach raw audio
        self.message_count += 1

        if self.on_message:
            await self.on_message(parent_msg)

    async def send_frame(self, jpeg_data: bytes) -> None:
        """
        Send video frame to parent app.

        Args:
            jpeg_data: JPEG compressed frame
        """
        if not self._connected or not self.websocket:
            return

        self.frame_count += 1

        # Check if we should send this frame based on quality settings
        if not self.quality_manager.should_send_frame(self.frame_count):
            return

        try:
            # Resize frame based on quality settings
            processed_frame = self._process_frame(jpeg_data)

            # Send as binary
            await self.websocket.send_bytes(processed_frame)
            self.last_frame_at = time.time()

        except Exception as e:
            logger.warning(f"Failed to send frame to parent: {e}")

    def _process_frame(self, jpeg_data: bytes) -> bytes:
        """Process frame based on quality settings."""
        if Image is None:
            return jpeg_data

        settings = self.quality_manager.get_settings()

        try:
            # Decode JPEG
            img = Image.open(io.BytesIO(jpeg_data))

            # Resize if needed
            if img.width > settings.max_width:
                ratio = settings.max_width / img.width
                new_size = (settings.max_width, int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # Re-encode with quality setting
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=settings.jpeg_quality)
            return output.getvalue()

        except Exception as e:
            logger.warning(f"Frame processing failed: {e}")
            return jpeg_data

    async def send_event(self, event: Dict[str, Any]) -> None:
        """
        Send event to parent app.

        Args:
            event: Event dictionary
        """
        if not self._connected or not self.websocket:
            return

        try:
            import json

            await self.websocket.send_text(json.dumps(event))
            self.event_count += 1

        except Exception as e:
            logger.warning(f"Failed to send event to parent: {e}")

    async def disconnect(self) -> None:
        """Close connection."""
        self._connected = False

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

        logger.info(f"Parent {self.parent_id} disconnected from session {self.session_id}")

    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "parent_id": self.parent_id,
            "session_id": self.session_id,
            "connected": self._connected,
            "connected_at": self.connected_at,
            "frame_count": self.frame_count,
            "event_count": self.event_count,
            "message_count": self.message_count,
            "quality": self.quality_manager.current_quality.value,
            "uptime_seconds": (
                time.time() - (self.connected_at or time.time()) if self._connected else 0
            ),
        }


class SessionBroadcaster:
    """
    Manages multi-client streaming for observation sessions.

    Coordinates:
    - Glasses WebSocket handler (frame source)
    - Multiple parent WebSocket handlers (frame sinks)
    - ContinuousObserver for AI processing
    - Parent-to-child message routing
    """

    def __init__(
        self,
        session_id: str,
        child_id: str,
        child_language: str = "en",
    ):
        """
        Initialize broadcaster.

        Args:
            session_id: Unique session identifier
            child_id: Child profile ID
            child_language: Child's preferred language for TTS
        """
        self.session_id = session_id
        self.child_id = child_id
        self.child_language = child_language

        self.glasses_handler: Optional[GlassesWebSocketHandler] = None
        self.parent_handlers: List[ParentWebSocketHandler] = []
        self.observer = None  # ContinuousObserver instance

        # TTS engine for text-to-speech
        self.tts_engine = None

        # Stats
        self.created_at = time.time()
        self.total_frames = 0
        self.total_events = 0

        # Callbacks
        self.on_parent_message: Optional[Callable[[ParentMessage], Awaitable[None]]] = None

    async def set_glasses_handler(self, handler: GlassesWebSocketHandler) -> None:
        """
        Set the glasses WebSocket handler.

        Args:
            handler: Glasses handler instance
        """
        self.glasses_handler = handler

        # Set up frame forwarding
        original_on_frame = handler.on_frame

        async def frame_handler(frame: FrameMessage):
            # Forward to observer
            if original_on_frame:
                await original_on_frame(frame)

            # Broadcast to parents
            await self.broadcast_frame(frame.data)
            self.total_frames += 1

        handler.on_frame = frame_handler

        logger.info(f"Glasses handler set for session {self.session_id}")

    def add_parent(self, handler: ParentWebSocketHandler) -> None:
        """
        Add a parent handler to receive broadcasts.

        Args:
            handler: Parent handler instance
        """
        # Set up message callback
        handler.on_message = self._handle_parent_message
        handler.on_disconnect = lambda: self._on_parent_disconnect(handler)

        self.parent_handlers.append(handler)
        logger.info(f"Parent {handler.parent_id} added to session {self.session_id}")

        # Notify glasses if parent wants notification
        if handler.notify_child and self.glasses_handler:
            asyncio.create_task(self._notify_child_of_parent(handler))

    async def _notify_child_of_parent(self, parent: ParentWebSocketHandler) -> None:
        """Send notification to child that parent is watching."""
        try:
            # Send event to glasses
            event = ObservationEvent(
                event_type="parent_connected",
                payload={
                    "message": "Mom or Dad is here to help!",
                    "parent_id": parent.parent_id,
                },
            )
            await self.glasses_handler.send_event(event)

            # Optionally speak notification
            audio = await self._synthesize_notification("Mom or Dad is here to help you!")
            if audio:
                await self.glasses_handler.send_audio(audio)

        except Exception as e:
            logger.error(f"Failed to notify child: {e}")

    async def _synthesize_notification(self, text: str) -> Optional[bytes]:
        """Synthesize TTS audio for notification."""
        if self.tts_engine is None:
            try:
                from src.audio.tts_engine import TTSEngine

                self.tts_engine = TTSEngine()
                self.tts_engine.set_language(self.child_language)
            except Exception as e:
                logger.warning(f"TTS engine not available: {e}")
                return None

        try:
            return await asyncio.to_thread(self.tts_engine.synthesize, text)
        except Exception as e:
            logger.warning(f"TTS synthesis failed: {e}")
            return None

    def remove_parent(self, handler: ParentWebSocketHandler) -> None:
        """
        Remove a parent handler.

        Args:
            handler: Parent handler to remove
        """
        if handler in self.parent_handlers:
            self.parent_handlers.remove(handler)
            logger.info(f"Parent {handler.parent_id} removed from session {self.session_id}")

    async def _on_parent_disconnect(self, handler: ParentWebSocketHandler) -> None:
        """Handle parent disconnection."""
        self.remove_parent(handler)

        # Notify glasses
        if self.glasses_handler and handler.notify_child:
            await self.glasses_handler.send_event(
                ObservationEvent(
                    event_type="parent_disconnected", payload={"parent_id": handler.parent_id}
                )
            )

    async def broadcast_frame(self, jpeg_data: bytes) -> None:
        """
        Broadcast frame to all connected parents.

        Args:
            jpeg_data: JPEG compressed frame
        """
        if not self.parent_handlers:
            return

        # Send to all parents concurrently
        tasks = [parent.send_frame(jpeg_data) for parent in self.parent_handlers]

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_event(self, event: ObservationEvent) -> None:
        """
        Broadcast observation event to all parents.

        Args:
            event: Observation event
        """
        self.total_events += 1

        if not self.parent_handlers:
            return

        event_dict = {
            "type": event.event_type,
            "payload": event.payload,
            "timestamp": event.timestamp,
        }

        tasks = [parent.send_event(event_dict) for parent in self.parent_handlers]

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _handle_parent_message(self, message: ParentMessage) -> None:
        """
        Handle message from parent to route to glasses.

        Args:
            message: Parent message
        """
        if not self.glasses_handler:
            logger.warning("No glasses connected to receive parent message")
            return

        logger.info(f"Parent message: {message.message_type} from {message.sender_id}")

        if message.message_type == "text_message":
            # Convert text to TTS and send to glasses
            audio = await self._synthesize_notification(message.content)
            if audio:
                await self.glasses_handler.send_event(
                    ObservationEvent(
                        event_type="parent_message",
                        payload={
                            "sender": "parent",
                            "text": message.content,
                            "has_audio": True,
                        },
                    )
                )
                await self.glasses_handler.send_audio(audio)
            else:
                # Send text-only event
                await self.glasses_handler.send_event(
                    ObservationEvent(
                        event_type="parent_message",
                        payload={
                            "sender": "parent",
                            "text": message.content,
                            "has_audio": False,
                        },
                    )
                )

        elif message.message_type == "voice_message":
            # Forward voice audio directly
            audio_data = getattr(message, "_audio_data", None)
            if audio_data:
                await self.glasses_handler.send_event(
                    ObservationEvent(
                        event_type="parent_message",
                        payload={
                            "sender": "parent",
                            "has_audio": True,
                        },
                    )
                )
                await self.glasses_handler.send_audio(audio_data)

        elif message.message_type == "encouragement":
            # Play pre-defined encouragement
            encouragements = {
                "great_job": "Great job! Keep it up!",
                "keep_going": "You're doing amazing! Keep going!",
                "proud": "I'm so proud of you!",
                "almost_there": "Almost there! You've got this!",
            }
            text = encouragements.get(message.content, message.content)
            audio = await self._synthesize_notification(text)

            await self.glasses_handler.send_event(
                ObservationEvent(
                    event_type="encouragement",
                    payload={
                        "sender": "parent",
                        "type": message.content,
                        "text": text,
                        "has_audio": audio is not None,
                    },
                )
            )

            if audio:
                await self.glasses_handler.send_audio(audio)

        elif message.message_type == "control":
            # Handle control messages
            if message.content == "stop_monitoring":
                # Parent wants to stop watching
                pass

        # Notify callback
        if self.on_parent_message:
            await self.on_parent_message(message)

    async def send_to_glasses(self, event: ObservationEvent) -> None:
        """
        Send event directly to glasses.

        Args:
            event: Event to send
        """
        if self.glasses_handler:
            await self.glasses_handler.send_event(event)

    async def shutdown(self) -> None:
        """Shut down the broadcaster and all connections."""
        # Disconnect all parents
        for parent in list(self.parent_handlers):
            await parent.disconnect()

        # Disconnect glasses
        if self.glasses_handler:
            await self.glasses_handler.disconnect()

        logger.info(f"Session {self.session_id} shut down")

    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        return {
            "session_id": self.session_id,
            "child_id": self.child_id,
            "created_at": self.created_at,
            "uptime_seconds": time.time() - self.created_at,
            "total_frames": self.total_frames,
            "total_events": self.total_events,
            "glasses_connected": self.glasses_handler is not None,
            "parent_count": len(self.parent_handlers),
            "parents": [p.get_stats() for p in self.parent_handlers],
        }


# Export classes
__all__ = [
    "SessionBroadcaster",
    "ParentWebSocketHandler",
    "ParentMessage",
    "AdaptiveQualityManager",
    "StreamQuality",
    "QualitySettings",
]
