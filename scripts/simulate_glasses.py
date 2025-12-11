#!/usr/bin/env python3
"""
EduLens Smart Glasses Simulator

Simulates the full smart glasses experience using your computer's:
- Webcam (as the glasses camera)
- Microphone (as the glasses mic)
- Speakers (as the glasses audio output)

Features:
- Wake word detection ("Hey EduLens")
- Voice commands
- Homework image capture
- AI tutoring responses
- Text-to-speech output
- **Autonomous Observation Mode** (NEW)
  - Continuous frame streaming via WebSocket
  - Automatic struggle detection
  - Proactive intervention playback

Usage:
    python scripts/simulate_glasses.py
    python scripts/simulate_glasses.py --autonomous   # Start in observation mode
    python scripts/simulate_glasses.py --server http://localhost:8000  # Custom server

Controls:
    - Say "Hey EduLens" to activate
    - Press 'c' to capture homework image
    - Press 'q' to quit
    - Press 'space' to manually trigger voice input
    - Press 'm' to toggle autonomous observation mode (NEW)
    - Press 'o' to view observation stats (NEW)

Requirements:
    pip install opencv-python sounddevice numpy pyttsx3 websockets
"""

import argparse
import asyncio
import json
import os
import struct
import sys
import threading
import time
import queue
import uuid
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

# Global state
class GlassesState:
    def __init__(self):
        self.is_listening = False
        self.is_processing = False
        self.last_image = None
        self.extracted_text = ""
        self.conversation_context = {
            'age': 8,
            'grade': '3',
            'subject': 'general'
        }
        self.audio_queue = queue.Queue()
        self.running = True

        # Autonomous observation state
        self.autonomous_mode = False
        self.observation_session_id: Optional[str] = None
        self.websocket = None
        self.frame_count = 0
        self.last_intervention: Optional[str] = None
        self.intervention_count = 0
        self.observation_stats = {
            'frames_sent': 0,
            'interventions_received': 0,
            'session_duration': 0,
        }


state = GlassesState()


# Autonomous Observation Mode Classes
class FrameProtocol:
    """Protocol for sending frames to backend."""
    FRAME_TYPE = 0x01
    HEARTBEAT_TYPE = 0x05

    @staticmethod
    def encode_frame(frame_id: int, jpeg_data: bytes) -> bytes:
        """Encode frame for WebSocket transmission.

        Format: [1 byte type][4 bytes frame_id][8 bytes timestamp_ms][N bytes JPEG]
        """
        timestamp_ms = int(time.time() * 1000)
        header = struct.pack('>BIQ', FrameProtocol.FRAME_TYPE, frame_id, timestamp_ms)
        return header + jpeg_data

    @staticmethod
    def encode_heartbeat() -> bytes:
        """Encode heartbeat message."""
        return bytes([FrameProtocol.HEARTBEAT_TYPE])


