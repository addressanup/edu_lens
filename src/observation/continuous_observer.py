"""
ContinuousObserver - Main Autonomous Observation Service

Orchestrates continuous monitoring of child's homework activity
and triggers proactive interventions when struggles are detected.
"""

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


class ObservationState(Enum):
    """Observation session states."""
    IDLE = "idle"
    OBSERVING = "observing"
    STRUGGLE_DETECTED = "struggle"
    INTERVENING = "intervening"
    COOLDOWN = "cooldown"


@dataclass
class Frame:
    """A single observation frame."""
    frame_id: int
    timestamp: float
    data: bytes  # JPEG compressed
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ObservationEvent:
    """Event generated during observation."""
    event_type: str  # "scene_change", "struggle_detected", "intervention", "problem_completed"
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "payload": self.payload,
            "timestamp": self.timestamp
        }


@dataclass
class ObservationConfig:
    """Configuration for observation service."""
    # Frame settings
    target_fps: int = 5
    frame_buffer_size: int = 30  # ~6 seconds at 5 FPS

    # Scene detection
    scene_detection_enabled: bool = True
    homework_confidence_threshold: float = 0.7
    scene_change_threshold: float = 0.3
    min_stable_frames: int = 5

    # Struggle detection
    struggle_detection_enabled: bool = True
    time_on_problem_threshold_seconds: float = 45.0
    warning_threshold_seconds: float = 30.0
    idle_threshold_seconds: float = 15.0
    motion_threshold: float = 0.05

    # Intervention
    intervention_enabled: bool = True
    cooldown_seconds: float = 60.0
    max_interventions_per_problem: int = 3
    intervention_delay_seconds: float = 2.0
    use_child_name: bool = True
    vary_messages: bool = True

    # Privacy
    store_frames: bool = False
    store_problem_text: bool = True
    retention_minutes: int = 5

    @classmethod
    def from_yaml(cls, path: str) -> 'ObservationConfig':
        """Load configuration from YAML file."""
        with open(path, 'r') as f:
            data = yaml.safe_load(f)

        obs = data.get('observation', {})
        struggle = data.get('struggle_detection', {})
        intervention = data.get('intervention', {})
        privacy = data.get('privacy', {})

        return cls(
            target_fps=obs.get('target_fps', 5),
            frame_buffer_size=obs.get('frame_buffer_size', 30),
            scene_detection_enabled=obs.get('scene_detection', {}).get('enabled', True),
            homework_confidence_threshold=obs.get('scene_detection', {}).get('homework_confidence_threshold', 0.7),
            scene_change_threshold=obs.get('scene_detection', {}).get('scene_change_threshold', 0.3),
            min_stable_frames=obs.get('scene_detection', {}).get('min_stable_frames', 5),
            struggle_detection_enabled=struggle.get('enabled', True),
            time_on_problem_threshold_seconds=struggle.get('time_on_problem_threshold_seconds', 45.0),
            warning_threshold_seconds=struggle.get('warning_threshold_seconds', 30.0),
            idle_threshold_seconds=struggle.get('idle_threshold_seconds', 15.0),
            motion_threshold=struggle.get('motion_threshold', 0.05),
            intervention_enabled=intervention.get('enabled', True),
            cooldown_seconds=intervention.get('cooldown_seconds', 60.0),
            max_interventions_per_problem=intervention.get('max_interventions_per_problem', 3),
            intervention_delay_seconds=intervention.get('intervention_delay_seconds', 2.0),
            use_child_name=intervention.get('use_child_name', True),
            vary_messages=intervention.get('vary_messages', True),
            store_frames=privacy.get('store_frames', False),
            store_problem_text=privacy.get('store_problem_text', True),
            retention_minutes=privacy.get('retention_minutes', 5),
        )


