"""
WebSocket Handler for EduLens Glasses Communication

Handles bidirectional WebSocket communication between smart glasses
and the backend for continuous observation mode.

Protocol:
- Glasses → Backend: Binary JPEG frames
- Backend → Glasses: JSON events + binary audio chunks
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Callable, Awaitable
import io

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """WebSocket message types."""
    FRAME = 0x01           # Binary JPEG frame from glasses
    EVENT = 0x02           # JSON event from backend
    AUDIO = 0x03           # Binary audio chunk from backend
    CONTROL = 0x04         # Control message (start/stop/config)
    HEARTBEAT = 0x05       # Keep-alive heartbeat


@dataclass
class FrameMessage:
    """Incoming frame from glasses."""
    frame_id: int
    timestamp: float
    data: bytes  # JPEG compressed frame
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_binary(cls, data: bytes) -> 'FrameMessage':
        """Parse binary frame message."""
        # Protocol: [1 byte type][4 bytes frame_id][8 bytes timestamp][N bytes JPEG]
        if len(data) < 13:
            raise ValueError(f"Frame message too short: {len(data)} bytes")

        msg_type = data[0]
        if msg_type != MessageType.FRAME.value:
            raise ValueError(f"Invalid message type: {msg_type}")

        frame_id = int.from_bytes(data[1:5], 'big')
        timestamp = int.from_bytes(data[5:13], 'big') / 1000.0  # ms to seconds
        jpeg_data = data[13:]

        return cls(frame_id=frame_id, timestamp=timestamp, data=jpeg_data)


@dataclass
class ObservationEvent:
    """Outgoing event to glasses."""
    event_type: str  # "struggle_detected", "scene_change", "intervention"
    payload: Dict[str, Any]
    audio_url: Optional[str] = None  # URL or base64 audio
    timestamp: float = field(default_factory=time.time)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps({
            "event_type": self.event_type,
            "payload": self.payload,
            "audio_url": self.audio_url,
            "timestamp": self.timestamp,
        })

    def to_binary(self) -> bytes:
        """Convert to binary message."""
        json_bytes = self.to_json().encode('utf-8')
        # Protocol: [1 byte type][N bytes JSON]
        return bytes([MessageType.EVENT.value]) + json_bytes


class ConnectionState(Enum):
    """WebSocket connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    OBSERVING = "observing"
    ERROR = "error"