class ObservationClient:
    """WebSocket client for autonomous observation mode."""

    def __init__(self, server_url: str, session_id: str, child_id: Optional[str] = None):
        self.server_url = server_url.replace('http://', 'ws://').replace('https://', 'wss://')
        self.session_id = session_id
        self.child_id = child_id
        self.websocket = None
        self.connected = False
        self.frame_id = 0

    async def connect(self):
        """Connect to observation WebSocket endpoint."""
        try:
            import websockets

            url = f"{self.server_url}/ws/observe/{self.session_id}"
            if self.child_id:
                url += f"?child_id={self.child_id}"

            print(f"🔌 Connecting to {url}...")
            self.websocket = await websockets.connect(url)
            self.connected = True
            print("✅ Connected to observation server!")

            # Start receive task
            asyncio.create_task(self._receive_loop())

            return True

        except ImportError:
            print("❌ websockets package not installed. Run: pip install websockets")
            return False
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False

    async def _receive_loop(self):
        """Receive events from server."""
        try:
            while self.connected and self.websocket:
                try:
                    message = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=1.0
                    )

                    # Handle text (JSON) or binary (audio) messages
                    if isinstance(message, str):
                        event = json.loads(message)
                        await self._handle_event(event)
                    elif isinstance(message, bytes):
                        await self._handle_audio(message)

                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    if self.connected:
                        print(f"⚠️ Receive error: {e}")
                    break

        except Exception as e:
            print(f"❌ Receive loop error: {e}")
        finally:
            self.connected = False

    async def _handle_event(self, event: dict):
        """Handle event from server."""
        event_type = event.get('event_type', '')

        if event_type == 'connected':
            print(f"📡 Observation session started: {event.get('payload', {}).get('session_id')}")

        elif event_type == 'intervention':
            payload = event.get('payload', {})
            message = payload.get('message', '')
            intervention_type = payload.get('intervention_type', '')

            print(f"\n🎯 INTERVENTION ({intervention_type}): {message}")
            state.last_intervention = message
            state.intervention_count += 1
            state.observation_stats['interventions_received'] += 1

            # Queue for TTS playback
            state.audio_queue.put(('intervention', message))

        elif event_type == 'scene_change':
            payload = event.get('payload', {})
            print(f"📍 Scene: {payload.get('previous_scene')} → {payload.get('new_scene')}")

        elif event_type == 'observation_stopped':
            print(f"🛑 Observation stopped: {event.get('payload', {})}")

        elif event_type == 'parent_connected':
            payload = event.get('payload', {})
            message = payload.get('message', 'A parent is now watching')
            print(f"\n👨‍👩‍👧 PARENT CONNECTED: {message}")
            # Announce via TTS if enabled
            if not state.no_audio:
                state.audio_queue.put(('parent', message))

        elif event_type == 'parent_message':
            payload = event.get('payload', {})
            text = payload.get('text', '')
            print(f"\n💬 PARENT MESSAGE: {text}")
            # Speak the parent message via TTS
            if not state.no_audio and text:
                state.audio_queue.put(('parent', text))

        elif event_type == 'encouragement':
            payload = event.get('payload', {})
            text = payload.get('text', '')
            enc_type = payload.get('type', '')
            print(f"\n👍 PARENT ENCOURAGEMENT ({enc_type}): {text}")
            # Speak the encouragement via TTS
            if not state.no_audio and text:
                state.audio_queue.put(('encouragement', text))

        elif event_type == 'parent_disconnected':
            print(f"\n👋 Parent disconnected")

    async def _handle_audio(self, data: bytes):
        """Handle binary audio from server."""
        if len(data) < 1:
            return

        msg_type = data[0]
        if msg_type == 0x03:  # AUDIO type
            # Extract audio data (skip type byte and 4-byte length)
            audio_data = data[5:] if len(data) > 5 else data[1:]
            print(f"🔊 Received audio: {len(audio_data)} bytes")
            # Would play audio here

    async def send_frame(self, jpeg_data: bytes):
        """Send a frame to the server."""
        if not self.connected or not self.websocket:
            return False

        try:
            self.frame_id += 1
            frame_packet = FrameProtocol.encode_frame(self.frame_id, jpeg_data)
            await self.websocket.send(frame_packet)
            state.observation_stats['frames_sent'] += 1
            return True

        except Exception as e:
            # Only print error once, then mark as disconnected to stop flood
            if self.connected:
                print(f"⚠️ Send frame error: {e}")
                self.connected = False  # Stop further send attempts
            return False

    async def disconnect(self):
        """Disconnect from server."""
        self.connected = False
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
        print("🔌 Disconnected from observation server")


# Global observation client
observation_client: Optional[ObservationClient] = None


def init_tts():
    """Initialize text-to-speech engine - uses macOS 'say' for natural voice."""
    import platform

    # Check for OpenAI TTS first (best quality)
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        print("🔊 Using OpenAI TTS (human-like voice)")
        return {"type": "openai", "api_key": openai_key}

    # On macOS, use built-in 'say' command with Samantha voice (good quality)
    if platform.system() == "Darwin":
        print("🔊 Using macOS Samantha voice")
        return {"type": "macos"}

    # Fallback to pyttsx3 on other platforms
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 0.9)
        print("🔊 Using pyttsx3 TTS")
        return {"type": "pyttsx3", "engine": engine}
    except Exception as e:
        print(f"⚠️ TTS not available: {e}")
        return None