class RingBuffer:
    """Fixed-size ring buffer for frame storage."""

    def __init__(self, max_size: int):
        self.max_size = max_size
        self._buffer: deque = deque(maxlen=max_size)

    def append(self, item: Any) -> None:
        self._buffer.append(item)

    def get_recent(self, n: int = None) -> List[Any]:
        """Get most recent n items."""
        if n is None or n >= len(self._buffer):
            return list(self._buffer)
        return list(self._buffer)[-n:]

    def __len__(self) -> int:
        return len(self._buffer)

    def __getitem__(self, index: int) -> Any:
        return self._buffer[index]

    def clear(self) -> None:
        self._buffer.clear()


class ContinuousObserver:
    """
    Main autonomous observation service.

    Orchestrates:
    - Frame buffering
    - Scene analysis (homework detection, OCR)
    - Problem tracking (engagement time, activity)
    - Struggle detection (time-based, activity-based, visual)
    - Proactive intervention generation
    """

    def __init__(
        self,
        session_id: str,
        child_id: Optional[str] = None,
        child_name: Optional[str] = None,
        language: str = "en",
        config: Optional[ObservationConfig] = None,
        on_event: Optional[Callable[[ObservationEvent], Awaitable[None]]] = None,
    ):
        """
        Initialize continuous observer.

        Args:
            session_id: Unique observation session ID
            child_id: Child profile ID (for personalization)
            child_name: Child's name (for personalized messages)
            language: Language for interventions
            config: Observation configuration
            on_event: Callback for observation events
        """
        self.session_id = session_id
        self.child_id = child_id
        self.child_name = child_name
        self.language = language
        self.config = config or ObservationConfig()
        self.on_event = on_event

        # State
        self.state = ObservationState.IDLE
        self.started_at: Optional[float] = None
        self.last_frame_at: Optional[float] = None

        # Frame buffer
        self.frame_buffer = RingBuffer(self.config.frame_buffer_size)

        # Scene tracking
        self.current_scene: Optional[str] = None  # "homework", "non_homework", "unknown"
        self.scene_stable_frames = 0

        # Problem tracking
        self.current_problem: Optional[Dict[str, Any]] = None
        self.problem_start_time: Optional[float] = None
        self.problem_interventions = 0
        self.last_activity_time: Optional[float] = None
        self.activity_state = "active"  # "active", "idle", "erasing"

        # Intervention tracking
        self.last_intervention_time: Optional[float] = None
        self.total_interventions = 0

        # Statistics
        self.stats = {
            "frames_processed": 0,
            "problems_detected": 0,
            "struggles_detected": 0,
            "interventions_triggered": 0,
        }

        # Lazy-loaded components
        self._scene_analyzer = None
        self._problem_tracker = None
        self._struggle_detector = None
        self._intervention_manager = None

        logger.info(f"ContinuousObserver initialized for session {session_id}")

    async def start(self) -> None:
        """Start observation."""
        self.state = ObservationState.OBSERVING
        self.started_at = time.time()
        self.last_activity_time = time.time()
        logger.info(f"Observation started for session {self.session_id}")

    async def stop(self) -> None:
        """Stop observation."""
        self.state = ObservationState.IDLE
        duration = time.time() - (self.started_at or time.time())
        logger.info(f"Observation stopped for session {self.session_id}, duration: {duration:.1f}s")

    async def process_frame(self, frame: Frame) -> Optional[ObservationEvent]:
        """
        Process an incoming frame from the glasses.

        Args:
            frame: Frame data from glasses camera

        Returns:
            ObservationEvent if an event was triggered, None otherwise
        """
        if self.state == ObservationState.IDLE:
            return None

        self.last_frame_at = time.time()
        self.stats["frames_processed"] += 1

        # Add to buffer
        self.frame_buffer.append(frame)

        # Skip processing during cooldown
        if self.state == ObservationState.COOLDOWN:
            if self._cooldown_expired():
                self.state = ObservationState.OBSERVING
            else:
                return None

        # Skip processing during intervention
        if self.state == ObservationState.INTERVENING:
            return None

        event = None

        try:
            # Step 1: Analyze scene
            if self.config.scene_detection_enabled:
                scene_event = await self._analyze_scene(frame)
                if scene_event:
                    event = scene_event

            # Step 2: Track problem engagement (only if homework scene)
            if self.current_scene == "homework":
                await self._track_problem(frame)

                # Step 3: Detect struggle
                if self.config.struggle_detection_enabled:
                    struggle = await self._detect_struggle(frame)

                    if struggle:
                        self.state = ObservationState.STRUGGLE_DETECTED
                        self.stats["struggles_detected"] += 1

                        # Step 4: Generate intervention
                        if self.config.intervention_enabled and self._can_intervene():
                            event = await self._generate_intervention(struggle)

        except Exception as e:
            logger.error(f"Error processing frame: {e}")

        return event

    async def _analyze_scene(self, frame: Frame) -> Optional[ObservationEvent]:
        """Analyze frame to detect homework scene."""
        # Lazy load scene analyzer
        if self._scene_analyzer is None:
            try:
                from .scene_analyzer import SceneAnalyzer
                self._scene_analyzer = SceneAnalyzer()
            except ImportError:
                logger.warning("SceneAnalyzer not available, using placeholder")
                self._scene_analyzer = PlaceholderSceneAnalyzer()

        result = await self._scene_analyzer.analyze(frame)
        new_scene = result.get("scene_type", "unknown")
        confidence = result.get("confidence", 0.0)

        # Check for scene change
        if new_scene != self.current_scene and confidence >= self.config.homework_confidence_threshold:
            self.scene_stable_frames += 1

            if self.scene_stable_frames >= self.config.min_stable_frames:
                old_scene = self.current_scene
                self.current_scene = new_scene
                self.scene_stable_frames = 0

                # Reset problem tracking on scene change
                if new_scene == "homework" and old_scene != "homework":
                    self.current_problem = None
                    self.problem_start_time = None

                event = ObservationEvent(
                    event_type="scene_change",
                    payload={
                        "previous_scene": old_scene,
                        "new_scene": new_scene,
                        "confidence": confidence
                    }
                )

                if self.on_event:
                    await self.on_event(event)

                return event
        else:
            self.scene_stable_frames = 0

        return None

    async def _track_problem(self, frame: Frame) -> None:
        """Track current problem engagement."""
        # Lazy load problem tracker
        if self._problem_tracker is None:
            try:
                from .problem_tracker import ProblemTracker
                self._problem_tracker = ProblemTracker()
            except ImportError:
                logger.debug("ProblemTracker not available, using placeholder")
                self._problem_tracker = PlaceholderProblemTracker()

        result = await self._problem_tracker.track(frame, self.current_problem)

        # Check if we have a new problem
        if result.get("new_problem"):
            self.current_problem = result.get("problem")
            self.problem_start_time = time.time()
            self.problem_interventions = 0
            self.stats["problems_detected"] += 1
            logger.info(f"New problem detected: {self.current_problem}")

        # Update activity state
        activity = result.get("activity", "unknown")
        if activity != "unknown":
            if activity == "writing" or activity == "active":
                self.last_activity_time = time.time()
                self.activity_state = "active"
            elif activity == "erasing":
                self.activity_state = "erasing"
            elif activity == "idle":
                self.activity_state = "idle"

    async def _detect_struggle(self, frame: Frame) -> Optional[Dict[str, Any]]:
        """Detect if child is struggling with current problem."""
        if not self.current_problem or not self.problem_start_time:
            return None

        # Lazy load struggle detector
        if self._struggle_detector is None:
            try:
                from .struggle_detector import StruggleDetector
                self._struggle_detector = StruggleDetector(self.config)
            except ImportError:
                logger.debug("StruggleDetector not available, using placeholder")
                self._struggle_detector = PlaceholderStruggleDetector(self.config)

        # Gather struggle indicators
        time_on_problem = time.time() - self.problem_start_time
        idle_time = time.time() - (self.last_activity_time or time.time())

        indicators = {
            "time_on_problem": time_on_problem,
            "idle_time": idle_time,
            "activity_state": self.activity_state,
            "problem": self.current_problem,
            "intervention_count": self.problem_interventions,
        }

        struggle = await self._struggle_detector.detect(frame, indicators)

        if struggle and struggle.get("is_struggling"):
            return struggle

        return None

    def _can_intervene(self) -> bool:
        """Check if we can trigger an intervention."""
        # Check cooldown
        if self.last_intervention_time:
            elapsed = time.time() - self.last_intervention_time
            if elapsed < self.config.cooldown_seconds:
                return False

        # Check max interventions per problem
        if self.problem_interventions >= self.config.max_interventions_per_problem:
            return False

        return True

    async def _generate_intervention(self, struggle: Dict[str, Any]) -> Optional[ObservationEvent]:
        """Generate proactive intervention."""
        # Lazy load intervention manager
        if self._intervention_manager is None:
            try:
                from .intervention_manager import InterventionManager
                self._intervention_manager = InterventionManager(
                    language=self.language,
                    child_name=self.child_name,
                    config=self.config
                )
            except ImportError:
                logger.debug("InterventionManager not available, using placeholder")
                self._intervention_manager = PlaceholderInterventionManager(
                    language=self.language,
                    child_name=self.child_name,
                    config=self.config
                )

        # Determine intervention type based on history
        intervention_types = ["gentle_prompt", "hint_offer", "check_in", "encouragement"]
        intervention_type = intervention_types[min(self.problem_interventions, len(intervention_types) - 1)]

        # Generate intervention
        intervention = await self._intervention_manager.generate(
            intervention_type=intervention_type,
            struggle_reason=struggle.get("reason"),
            problem=self.current_problem,
            problem_time=time.time() - (self.problem_start_time or time.time())
        )

        if intervention:
            self.state = ObservationState.INTERVENING
            self.last_intervention_time = time.time()
            self.problem_interventions += 1
            self.total_interventions += 1
            self.stats["interventions_triggered"] += 1

            event = ObservationEvent(
                event_type="intervention",
                payload={
                    "intervention_type": intervention_type,
                    "message": intervention.get("message"),
                    "audio_data": intervention.get("audio_data"),
                    "struggle_reason": struggle.get("reason"),
                    "time_on_problem": time.time() - (self.problem_start_time or time.time()),
                }
            )

            if self.on_event:
                await self.on_event(event)

            # Enter cooldown after short delay
            asyncio.create_task(self._enter_cooldown_after_delay())

            return event

        return None

    async def _enter_cooldown_after_delay(self) -> None:
        """Enter cooldown state after intervention delay."""
        await asyncio.sleep(self.config.intervention_delay_seconds)
        if self.state == ObservationState.INTERVENING:
            self.state = ObservationState.COOLDOWN

    def _cooldown_expired(self) -> bool:
        """Check if cooldown period has expired."""
        if not self.last_intervention_time:
            return True
        elapsed = time.time() - self.last_intervention_time
        return elapsed >= self.config.cooldown_seconds

    def get_stats(self) -> Dict[str, Any]:
        """Get observation statistics."""
        return {
            "session_id": self.session_id,
            "child_id": self.child_id,
            "state": self.state.value,
            "started_at": self.started_at,
            "duration_seconds": time.time() - (self.started_at or time.time()),
            "current_scene": self.current_scene,
            "current_problem": self.current_problem,
            "problem_time_seconds": time.time() - (self.problem_start_time or time.time()) if self.problem_start_time else 0,
            "problem_interventions": self.problem_interventions,
            "total_interventions": self.total_interventions,
            "buffer_size": len(self.frame_buffer),
            **self.stats
        }