class GlassesWebSocketHandler:
    """
    Manages WebSocket connection with smart glasses.

    Handles:
    - Connection lifecycle
    - Frame reception
    - Event and audio transmission
    - Heartbeat management
    """

    def __init__(
        self,
        session_id: str,
        child_id: Optional[str] = None,
        on_frame: Optional[Callable[[FrameMessage], Awaitable[None]]] = None,
    ):
        """
        Initialize handler.

        Args:
            session_id: Unique observation session ID
            child_id: Optional child profile ID
            on_frame: Callback for received frames
        """
        self.session_id = session_id
        self.child_id = child_id
        self.on_frame = on_frame

        self.websocket: Optional[WebSocket] = None
        self.state = ConnectionState.DISCONNECTED
        self.connected_at: Optional[float] = None
        self.last_frame_at: Optional[float] = None
        self.frame_count = 0
        self.event_count = 0

        self._heartbeat_task: Optional[asyncio.Task] = None
        self._receive_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: WebSocket) -> None:
        """
        Accept and initialize WebSocket connection.

        Args:
            websocket: FastAPI WebSocket instance
        """
        self.websocket = websocket
        self.state = ConnectionState.CONNECTING

        try:
            await websocket.accept()
            self.state = ConnectionState.CONNECTED
            self.connected_at = time.time()

            logger.info(f"WebSocket connected for session {self.session_id}")

            # Send welcome message
            await self.send_event(ObservationEvent(
                event_type="connected",
                payload={
                    "session_id": self.session_id,
                    "child_id": self.child_id,
                    "message": "Observation session started"
                }
            ))

        except Exception as e:
            self.state = ConnectionState.ERROR
            logger.error(f"WebSocket connection failed: {e}")
            raise

    async def start_observation(self) -> None:
        """Start observation mode with frame reception."""
        if self.state != ConnectionState.CONNECTED:
            raise RuntimeError(f"Cannot start observation in state: {self.state}")

        self.state = ConnectionState.OBSERVING

        # Start heartbeat
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        # Start receiving frames
        self._receive_task = asyncio.create_task(self._receive_loop())

        logger.info(f"Observation started for session {self.session_id}")

    async def _receive_loop(self) -> None:
        """Main loop for receiving frames from glasses."""
        try:
            while self.state == ConnectionState.OBSERVING:
                try:
                    # Receive binary or text message
                    message = await self.websocket.receive()

                    if "bytes" in message:
                        # Binary frame data
                        data = message["bytes"]
                        if data and len(data) > 0:
                            await self._handle_binary_message(data)

                    elif "text" in message:
                        # JSON control message
                        text = message["text"]
                        await self._handle_text_message(text)

                except WebSocketDisconnect:
                    logger.info(f"WebSocket disconnected for session {self.session_id}")
                    break

                except RuntimeError as e:
                    # WebSocket closed - "Cannot call receive once disconnect received"
                    if "disconnect" in str(e).lower():
                        logger.info(f"WebSocket closed for session {self.session_id}")
                        break
                    logger.error(f"Error receiving message: {e}")
                    break

                except Exception as e:
                    error_msg = str(e).lower()
                    if "disconnect" in error_msg or "closed" in error_msg:
                        logger.info(f"WebSocket connection closed for session {self.session_id}")
                        break
                    logger.error(f"Error receiving message: {e}")
                    break

        finally:
            self.state = ConnectionState.DISCONNECTED

    async def _handle_binary_message(self, data: bytes) -> None:
        """Handle binary message (frame or audio)."""
        if len(data) < 1:
            return

        msg_type = data[0]

        if msg_type == MessageType.FRAME.value:
            try:
                frame = FrameMessage.from_binary(data)
                self.frame_count += 1
                self.last_frame_at = time.time()

                # Call frame handler
                if self.on_frame:
                    await self.on_frame(frame)

            except ValueError as e:
                logger.warning(f"Invalid frame: {e}")

        elif msg_type == MessageType.HEARTBEAT.value:
            # Respond to heartbeat
            await self.websocket.send_bytes(bytes([MessageType.HEARTBEAT.value]))

    async def _handle_text_message(self, text: str) -> None:
        """Handle text (JSON) control message."""
        try:
            msg = json.loads(text)
            msg_type = msg.get("type")

            if msg_type == "stop":
                await self.stop_observation()

            elif msg_type == "config":
                # Handle configuration updates
                logger.info(f"Config update received: {msg.get('config')}")

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON message: {text[:100]}")

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats."""
        while self.state == ConnectionState.OBSERVING:
            try:
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
                if self.websocket:
                    await self.websocket.send_bytes(bytes([MessageType.HEARTBEAT.value]))
            except Exception as e:
                logger.warning(f"Heartbeat failed: {e}")
                break

    async def send_event(self, event: ObservationEvent) -> None:
        """
        Send event to glasses.

        Args:
            event: Event to send
        """
        if not self.websocket:
            raise RuntimeError("Not connected")

        try:
            # Send as JSON text
            await self.websocket.send_text(event.to_json())
            self.event_count += 1
            logger.debug(f"Sent event: {event.event_type}")

        except Exception as e:
            logger.error(f"Failed to send event: {e}")
            raise

    async def send_audio(self, audio_data: bytes) -> None:
        """
        Send audio chunk to glasses.

        Args:
            audio_data: PCM audio data
        """
        if not self.websocket:
            raise RuntimeError("Not connected")

        try:
            # Protocol: [1 byte type][4 bytes length][N bytes audio]
            length = len(audio_data)
            header = bytes([MessageType.AUDIO.value]) + length.to_bytes(4, 'big')
            await self.websocket.send_bytes(header + audio_data)

        except Exception as e:
            logger.error(f"Failed to send audio: {e}")
            raise

    async def send_intervention(
        self,
        message: str,
        audio_data: Optional[bytes] = None,
        intervention_type: str = "gentle_prompt"
    ) -> None:
        """
        Send proactive intervention to glasses.

        Args:
            message: Text message for the intervention
            audio_data: Optional pre-generated TTS audio
            intervention_type: Type of intervention
        """
        # Send event first
        await self.send_event(ObservationEvent(
            event_type="intervention",
            payload={
                "intervention_type": intervention_type,
                "message": message,
                "has_audio": audio_data is not None
            }
        ))

        # Send audio if provided
        if audio_data:
            await self.send_audio(audio_data)

    async def stop_observation(self) -> None:
        """Stop observation and clean up."""
        logger.info(f"Stopping observation for session {self.session_id}")

        self.state = ConnectionState.CONNECTED

        # Cancel background tasks
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        # Send stop confirmation (only if websocket is still open)
        if self.websocket and self.websocket.client_state.name == "CONNECTED":
            try:
                await self.send_event(ObservationEvent(
                    event_type="observation_stopped",
                    payload={
                        "session_id": self.session_id,
                        "total_frames": self.frame_count,
                        "total_events": self.event_count,
                        "duration_seconds": time.time() - (self.connected_at or time.time())
                    }
                ))
            except Exception as e:
                logger.debug(f"Could not send stop event (connection closed): {e}")

    async def disconnect(self) -> None:
        """Close WebSocket connection."""
        await self.stop_observation()

        if self.websocket:
            try:
                await self.websocket.close()
            except Exception:
                pass

        self.state = ConnectionState.DISCONNECTED
        logger.info(f"WebSocket disconnected for session {self.session_id}")

    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "session_id": self.session_id,
            "child_id": self.child_id,
            "state": self.state.value,
            "connected_at": self.connected_at,
            "frame_count": self.frame_count,
            "event_count": self.event_count,
            "last_frame_at": self.last_frame_at,
            "uptime_seconds": time.time() - (self.connected_at or time.time()),
        }