def speak(text, tts_engine):
    """Speak text using TTS - with echo cancellation (pauses mic during speech)."""
    global state
    if not tts_engine:
        print(f"🔊 [TTS disabled] {text}")
        return

    # Pause listening during speech to avoid echo
    was_listening = state.is_listening
    state.is_listening = False
    print(f"🔊 Speaking: {text[:80]}...")

    import subprocess

    try:
        if tts_engine.get("type") == "openai":
            try:
                import tempfile
                from openai import OpenAI

                client = OpenAI(api_key=tts_engine["api_key"])
                response = client.audio.speech.create(
                    model="tts-1",
                    voice="nova",
                    input=text,
                    speed=1.0
                )

                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    f.write(response.content)
                    temp_path = f.name

                subprocess.run(["afplay", temp_path], capture_output=True)
                os.unlink(temp_path)

            except Exception as e:
                print(f"⚠️ OpenAI TTS failed: {e}")
                subprocess.run(["say", "-v", "Samantha", "-r", "180", text], capture_output=True)

        elif tts_engine.get("type") == "macos":
            # Use macOS say with Samantha voice (natural sounding)
            subprocess.run(["say", "-v", "Samantha", "-r", "180", text], capture_output=True)

        elif tts_engine.get("type") == "pyttsx3":
            engine = tts_engine.get("engine")
            if engine:
                engine.say(text)
                engine.runAndWait()

    finally:
        # Resume listening after speech
        state.is_listening = was_listening


def init_tutor():
    """Initialize the AI tutor engine."""
    from src.ai import create_tutor_engine

    provider = os.getenv("LLM_PROVIDER", "anthropic")
    print(f"🎓 Initializing tutor with {provider}...")

    try:
        engine = create_tutor_engine(llm_provider=provider)
        print("✅ Tutor ready!")
        return engine
    except Exception as e:
        print(f"❌ Tutor init failed: {e}")
        return None


def capture_frame(cap):
    """Capture a frame from webcam."""
    ret, frame = cap.read()
    if ret:
        return frame
    return None


def process_image_for_ocr(image):
    """Process image through OCR."""
    try:
        from src.vision.ocr_engine import OCREngine
        ocr = OCREngine()
        result = ocr.extract_text(image)
        return result.get('text', '')
    except ImportError:
        # Fallback: try pytesseract directly
        try:
            import pytesseract
            from PIL import Image
            import cv2

            # Convert to RGB
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb)
            text = pytesseract.image_to_string(pil_image)
            return text.strip()
        except Exception as e:
            print(f"⚠️ OCR failed: {e}")
            return ""
    except Exception as e:
        print(f"⚠️ OCR error: {e}")
        return ""


def listen_for_speech(duration=5):
    """Record audio and convert to text."""
    try:
        import sounddevice as sd
        import numpy as np

        print("🎤 Listening...")
        sample_rate = 16000
        audio_data = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype='float32'
        )
        sd.wait()

        # Try to transcribe with whisper
        try:
            import whisper
            model = whisper.load_model("base")

            # Save temp file
            import tempfile
            import scipy.io.wavfile as wav

            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                wav.write(f.name, sample_rate, (audio_data * 32767).astype(np.int16))
                result = model.transcribe(f.name)
                os.unlink(f.name)
                return result['text'].strip()
        except ImportError:
            print("⚠️ Whisper not available, using placeholder")
            return None

    except Exception as e:
        print(f"⚠️ Audio capture failed: {e}")
        return None


def detect_wake_word(text):
    """Check if wake word was spoken."""
    if not text:
        return False

    wake_phrases = [
        "hey edulens",
        "hey edu lens",
        "hey ed lens",
        "okay edulens",
        "hi edulens"
    ]

    text_lower = text.lower()
    return any(phrase in text_lower for phrase in wake_phrases)


def process_voice_query(tutor_engine, query, tts_engine):
    """Process a voice query and speak the response."""
    if not tutor_engine:
        speak("Sorry, the tutor is not available right now.", tts_engine)
        return

    # Add image context if available
    context = state.conversation_context.copy()
    if state.extracted_text:
        context['problem_statement'] = state.extracted_text[:500]

    try:
        print(f"🧒 Query: {query}")
        result = tutor_engine.generate_response(query, context)
        response = result['response']
        print(f"🤖 Response: {response}")
        speak(response, tts_engine)
    except Exception as e:
        print(f"❌ Error: {e}")
        speak("Sorry, I had trouble understanding. Can you ask again?", tts_engine)