# ============================================
# Placeholder Classes (for when modules aren't available)
# ============================================

class PlaceholderSceneAnalyzer:
    """Placeholder scene analyzer when real one isn't available."""

    async def analyze(self, frame: Frame) -> Dict[str, Any]:
        # Simple heuristic: assume homework if frame is reasonably sized
        return {
            "scene_type": "homework",
            "confidence": 0.8,
        }


class PlaceholderProblemTracker:
    """Placeholder problem tracker when real one isn't available."""

    def __init__(self):
        self._last_problem_time = 0

    async def track(self, frame: Frame, current_problem: Optional[Dict]) -> Dict[str, Any]:
        now = time.time()
        # Simulate detecting a new problem every 60 seconds if none exists
        if not current_problem and (now - self._last_problem_time) > 60:
            self._last_problem_time = now
            return {
                "new_problem": True,
                "problem": {"id": f"problem_{int(now)}", "text": "Math problem"},
                "activity": "writing",
            }
        return {
            "new_problem": False,
            "problem": current_problem,
            "activity": "writing",
        }


class PlaceholderStruggleDetector:
    """Placeholder struggle detector when real one isn't available."""

    def __init__(self, config: ObservationConfig):
        self.config = config

    async def detect(self, frame: Frame, indicators: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        time_on_problem = indicators.get("time_on_problem", 0)
        idle_time = indicators.get("idle_time", 0)

        # Time-based detection
        if time_on_problem >= self.config.time_on_problem_threshold_seconds:
            return {
                "is_struggling": True,
                "reason": "time_threshold",
                "time_on_problem": time_on_problem,
            }

        # Idle detection
        if idle_time >= self.config.idle_threshold_seconds:
            return {
                "is_struggling": True,
                "reason": "idle",
                "idle_time": idle_time,
            }

        return None


class PlaceholderInterventionManager:
    """Placeholder intervention manager when real one isn't available."""

    MESSAGES = {
        "en": {
            "gentle_prompt": [
                "I see you've been working on this for a while. Would you like a hint?",
                "This one looks tricky! Do you want me to help?",
            ],
            "hint_offer": [
                "I have an idea that might help! Want to hear it?",
            ],
            "check_in": [
                "How's it going? Let me know if you need anything!",
            ],
            "encouragement": [
                "I see you working hard! Keep it up!",
                "Don't give up - you're getting closer!",
            ],
        },
        "es": {
            "gentle_prompt": [
                "Veo que has estado trabajando en esto. Te gustaria una pista?",
            ],
            "hint_offer": [
                "Tengo una idea que podria ayudar!",
            ],
            "check_in": [
                "Como va? Dime si necesitas algo!",
            ],
            "encouragement": [
                "Te veo trabajando duro! Muy bien!",
            ],
        },
    }

    def __init__(self, language: str, child_name: Optional[str], config: ObservationConfig):
        self.language = language
        self.child_name = child_name
        self.config = config
        self._message_index = {}

    async def generate(
        self,
        intervention_type: str,
        struggle_reason: Optional[str],
        problem: Optional[Dict],
        problem_time: float
    ) -> Optional[Dict[str, Any]]:
        messages = self.MESSAGES.get(self.language, self.MESSAGES["en"])
        type_messages = messages.get(intervention_type, messages.get("gentle_prompt", []))

        if not type_messages:
            return None

        # Select message (vary if configured)
        if self.config.vary_messages:
            idx = self._message_index.get(intervention_type, 0)
            message = type_messages[idx % len(type_messages)]
            self._message_index[intervention_type] = idx + 1
        else:
            message = type_messages[0]

        # Personalize with name if configured
        if self.config.use_child_name and self.child_name:
            message = f"{self.child_name}, {message[0].lower()}{message[1:]}"

        return {
            "message": message,
            "intervention_type": intervention_type,
            "audio_data": None,  # TTS would be generated here
        }