def run_camera_loop(cap, window_name, server_url="http://localhost:8000", child_id=None):
    """Run the camera display loop."""
    import cv2

    print("\n📹 Camera active. Controls:")
    print("   'c' - Capture homework image")
    print("   'space' - Voice input")
    print("   'm' - Toggle autonomous observation mode")
    print("   'o' - Show observation stats")
    print("   'q' - Quit")
    print("   Say 'Hey EduLens' to activate voice\n")

    # Async event loop for observation mode
    loop = asyncio.new_event_loop()
    frame_interval = 1.0 / 5  # 5 FPS for observation
    last_frame_time = 0

    while state.running:
        frame = capture_frame(cap)
        if frame is None:
            continue

        # Add status overlay
        status = "EduLens Simulator"
        if state.autonomous_mode:
            status += " | [AUTO MODE]"
            status += f" | Frames: {state.observation_stats['frames_sent']}"
            if state.intervention_count > 0:
                status += f" | Interventions: {state.intervention_count}"
        if state.is_listening:
            status += " | Listening..."
        if state.is_processing:
            status += " | Processing..."
        if state.extracted_text and not state.autonomous_mode:
            status += " | Text captured"

        # Draw status bar (green if autonomous mode, otherwise dark gray)
        bar_color = (0, 100, 0) if state.autonomous_mode else (50, 50, 50)
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 40), bar_color, -1)
        cv2.putText(frame, status, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Show last intervention message if in autonomous mode
        if state.autonomous_mode and state.last_intervention:
            # Draw intervention banner
            cv2.rectangle(frame, (0, 45), (frame.shape[1], 85), (0, 80, 120), -1)
            intervention_text = f"Last: {state.last_intervention[:60]}..."
            cv2.putText(frame, intervention_text, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Show instructions at bottom
        if state.autonomous_mode:
            instructions = "[M]anual mode | [O]stats | [Q]uit | Streaming @ 5 FPS..."
        else:
            instructions = "[C]apture | [SPACE]Voice | [M]Auto mode | [Q]uit"
        cv2.rectangle(frame, (0, frame.shape[0]-35), (frame.shape[1], frame.shape[0]), (50, 50, 50), -1)
        cv2.putText(frame, instructions, (10, frame.shape[0]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        cv2.imshow(window_name, frame)

        # Send frame in autonomous mode
        if state.autonomous_mode and observation_client and observation_client.connected:
            current_time = time.time()
            if current_time - last_frame_time >= frame_interval:
                # Encode frame as JPEG
                _, jpeg_data = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if jpeg_data is not None:
                    loop.run_until_complete(observation_client.send_frame(jpeg_data.tobytes()))
                    last_frame_time = current_time

        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            state.running = False
            break

        elif key == ord('c') and not state.autonomous_mode:
            # Capture image (manual mode only)
            state.last_image = frame.copy()
            state.is_processing = True
            print("\n📸 Capturing homework...")

            # Process OCR in background
            text = process_image_for_ocr(frame)
            if text:
                state.extracted_text = text
                print(f"📝 Detected: {text[:200]}...")
            else:
                print("⚠️ No text detected")
            state.is_processing = False

        elif key == ord(' ') and not state.autonomous_mode:
            # Manual voice trigger
            state.audio_queue.put("manual_trigger")

        elif key == ord('m'):
            # Toggle autonomous observation mode
            loop.run_until_complete(toggle_observation_mode(server_url, child_id))

        elif key == ord('o'):
            # Show observation stats
            print_observation_stats()

    # Cleanup
    if state.autonomous_mode and observation_client:
        loop.run_until_complete(observation_client.disconnect())

    loop.close()
    cv2.destroyAllWindows()


async def toggle_observation_mode(server_url: str, child_id: Optional[str] = None):
    """Toggle autonomous observation mode."""
    global observation_client

    if state.autonomous_mode:
        # Disable autonomous mode
        print("\n🛑 Stopping autonomous observation...")
        if observation_client:
            await observation_client.disconnect()
            observation_client = None
        state.autonomous_mode = False
        state.observation_session_id = None
        print("✅ Switched to manual mode")

    else:
        # Enable autonomous mode
        print("\n🚀 Starting autonomous observation mode...")
        session_id = str(uuid.uuid4())
        state.observation_session_id = session_id

        observation_client = ObservationClient(
            server_url=server_url,
            session_id=session_id,
            child_id=child_id
        )

        connected = await observation_client.connect()
        if connected:
            state.autonomous_mode = True
            state.observation_stats = {
                'frames_sent': 0,
                'interventions_received': 0,
                'session_start': time.time(),
            }
            print("✅ Autonomous observation active!")
            print("   The system will now watch for struggles and intervene proactively.")
        else:
            print("❌ Failed to connect. Make sure the server is running.")
            observation_client = None


def print_observation_stats():
    """Print observation statistics."""
    print("\n" + "=" * 50)
    print("📊 OBSERVATION STATISTICS")
    print("=" * 50)
    print(f"Mode: {'AUTONOMOUS' if state.autonomous_mode else 'MANUAL'}")

    if state.observation_session_id:
        print(f"Session ID: {state.observation_session_id[:8]}...")

    print(f"Frames Sent: {state.observation_stats.get('frames_sent', 0)}")
    print(f"Interventions: {state.observation_stats.get('interventions_received', 0)}")

    if 'session_start' in state.observation_stats:
        duration = time.time() - state.observation_stats['session_start']
        print(f"Session Duration: {duration:.1f}s")

    if state.last_intervention:
        print(f"Last Intervention: {state.last_intervention[:50]}...")

    print("=" * 50 + "\n")


def run_audio_loop(tutor_engine, tts_engine):
    """Run the audio processing loop."""

    # Initial greeting
    speak("Hello! I'm EduLens, your learning buddy. Show me your homework and ask me questions!", tts_engine)

    while state.running:
        try:
            # Check for manual trigger
            try:
                trigger = state.audio_queue.get(timeout=0.5)
                if trigger == "manual_trigger":
                    state.is_listening = True
                    speak("I'm listening!", tts_engine)

                    # Get voice input
                    text = listen_for_speech(duration=5)
                    state.is_listening = False

                    if text:
                        process_voice_query(tutor_engine, text, tts_engine)
                    else:
                        # Fallback to text input
                        print("\n💬 Voice not captured. Type your question:")
                        try:
                            import select
                            import sys

                            # Non-blocking input with timeout
                            if sys.stdin in select.select([sys.stdin], [], [], 10)[0]:
                                text = input().strip()
                                if text:
                                    process_voice_query(tutor_engine, text, tts_engine)
                        except:
                            pass

            except queue.Empty:
                pass

        except Exception as e:
            print(f"Audio loop error: {e}")
            time.sleep(1)


def run_continuous_listening(tutor_engine, tts_engine):
    """Run continuous voice listening mode - always on, hands-free."""

    speak("Hello! I'm EduLens, your learning helper. I'm always listening - just talk to me anytime!", tts_engine)
    print("\n🎧 CONTINUOUS LISTENING MODE - Just speak naturally!")
    print("   Say 'Hey EduLens' to get my attention, or just ask a question.")
    print("   (Handles pauses - waits for you to finish speaking)\n")

    # Voice Activity Detection (VAD) settings
    chunk_duration = 0.3  # Record in small chunks for responsive VAD
    silence_threshold = 0.008  # Audio level to detect speech
    silence_timeout = 1.5  # Seconds of silence before processing (allows natural pauses)
    max_recording_time = 15  # Maximum recording time to prevent runaway

    sample_rate = 16000

    while state.running:
        try:
            import sounddevice as sd
            import numpy as np

            # Listen for initial speech detection
            print("🎤 Listening...                    ", end="\r", flush=True)
            audio_chunk = sd.rec(
                int(chunk_duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype='float32'
            )
            sd.wait()

            # Check if there's actual speech
            audio_level = np.abs(audio_chunk).mean()
            print(f"🎤 Audio level: {audio_level:.4f}          ", end="\r", flush=True)

            if audio_level < silence_threshold:
                continue  # No speech detected, keep waiting

            # Speech detected! Now accumulate audio until silence
            print(f"\n🎤 Speech detected (level: {audio_level:.4f}). Recording...")
            accumulated_audio = [audio_chunk.flatten()]
            silence_start = None
            recording_start = time.time()

            # Continue recording until sustained silence or max time
            while state.running:
                # Record next chunk
                chunk = sd.rec(
                    int(chunk_duration * sample_rate),
                    samplerate=sample_rate,
                    channels=1,
                    dtype='float32'
                )
                sd.wait()

                chunk_level = np.abs(chunk).mean()
                accumulated_audio.append(chunk.flatten())

                # Check for silence
                if chunk_level < silence_threshold:
                    if silence_start is None:
                        silence_start = time.time()
                    elif time.time() - silence_start >= silence_timeout:
                        # Enough silence - user finished speaking
                        print(f"   [End of speech - {silence_timeout}s silence detected]")
                        break
                else:
                    # Speech detected - reset silence counter
                    silence_start = None
                    print(f"   [Recording... level: {chunk_level:.4f}]", end="\r", flush=True)

                # Safety: max recording time
                if time.time() - recording_start > max_recording_time:
                    print(f"   [Max recording time {max_recording_time}s reached]")
                    break

            # Combine all audio chunks
            audio_data = np.concatenate(accumulated_audio).reshape(-1, 1)
            duration = len(audio_data) / sample_rate
            print(f"   [Captured {duration:.1f}s of audio]")

            # Transcribe
            try:
                import whisper
                import tempfile
                import scipy.io.wavfile as wav

                # Load model once
                if not hasattr(run_continuous_listening, 'whisper_model'):
                    print("Loading Whisper model...", flush=True)
                    run_continuous_listening.whisper_model = whisper.load_model("base")
                    print("Whisper model loaded!", flush=True)

                # Save audio to temp file
                temp_path = tempfile.mktemp(suffix='.wav')
                wav.write(temp_path, sample_rate, (audio_data * 32767).astype(np.int16))

                # Transcribe with timing
                import time as time_module
                start_time = time_module.time()
                print(f"   [Transcribing {temp_path}...]", flush=True)

                try:
                    result = run_continuous_listening.whisper_model.transcribe(
                        temp_path,
                        language='en',  # Force English for faster processing
                        fp16=False      # Explicitly disable FP16
                    )
                    elapsed = time_module.time() - start_time
                    text = result.get('text', '').strip()

                    # Debug: show timing and result
                    print(f"   [Transcribed in {elapsed:.1f}s]", flush=True)
                    if text:
                        print(f"   [Whisper]: '{text}'", flush=True)
                    else:
                        print(f"   [Whisper]: (empty result)", flush=True)

                except Exception as transcribe_error:
                    elapsed = time_module.time() - start_time
                    print(f"   [Transcription FAILED after {elapsed:.1f}s: {transcribe_error}]", flush=True)
                    text = ""

                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except:
                    pass

                if not text or len(text) < 2:
                    print("   [Skipped: too short]", flush=True)
                    continue

                print(f"🧒 Heard: {text}")

                # Check for wake word
                if detect_wake_word(text):
                    speak("Yes? I'm listening!", tts_engine)
                    # Listen for the actual question
                    print("🎤 Listening for your question...")
                    audio_data = sd.rec(
                        int(5 * sample_rate),  # 5 seconds for question
                        samplerate=sample_rate,
                        channels=1,
                        dtype='float32'
                    )
                    sd.wait()

                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                        wav.write(f.name, sample_rate, (audio_data * 32767).astype(np.int16))
                        result = run_continuous_listening.whisper_model.transcribe(f.name)
                        os.unlink(f.name)
                        text = result['text'].strip()

                    if text:
                        print(f"🧒 Question: {text}")
                        process_voice_query(tutor_engine, text, tts_engine)
                else:
                    # Direct speech without wake word - be more responsive!
                    # Process any meaningful speech (lowered threshold for natural conversation)
                    text_lower = text.lower()

                    # Respond to greetings
                    greetings = ['hello', 'hi', 'hey', 'good morning', 'good afternoon']
                    is_greeting = any(g in text_lower for g in greetings)

                    # Respond to questions or longer statements
                    is_question = '?' in text or any(w in text_lower for w in ['what', 'how', 'why', 'help', 'can you', 'explain', 'tell me', 'show me'])

                    # Process if it's a greeting, question, or reasonably long statement
                    if is_greeting or is_question or len(text) > 5:
                        process_voice_query(tutor_engine, text, tts_engine)

            except ImportError:
                print("⚠️ Whisper not available for continuous listening")
                time.sleep(2)

        except Exception as e:
            if "sounddevice" in str(e).lower():
                print("⚠️ Microphone not available. Falling back to text mode.")
                run_text_fallback(tutor_engine, tts_engine)
                return
            time.sleep(0.5)


def run_realtime_voice():
    """
    Run OpenAI Realtime API voice conversation mode.

    This uses GPT-4o's native voice capabilities for:
    - Low latency (~300ms) responses
    - Natural voice generation (no separate TTS)
    - Built-in VAD for seamless conversation
    """
    import asyncio

    async def _run_realtime():
        try:
            from src.ai.openai_realtime import (
                create_edulens_voice_service,
                AudioChunk
            )
        except ImportError as e:
            print(f"Error importing OpenAI Realtime service: {e}")
            print("Make sure websockets is installed: pip install websockets")
            return

        # Check for API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "your-openai-api-key-here":
            print("\n" + "=" * 60)
            print("ERROR: OpenAI API key not configured!")
            print("=" * 60)
            print("\nTo use OpenAI Realtime API, add your key to .env:")
            print("  OPENAI_API_KEY=sk-your-key-here")
            print("\nGet your key from: https://platform.openai.com/api-keys")
            print("=" * 60 + "\n")
            return

        print("\n" + "=" * 60)
        print("  OPENAI REALTIME VOICE MODE")
        print("  Using GPT-4o native voice (low latency)")
        print("=" * 60)
        print("\nConnecting to OpenAI Realtime API...")

        # Audio playback queue
        audio_queue = asyncio.Queue()
        playback_task = None

        async def on_assistant_speaking(text: str, audio_data: bytes):
            """Called when assistant finishes speaking."""
            if text:
                print(f"\nEduLens: {text}")

        async def on_user_transcript(text: str):
            """Called when user speech is transcribed."""
            print(f"\nYou: {text}")

        # Create the voice service
        voice_service = create_edulens_voice_service(
            on_assistant_speaking=on_assistant_speaking,
            on_user_transcript=on_user_transcript,
        )

        # Start the conversation
        if not await voice_service.start():
            print("Failed to connect to OpenAI Realtime API")
            print("Check your API key and internet connection.")
            return

        print("Connected! Start speaking naturally.")
        print("(Press Ctrl+C to stop)\n")

        # Audio playback in separate task
        async def play_audio():
            """Play audio chunks from the queue."""
            try:
                import sounddevice as sd
                import numpy as np

                sample_rate = 24000  # OpenAI Realtime uses 24kHz

                while state.running:
                    try:
                        chunk = await voice_service.get_audio_chunk(timeout=0.1)
                        if chunk:
                            # Convert PCM16 bytes to numpy array
                            audio_data = np.frombuffer(chunk.data, dtype=np.int16)
                            audio_float = audio_data.astype(np.float32) / 32768.0

                            # Play audio
                            sd.play(audio_float, samplerate=sample_rate)
                            sd.wait()
                    except asyncio.TimeoutError:
                        pass
                    except Exception as e:
                        if "sounddevice" not in str(e).lower():
                            print(f"Audio playback error: {e}")
            except ImportError:
                print("sounddevice not available for audio playback")

        # Audio capture and streaming
        async def capture_and_stream():
            """Capture audio from microphone and stream to API."""
            try:
                import sounddevice as sd
                import numpy as np

                sample_rate = 24000  # OpenAI Realtime expects 24kHz
                chunk_duration = 0.1  # 100ms chunks

                print("Microphone active. Speak naturally...")

                while state.running:
                    try:
                        # Record a chunk
                        samples = int(sample_rate * chunk_duration)
                        audio = sd.rec(
                            samples,
                            samplerate=sample_rate,
                            channels=1,
                            dtype='int16'
                        )
                        sd.wait()

                        # Convert to bytes and send
                        audio_bytes = audio.tobytes()
                        await voice_service.send_audio_chunk(audio_bytes)

                    except Exception as e:
                        if "sounddevice" not in str(e).lower():
                            print(f"Audio capture error: {e}")
                        await asyncio.sleep(0.1)

            except ImportError:
                print("sounddevice not available for audio capture")
                print("Falling back to text input mode...")

                # Text fallback
                while state.running:
                    try:
                        text = await asyncio.get_event_loop().run_in_executor(
                            None, input, "\nYou (type): "
                        )
                        if text.strip():
                            await voice_service.send_text(text.strip())
                    except EOFError:
                        break

        # Run both tasks concurrently
        playback_task = asyncio.create_task(play_audio())
        capture_task = asyncio.create_task(capture_and_stream())

        try:
            await asyncio.gather(playback_task, capture_task)
        except asyncio.CancelledError:
            pass
        finally:
            await voice_service.stop()
            print("\nRealtime voice session ended.")

    # Run the async function
    try:
        asyncio.run(_run_realtime())
    except KeyboardInterrupt:
        print("\nStopping...")
        state.running = False


def run_text_fallback(tutor_engine, tts_engine):
    """Run text-based interaction when audio isn't available."""

    speak("Hello! I'm EduLens. Type your questions below!", tts_engine)

    while state.running:
        try:
            print("\n🧒 You: ", end="", flush=True)
            query = input().strip()

            if not query:
                continue
            if query.lower() in ['quit', 'exit', 'q']:
                state.running = False
                break
            if query.lower() == 'capture':
                print("📸 Use the camera window to capture (press 'c')")
                continue

            process_voice_query(tutor_engine, query, tts_engine)

        except EOFError:
            break
        except KeyboardInterrupt:
            state.running = False
            break


def main():
    parser = argparse.ArgumentParser(description="EduLens Smart Glasses Simulator")
    parser.add_argument('--no-camera', action='store_true', help='Run without camera')
    parser.add_argument('--no-audio', action='store_true', help='Run without audio (text only)')
    parser.add_argument('--provider', choices=['anthropic', 'openai', 'google', 'deepseek', 'ollama'],
                       help='LLM provider')
    parser.add_argument('--server', default='http://localhost:8000',
                       help='Backend server URL (default: http://localhost:8000)')
    parser.add_argument('--autonomous', '-a', action='store_true',
                       help='Start in autonomous observation mode')
    parser.add_argument('--continuous-listen', '-l', action='store_true',
                       help='Enable continuous voice listening (always-on microphone)')
    parser.add_argument('--realtime', '-r', action='store_true',
                       help='Use OpenAI Realtime API for native voice conversation (requires OPENAI_API_KEY)')
    parser.add_argument('--child-id', help='Child profile ID for personalization')
    args = parser.parse_args()

    if args.provider:
        os.environ['LLM_PROVIDER'] = args.provider

    server_url = args.server

    print("=" * 60)
    print("🕶️  EduLens Smart Glasses Simulator")
    print("=" * 60)
    print("\nThis simulates the smart glasses experience using your computer.\n")

    # Initialize components
    print("Initializing components...")

    # TTS
    tts_engine = init_tts()

    # Tutor
    tutor_engine = init_tutor()
    if not tutor_engine:
        print("❌ Cannot continue without tutor engine")
        print("Make sure you have set your API key (e.g., ANTHROPIC_API_KEY)")
        sys.exit(1)

    # Child ID for parent connection support
    child_id = getattr(args, 'child_id', None)
    if child_id:
        print(f"👶 Using child profile: {child_id}")

    # Camera
    use_camera = not args.no_camera
    cap = None

    if use_camera:
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                print("⚠️ No camera available, running in text mode")
                use_camera = False
            else:
                print("✅ Camera ready")
        except ImportError:
            print("⚠️ OpenCV not installed, running in text mode")
            use_camera = False

    print("\n" + "=" * 60)
    print(f"Server: {server_url}")
    if args.realtime:
        print("Mode: OPENAI REALTIME (GPT-4o native voice)")
    elif args.autonomous:
        print("Mode: AUTONOMOUS (press 'm' to switch to manual)")
    else:
        print("Mode: MANUAL (press 'm' to switch to autonomous)")
    print("=" * 60)

    # Check if using OpenAI Realtime mode
    if args.realtime:
        print("\nStarting OpenAI Realtime voice mode...")
        run_realtime_voice()
        return

    # Determine audio mode
    use_continuous = args.continuous_listen or (args.autonomous and not args.no_audio)

    try:
        if use_camera:
            # Run camera in main thread, audio in background
            if args.no_audio:
                audio_func = run_text_fallback
            elif use_continuous:
                audio_func = run_continuous_listening
                print("🎧 Continuous listening enabled - speak naturally, I'm always listening!")
            else:
                audio_func = run_text_fallback

            audio_thread = threading.Thread(
                target=audio_func,
                args=(tutor_engine, tts_engine),
                daemon=True
            )
            audio_thread.start()

            # Start in autonomous mode if requested
            if args.autonomous:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(toggle_observation_mode(server_url, child_id))
                loop.close()

            run_camera_loop(cap, "EduLens Simulator", server_url, child_id)
        else:
            # Text-only mode
            run_text_fallback(tutor_engine, tts_engine)

    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    finally:
        state.running = False

        # Cleanup observation client
        if observation_client:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(observation_client.disconnect())
            loop.close()

        if cap:
            cap.release()

        # Final goodbye
        speak("Goodbye! Keep learning!", tts_engine)


if __name__ == "__main__":
    main()
