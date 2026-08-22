"""
EduLens API Server

FastAPI backend for EduLens smart glasses tutoring system.
Provides endpoints for:
- Tutoring queries (text and image)
- Health checks
- Session management
"""

import asyncio
import base64
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse

# WebSocket handler import
from src.api.websocket_handler import GlassesWebSocketHandler, FrameMessage, ObservationEvent
from src.api.session_broadcaster import SessionBroadcaster, ParentWebSocketHandler, ParentMessage
from pydantic import BaseModel, Field
from typing import List

# Database imports
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.models import (
    ChildDB, SessionDB, ChildCreate, ChildUpdate, ChildResponse,
    init_db, create_async_db_engine, Base
)
from sqlalchemy.ext.asyncio import async_sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Session storage (in production, use Redis)
sessions: dict = {}
tutor_engine = None

# Active observation handlers (WebSocket connections)
observation_handlers: dict[str, GlassesWebSocketHandler] = {}

# Active session broadcasters for parent monitoring
session_broadcasters: dict[str, SessionBroadcaster] = {}

# Database session factory (initialized at startup)
async_session_factory = None


class SimpleTutor:
    """Simple tutor using LLM service directly."""

    def __init__(self, provider: str = "deepseek"):
        from src.ai.llm_service import LLMService
        self.llm = LLMService(provider=provider, safety_filter=True)
        self.system_prompt = """You are EduLens, a friendly AI tutor for children ages 6-12.

TEACHING APPROACH:
- Use the Socratic method: Ask guiding questions instead of giving direct answers
- Be encouraging about EFFORT, but NEVER congratulate wrong answers
- When a student gives a WRONG answer, gently say "Not quite" or "Let's check that" and guide them to the correct answer
- Use age-appropriate language and examples
- Break complex concepts into simple steps

ACCURACY RULES (CRITICAL - FOLLOW EXACTLY):
When a student gives a numerical answer:
1. First, calculate the CORRECT answer to the math problem
2. Then, check if the student's number EXACTLY matches the correct answer
3. If student's number != correct answer, respond with "Not quite" and help them
4. ONLY say "correct" or "right" if student's number == correct answer

Example: Problem is 5+3=?
- Student says "2" → WRONG (2 ≠ 8) → Say "Not quite, let's try again"
- Student says "8" → CORRECT (8 = 8) → Say "That's right!"

NEVER congratulate unless the student's exact number matches the exact correct answer.
NEVER make up facts not in the conversation.

SAFETY RULES (CRITICAL):
- Never provide harmful, inappropriate, or adult content
- Do not discuss violence, drugs, or inappropriate topics
- Redirect off-topic questions back to learning
- Protect student privacy - never ask for personal information
- If unsure about safety, err on the side of caution

Keep responses concise (2-3 sentences for simple questions)."""

    def generate_response(self, query: str, context: dict = None) -> dict:
        """Generate a tutoring response."""
        import asyncio
        from src.ai.llm_service import LLMMessage

        age = context.get('age', 8) if context else 8
        subject = context.get('subject', 'general') if context else 'general'
        history = context.get('history', []) if context else []
        language = context.get('language', 'en') if context else 'en'

        # Build system prompt with language instruction if not English
        system_content = self.system_prompt
        if language != 'en':
            lang_names = {
                'es': 'Spanish', 'fr': 'French', 'de': 'German',
                'zh': 'Chinese (Simplified)', 'hi': 'Hindi', 'ne': 'Nepali'
            }
            lang_name = lang_names.get(language, language)
            system_content += f"""

LANGUAGE INSTRUCTION (CRITICAL):
You MUST respond ONLY in {lang_name}. The child speaks {lang_name} as their primary language.
- Use simple, age-appropriate vocabulary in {lang_name}
- Never switch to English unless the child speaks English first
- Keep explanations clear and simple in {lang_name}"""

        messages = [
            LLMMessage(role="system", content=system_content),
        ]

        # Add conversation history (last 6 exchanges)
        for turn in history[-6:]:
            messages.append(LLMMessage(role="user", content=turn.get('query', '')))
            messages.append(LLMMessage(role="assistant", content=turn.get('response', '')))

        # Add current query
        messages.append(LLMMessage(role="user", content=f"[Student age: {age}, Subject: {subject}]\n\n{query}"))

        try:
            # Handle both sync and async contexts
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, need to run in executor
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self.llm.generate(messages))
                    response = future.result(timeout=30)
            except RuntimeError:
                # No running loop, can use asyncio.run directly
                response = asyncio.run(self.llm.generate(messages))

            return {
                "response": response.content,
                "type": "explanation",
                "subject": subject
            }
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return {
                "response": "That's a great question! Can you tell me more about what you're trying to learn?",
                "type": "fallback",
                "error": str(e)
            }


class TutorQuery(BaseModel):
    """Request model for tutoring queries."""
    query: str = Field(..., min_length=1, max_length=2000, description="The student's question")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    student_age: Optional[int] = Field(8, ge=6, le=12, description="Student's age (6-12)")
    student_grade: Optional[str] = Field("3", description="Student's grade level")
    subject: Optional[str] = Field(None, description="Subject area (math, reading, science, social_studies)")


class TutorResponse(BaseModel):
    """Response model for tutoring queries."""
    response: str
    response_type: str
    session_id: str
    hints_remaining: Optional[int] = None
    subject_detected: Optional[str] = None


class ImageQuery(BaseModel):
    """Request model for image-based queries."""
    session_id: Optional[str] = None
    student_age: Optional[int] = 8
    follow_up_question: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    llm_provider: str
    uptime_seconds: float


# Track server start time
start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources."""
    global tutor_engine, async_session_factory

    logger.info("Starting EduLens API server...")

    # Initialize database
    try:
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            # Convert to async URL
            async_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            engine = create_async_db_engine()
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            logger.info("Database initialized successfully")
        else:
            logger.warning("DATABASE_URL not set, using in-memory storage")
    except Exception as e:
        logger.warning(f"Database init failed: {e}, using in-memory storage")
        async_session_factory = None

    # Initialize tutor engine
    provider = os.getenv("LLM_PROVIDER", "deepseek")

    # Try full tutor engine first
    try:
        from src.ai import create_tutor_engine
        tutor_engine = create_tutor_engine(llm_provider=provider)
        logger.info(f"Tutor engine initialized with {provider}")
    except Exception as e:
        logger.warning(f"Full tutor init failed: {e}, using LLM-only mode")
        # Fallback to simple LLM service wrapper
        try:
            from src.ai.llm_service import LLMService
            tutor_engine = SimpleTutor(provider)
            logger.info(f"Simple tutor initialized with {provider}")
        except Exception as e2:
            logger.error(f"LLM service init failed: {e2}")
            tutor_engine = None

    yield

    # Cleanup
    logger.info("Shutting down EduLens API server...")
    sessions.clear()


# Create FastAPI app
app = FastAPI(
    title="EduLens API",
    description="AI-powered tutoring backend for EduLens smart glasses",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Live tutoring WebSocket router (student app camera streaming)
from src.api.live_ws import router as live_ws_router  # noqa: E402
app.include_router(live_ws_router)


def get_or_create_session(session_id: Optional[str]) -> str:
    """Get existing session or create new one."""
    if session_id and session_id in sessions:
        return session_id

    # Use provided session_id or generate new one
    new_id = session_id if session_id else str(uuid.uuid4())
    sessions[new_id] = {
        "created_at": time.time(),
        "history": [],
        "context": {}
    }
    return new_id


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy" if tutor_engine else "degraded",
        version="1.0.0",
        llm_provider=os.getenv("LLM_PROVIDER", "deepseek"),
        uptime_seconds=time.time() - start_time
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "EduLens API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "demo": "/demo"
    }


@app.get("/demo")
async def serve_demo():
    """Serve the web demo interface."""
    import os
    # Check multiple possible locations
    for path in ["web/index.html", "/app/web/index.html", "../../web/index.html"]:
        if os.path.exists(path):
            return FileResponse(path, media_type="text/html")
    raise HTTPException(status_code=404, detail="Demo page not found")


@app.post("/api/v1/tutor/query", response_model=TutorResponse)
async def tutor_query(request: TutorQuery):
    """
    Process a tutoring query.

    Send a question and receive a Socratic teaching response.
    """
    if not tutor_engine:
        raise HTTPException(status_code=503, detail="Tutor engine not available")

    session_id = get_or_create_session(request.session_id)

    # Build context
    context = {
        "age": request.student_age,
        "grade": request.student_grade,
        "subject": request.subject or "general"
    }

    # Add session context if exists
    if session_id in sessions:
        session_ctx = sessions[session_id].get("context", {})
        if "problem_statement" in session_ctx:
            context["problem_statement"] = session_ctx["problem_statement"]
        # Include conversation history for context
        context["history"] = sessions[session_id].get("history", [])

    try:
        # Generate response
        result = tutor_engine.generate_response(request.query, context)

        # Store in session history
        if session_id in sessions:
            sessions[session_id]["history"].append({
                "query": request.query,
                "response": result["response"],
                "timestamp": time.time()
            })

        return TutorResponse(
            response=result["response"],
            response_type=result.get("type", "explanation"),
            session_id=session_id,
            hints_remaining=result.get("hints_remaining"),
            subject_detected=result.get("subject")
        )

    except Exception as e:
        logger.error(f"Tutor query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/tutor/image")
async def tutor_image(
    image: UploadFile = File(..., description="Homework image to analyze"),
    session_id: Optional[str] = Form(None),
    student_age: int = Form(8),
    question: Optional[str] = Form(None)
):
    """
    Process a homework image.

    Upload an image of homework to extract text and get tutoring help.
    """
    if not tutor_engine:
        raise HTTPException(status_code=503, detail="Tutor engine not available")

    session_id = get_or_create_session(session_id)

    try:
        # Read image
        contents = await image.read()

        # Try OCR
        extracted_text = ""
        try:
            import cv2
            import numpy as np
            from src.vision.ocr_engine import OCREngine

            # Decode image
            nparr = np.frombuffer(contents, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            # Extract text
            ocr = OCREngine()
            result = ocr.extract_text(img)
            extracted_text = result.get("text", "")

        except ImportError:
            # Fallback to pytesseract
            try:
                import pytesseract
                from PIL import Image
                import io

                pil_image = Image.open(io.BytesIO(contents))
                extracted_text = pytesseract.image_to_string(pil_image)
            except Exception as e:
                logger.warning(f"OCR fallback failed: {e}")

        # Store extracted text in session
        if session_id in sessions:
            sessions[session_id]["context"]["problem_statement"] = extracted_text[:1000]

        # Build context
        context = {
            "age": student_age,
            "problem_statement": extracted_text[:1000] if extracted_text else "Image uploaded but text not detected"
        }

        # Generate response
        query = question if question else f"I see this problem: {extracted_text[:500]}. Can you help me understand it?"
        result = tutor_engine.generate_response(query, context)

        return {
            "session_id": session_id,
            "extracted_text": extracted_text[:500] if extracted_text else None,
            "response": result["response"],
            "response_type": result.get("type", "explanation")
        }

    except Exception as e:
        logger.error(f"Image processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/tutor/vision")
async def tutor_vision(
    image: UploadFile = File(..., description="Homework photo for the vision model"),
    question: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    child_name: str = Form("friend"),
    child_age: int = Form(8),
):
    """
    Vision-native tutoring: send the homework photo straight to the DeepSeek
    vision model (no local OCR). The model sees the page and answers with a
    Socratic, age-appropriate hint.

    This is the one-shot counterpart of the /ws/live streaming protocol.
    """
    if not tutor_engine:
        raise HTTPException(status_code=503, detail="Tutor engine not available")

    session_id = get_or_create_session(session_id)

    try:
        contents = await image.read()
        image_b64 = base64.b64encode(contents).decode("utf-8")

        from src.api.live_tutor import TUTOR_SYSTEM_PROMPT

        llm = tutor_engine.llm  # Shared LLMService instance
        prompt = (
            f"The child ({child_name}, age {child_age}) "
            + (f"asks: \"{question}\"" if question else "needs help with what is shown.")
            + "\n\nLook at the attached image of their work and respond "
            "following your tutoring guidelines."
        )

        response = await llm.generate_with_image(
            prompt=prompt,
            image_base64=image_b64,
            image_mime=image.content_type or "image/jpeg",
            system=TUTOR_SYSTEM_PROMPT,
            detail="original",
            max_tokens=1000,  # thinking model: reasoning tokens count against this
            temperature=0.6,
        )

        return {
            "session_id": session_id,
            "response": response.content.strip(),
            "model": response.model,
            "usage": response.usage,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vision tutoring failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/session/{session_id}")
async def get_session(session_id: str):
    """Get session history."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]
    return {
        "session_id": session_id,
        "created_at": session["created_at"],
        "history_count": len(session["history"]),
        "history": session["history"][-10:]  # Last 10 interactions
    }


@app.delete("/api/v1/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session (COPPA compliance - data deletion)."""
    if session_id in sessions:
        del sessions[session_id]
        return {"status": "deleted", "session_id": session_id}
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/api/v1/subjects")
async def list_subjects():
    """List available tutoring subjects."""
    return {
        "subjects": [
            {"id": "math", "name": "Mathematics", "grades": ["K-6"]},
            {"id": "reading", "name": "Reading & Language Arts", "grades": ["K-6"]},
            {"id": "science", "name": "Science", "grades": ["K-6"]},
            {"id": "social_studies", "name": "Social Studies", "grades": ["K-6"]}
        ]
    }


# ============================================
# Database Dependency
# ============================================

async def get_db():
    """Get database session."""
    if async_session_factory is None:
        raise HTTPException(status_code=503, detail="Database not available")
    async with async_session_factory() as session:
        yield session


# ============================================
# Child Profile API Endpoints
# ============================================

@app.post("/api/v1/children", response_model=ChildResponse)
async def create_child(child: ChildCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new child profile.

    Parent app uses this to set up a child with age, grade, and language.
    """
    db_child = ChildDB(
        name=child.name,
        age=child.age,
        grade=child.grade,
        language=child.language,
        parent_id=child.parent_id
    )
    db.add(db_child)
    await db.commit()
    await db.refresh(db_child)

    logger.info(f"Created child profile: {db_child.id}")
    return ChildResponse.model_validate(db_child)


@app.get("/api/v1/children", response_model=List[ChildResponse])
async def list_children(
    parent_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List all children profiles.

    Optionally filter by parent_id.
    """
    query = select(ChildDB)
    if parent_id:
        query = query.where(ChildDB.parent_id == parent_id)

    result = await db.execute(query)
    children = result.scalars().all()

    return [ChildResponse.model_validate(c) for c in children]


@app.get("/api/v1/children/{child_id}", response_model=ChildResponse)
async def get_child(child_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific child profile by ID."""
    result = await db.execute(select(ChildDB).where(ChildDB.id == child_id))
    child = result.scalar_one_or_none()

    if not child:
        raise HTTPException(status_code=404, detail="Child not found")

    return ChildResponse.model_validate(child)


@app.put("/api/v1/children/{child_id}", response_model=ChildResponse)
async def update_child(
    child_id: str,
    updates: ChildUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a child profile."""
    result = await db.execute(select(ChildDB).where(ChildDB.id == child_id))
    child = result.scalar_one_or_none()

    if not child:
        raise HTTPException(status_code=404, detail="Child not found")

    # Apply updates
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(child, field, value)

    await db.commit()
    await db.refresh(child)

    logger.info(f"Updated child profile: {child_id}")
    return ChildResponse.model_validate(child)


@app.delete("/api/v1/children/{child_id}")
async def delete_child(child_id: str, db: AsyncSession = Depends(get_db)):
    """
    Delete a child profile (COPPA compliance - right to deletion).

    This also deletes all associated sessions.
    """
    result = await db.execute(select(ChildDB).where(ChildDB.id == child_id))
    child = result.scalar_one_or_none()

    if not child:
        raise HTTPException(status_code=404, detail="Child not found")

    await db.delete(child)
    await db.commit()

    logger.info(f"Deleted child profile: {child_id}")
    return {"status": "deleted", "child_id": child_id}


# ============================================
# Voice API Endpoints
# ============================================

class VoiceQueryRequest(BaseModel):
    """Request model for voice-based tutoring query."""
    transcript: str = Field(..., min_length=1, description="Transcribed speech text")
    child_id: Optional[str] = None
    session_id: Optional[str] = None
    language: str = "en"


class VoiceQueryResponse(BaseModel):
    """Response model for voice query."""
    response: str
    response_type: str
    session_id: str
    audio_url: Optional[str] = None


class TranscriptionResponse(BaseModel):
    """Response model for audio transcription."""
    transcript: str
    confidence: float
    language: str


@app.post("/api/v1/voice/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(..., description="Audio file (WAV, MP3, M4A)"),
    language: str = Form("en")
):
    """
    Transcribe audio to text.

    Upload audio from smart glasses and get text transcription.
    Uses Whisper ASR for high-quality child speech recognition.
    """
    try:
        # Read audio file
        contents = await audio.read()

        # Try to use the speech recognizer
        transcript = ""
        confidence = 0.0

        try:
            from src.audio.speech_recognizer import SpeechRecognizer

            recognizer = SpeechRecognizer()
            result = recognizer.transcribe(contents, language=language)
            transcript = result.get("text", "")
            confidence = result.get("confidence", 0.9)

        except ImportError:
            # Fallback to simple whisper
            try:
                import whisper
                import tempfile
                import os

                # Save to temp file
                suffix = "." + (audio.filename.split(".")[-1] if audio.filename else "wav")
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                    f.write(contents)
                    temp_path = f.name

                # Transcribe with whisper
                model = whisper.load_model("base")
                result = model.transcribe(temp_path, language=language if language != "auto" else None)
                transcript = result.get("text", "").strip()
                confidence = 0.85

                # Cleanup
                os.unlink(temp_path)

            except Exception as e:
                logger.error(f"Whisper transcription failed: {e}")
                raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")

        return TranscriptionResponse(
            transcript=transcript,
            confidence=confidence,
            language=language
        )

    except Exception as e:
        logger.error(f"Audio transcription failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/voice/query", response_model=VoiceQueryResponse)
async def voice_query(request: VoiceQueryRequest):
    """
    Process a voice-based tutoring query.

    Takes transcribed text and returns AI response with optional TTS audio URL.
    This is the main endpoint for glasses → backend → glasses communication.
    """
    if not tutor_engine:
        raise HTTPException(status_code=503, detail="Tutor engine not available")

    session_id = get_or_create_session(request.session_id)

    # Get child info if provided (including language preference)
    age = 8
    language = "en"  # Default to English
    if request.child_id and async_session_factory:
        try:
            async with async_session_factory() as db:
                result = await db.execute(select(ChildDB).where(ChildDB.id == request.child_id))
                child = result.scalar_one_or_none()
                if child:
                    age = child.age
                    language = child.language or "en"  # Use child's preferred language
        except Exception as e:
            logger.warning(f"Failed to get child info: {e}")

    # Build context with language
    context = {
        "age": age,
        "subject": "general",
        "language": language,  # Include language for multi-lingual support
        "history": sessions.get(session_id, {}).get("history", [])
    }

    try:
        # Generate response
        result = tutor_engine.generate_response(request.transcript, context)

        # Store in session history
        if session_id in sessions:
            sessions[session_id]["history"].append({
                "query": request.transcript,
                "response": result["response"],
                "timestamp": time.time()
            })

        # Generate audio URL (for TTS with language)
        from urllib.parse import quote
        encoded_text = quote(result['response'][:200])
        audio_url = f"/api/v1/voice/synthesize?text={encoded_text}&language={language}&session_id={session_id}"

        return VoiceQueryResponse(
            response=result["response"],
            response_type=result.get("type", "explanation"),
            session_id=session_id,
            audio_url=audio_url
        )

    except Exception as e:
        logger.error(f"Voice query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/voice/synthesize")
async def synthesize_speech(
    text: str,
    voice: str = "child_friendly",
    language: str = "en",  # Language code for multi-language support
    session_id: Optional[str] = None,
    child_id: Optional[str] = None  # Optional: auto-detect language from child profile
):
    """
    Synthesize text to speech audio in the specified language.

    Returns audio file (WAV) for playback on smart glasses speakers.
    Supports 7 languages: en, es, fr, de, zh, hi, ne
    """
    import io

    # Child-friendly voices by language (from tts_engine.py)
    VOICE_MAP = {
        "en": "en-US-AnaNeural",
        "es": "es-MX-DaliaNeural",
        "fr": "fr-FR-EloiseNeural",
        "de": "de-DE-GiselaNeural",
        "zh": "zh-CN-XiaoxiaoNeural",
        "hi": "hi-IN-SwaraNeural",
        "ne": "ne-NP-HemkalaNeural",
    }

    # Get language from child profile if child_id provided
    if child_id and async_session_factory:
        try:
            async with async_session_factory() as db:
                result = await db.execute(select(ChildDB).where(ChildDB.id == child_id))
                child = result.scalar_one_or_none()
                if child and child.language:
                    language = child.language
        except Exception as e:
            logger.warning(f"Failed to get child language: {e}")

    # Select voice based on language
    voice_id = VOICE_MAP.get(language, VOICE_MAP["en"])

    try:
        audio_data = None

        # Try to use TTS engine with language support
        try:
            from src.audio.tts_engine import TTSEngine, TTSConfig, TTSBackend

            config = TTSConfig(
                backend=TTSBackend.EDGE_TTS,
                language=language,
                voice_id=voice_id,
                speaking_rate=0.9  # Slightly slower for children
            )
            tts = TTSEngine(config=config)
            result = await tts.synthesize(text)
            audio_data = result.audio_data

        except ImportError:
            # Fallback to pyttsx3 or edge-tts
            try:
                import pyttsx3
                import tempfile

                engine = pyttsx3.init()
                engine.setProperty('rate', 150)  # Slower for children

                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    temp_path = f.name

                engine.save_to_file(text, temp_path)
                engine.runAndWait()

                with open(temp_path, 'rb') as f:
                    audio_data = f.read()

                import os
                os.unlink(temp_path)

            except Exception as e:
                logger.warning(f"pyttsx3 TTS failed: {e}")

                # Last resort: edge-tts with language-specific voice
                try:
                    import edge_tts
                    import asyncio

                    communicate = edge_tts.Communicate(text, voice_id)  # Language-specific voice
                    audio_buffer = io.BytesIO()

                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            audio_buffer.write(chunk["data"])

                    audio_data = audio_buffer.getvalue()

                except Exception as e2:
                    logger.error(f"All TTS methods failed: {e2}")
                    raise HTTPException(status_code=500, detail="Text-to-speech not available")

        if not audio_data:
            raise HTTPException(status_code=500, detail="Failed to generate audio")

        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/wav",
            headers={"Content-Disposition": f"attachment; filename=response_{session_id or 'audio'}.wav"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Speech synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# WebSocket Observation Endpoint
# ============================================

@app.websocket("/ws/observe/{session_id}")
async def observation_websocket(
    websocket: WebSocket,
    session_id: str,
    child_id: Optional[str] = None
):
    """
    Bidirectional WebSocket for continuous observation mode.

    Protocol:
    - Glasses → Backend: Binary JPEG frames (5 FPS)
    - Backend → Glasses: JSON events + binary audio chunks

    Frame format (binary):
    [1 byte type=0x01][4 bytes frame_id][8 bytes timestamp_ms][N bytes JPEG]

    Event format (JSON):
    {"event_type": "intervention", "payload": {...}, "timestamp": ...}
    """
    # Create frame handler callback
    async def on_frame(frame: FrameMessage):
        """Process incoming frames for struggle detection."""
        # TODO: Integrate with ContinuousObserver (Task 2.2)
        # For now, log frame reception
        logger.debug(f"Frame {frame.frame_id} received: {len(frame.data)} bytes")

    # Create handler
    handler = GlassesWebSocketHandler(
        session_id=session_id,
        child_id=child_id,
        on_frame=on_frame
    )

    try:
        # Store handler
        observation_handlers[session_id] = handler

        # Connect and accept WebSocket
        await handler.connect(websocket)

        # Start observation mode
        await handler.start_observation()

        # Keep connection alive until disconnected
        # The receive_loop in the handler manages this
        while handler.state.value == "observing":
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        logger.info(f"Observation WebSocket disconnected: {session_id}")

    except Exception as e:
        logger.error(f"Observation WebSocket error: {e}")

    finally:
        # Cleanup
        if session_id in observation_handlers:
            del observation_handlers[session_id]
        await handler.disconnect()


@app.get("/api/v1/observation/sessions")
async def list_observation_sessions():
    """List active observation sessions."""
    return {
        "active_sessions": [
            {
                "session_id": sid,
                "child_id": h.child_id,
                "state": h.state.value,
                **h.get_stats()
            }
            for sid, h in observation_handlers.items()
        ],
        "total": len(observation_handlers)
    }


@app.get("/api/v1/observation/sessions/{session_id}")
async def get_observation_session(session_id: str):
    """Get details of a specific observation session."""
    if session_id not in observation_handlers:
        raise HTTPException(status_code=404, detail="Observation session not found")

    handler = observation_handlers[session_id]
    return handler.get_stats()


@app.post("/api/v1/observation/sessions/{session_id}/stop")
async def stop_observation_session(session_id: str):
    """Stop an active observation session."""
    if session_id not in observation_handlers:
        raise HTTPException(status_code=404, detail="Observation session not found")

    handler = observation_handlers[session_id]
    await handler.stop_observation()

    return {"status": "stopped", "session_id": session_id, **handler.get_stats()}


# ============================================
# Parent Live Monitoring WebSocket Endpoint
# ============================================

async def verify_parent_access(parent_id: str, session_id: str) -> bool:
    """
    Verify parent owns the child in this session.

    Args:
        parent_id: Parent user ID (from JWT token)
        session_id: Observation session ID

    Returns:
        True if parent is authorized to view this session
    """
    # Check if session exists
    broadcaster = session_broadcasters.get(session_id)
    if not broadcaster:
        # Also check observation_handlers for sessions not yet using broadcaster
        handler = observation_handlers.get(session_id)
        if not handler:
            return False
        child_id = handler.child_id
    else:
        child_id = broadcaster.child_id

    if not child_id:
        # Allow access for testing/dev mode when no child is associated
        # In production, this should return False
        logger.warning(f"Session {session_id} has no child_id - allowing parent access for dev mode")
        return True

    # Get child from database and verify parent ownership
    if async_session_factory is None:
        # Fallback for when DB not available - allow access
        logger.warning("Database not available for parent verification")
        return True

    try:
        async with async_session_factory() as db:
            result = await db.execute(
                select(ChildDB).where(ChildDB.id == child_id)
            )
            child = result.scalar_one_or_none()

            if not child:
                return False

            # Check if parent_id matches
            return child.parent_id == parent_id

    except Exception as e:
        logger.error(f"Error verifying parent access: {e}")
        return False


async def get_or_create_broadcaster(session_id: str, child_id: str, child_language: str = "en") -> SessionBroadcaster:
    """Get existing broadcaster or create new one."""
    if session_id not in session_broadcasters:
        broadcaster = SessionBroadcaster(
            session_id=session_id,
            child_id=child_id,
            child_language=child_language,
        )
        session_broadcasters[session_id] = broadcaster

        # Link to existing glasses handler if one exists
        if session_id in observation_handlers:
            await broadcaster.set_glasses_handler(observation_handlers[session_id])

    return session_broadcasters[session_id]


@app.websocket("/ws/parent/{session_id}")
async def parent_stream_websocket(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = None,
    notify_child: bool = True,
):
    """
    Parent app connects to watch child's observation session.

    Args:
        websocket: WebSocket connection
        session_id: Observation session ID
        token: JWT auth token (query param or header)
        notify_child: Whether to notify child when parent connects

    Protocol:
    - Parent receives: JPEG frames (quality-adjusted) + observation events
    - Parent sends: Voice messages, text guidance, encouragement

    Message formats:
    - Outgoing frames: Binary JPEG data
    - Outgoing events: JSON {"type": "...", "payload": {...}}
    - Incoming messages: JSON {"type": "text_message|voice_message|encouragement", "content": "..."}
    """
    # TODO: In production, verify JWT token
    # For now, extract parent_id from token or use placeholder
    parent_id = token or "anonymous_parent"

    # Verify parent has access to this session
    if not await verify_parent_access(parent_id, session_id):
        await websocket.close(code=4003, reason="Unauthorized: Cannot access this session")
        return

    # Check if session exists
    if session_id not in observation_handlers and session_id not in session_broadcasters:
        await websocket.close(code=4004, reason="Session not found")
        return

    # Get child info for broadcaster
    child_id = None
    child_language = "en"
    child_allow_monitoring = True
    child_notify_on_connect = True

    if session_id in observation_handlers:
        child_id = observation_handlers[session_id].child_id

    if child_id and async_session_factory:
        try:
            async with async_session_factory() as db:
                result = await db.execute(
                    select(ChildDB).where(ChildDB.id == child_id)
                )
                child = result.scalar_one_or_none()
                if child:
                    child_language = child.language or "en"
                    child_allow_monitoring = child.allow_remote_monitoring if hasattr(child, 'allow_remote_monitoring') else True
                    child_notify_on_connect = child.notify_child_on_connect if hasattr(child, 'notify_child_on_connect') else True
        except Exception as e:
            logger.warning(f"Could not fetch child settings: {e}")

    # Check if remote monitoring is allowed for this child
    if not child_allow_monitoring:
        await websocket.close(code=4005, reason="Remote monitoring disabled for this child")
        return

    # Override notify_child based on child's settings (must be enabled by child AND parent)
    effective_notify_child = notify_child and child_notify_on_connect

    # Get or create broadcaster
    broadcaster = await get_or_create_broadcaster(
        session_id,
        child_id or "unknown",
        child_language
    )

    # Create parent handler
    parent_handler = ParentWebSocketHandler(
        parent_id=parent_id,
        session_id=session_id,
        notify_child=effective_notify_child,
    )

    try:
        # Connect WebSocket
        await parent_handler.connect(websocket)

        # Add to broadcaster
        broadcaster.add_parent(parent_handler)

        logger.info(f"Parent {parent_id} connected to session {session_id}")

        # Keep connection alive
        while parent_handler._connected:
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        logger.info(f"Parent WebSocket disconnected: {parent_id}")

    except Exception as e:
        logger.error(f"Parent WebSocket error: {e}")

    finally:
        # Cleanup
        broadcaster.remove_parent(parent_handler)
        await parent_handler.disconnect()

        # Remove broadcaster if no more clients
        if not broadcaster.parent_handlers and broadcaster.glasses_handler is None:
            if session_id in session_broadcasters:
                del session_broadcasters[session_id]


@app.get("/api/v1/parent/sessions")
async def list_parent_sessions(parent_id: Optional[str] = None):
    """
    List observation sessions available for parent monitoring.

    Args:
        parent_id: Filter by parent ID (from auth)
    """
    available_sessions = []

    for session_id, handler in observation_handlers.items():
        child_id = handler.child_id

        # Check if parent has access
        if parent_id and child_id:
            has_access = await verify_parent_access(parent_id, session_id)
            if not has_access:
                continue

        session_info = {
            "session_id": session_id,
            "child_id": child_id,
            "state": handler.state.value,
            "frame_count": handler.frame_count,
            "connected_at": handler.connected_at,
            "parent_count": len(session_broadcasters.get(session_id, SessionBroadcaster(session_id, "")).parent_handlers) if session_id in session_broadcasters else 0,
        }
        available_sessions.append(session_info)

    return {
        "sessions": available_sessions,
        "total": len(available_sessions)
    }


@app.get("/api/v1/parent/sessions/{session_id}")
async def get_parent_session_details(session_id: str, parent_id: Optional[str] = None):
    """Get details of a specific session for parent monitoring."""
    if session_id not in observation_handlers:
        raise HTTPException(status_code=404, detail="Session not found")

    # Verify access
    if parent_id:
        has_access = await verify_parent_access(parent_id, session_id)
        if not has_access:
            raise HTTPException(status_code=403, detail="Not authorized to view this session")

    handler = observation_handlers[session_id]
    broadcaster = session_broadcasters.get(session_id)

    return {
        "session_id": session_id,
        "child_id": handler.child_id,
        "state": handler.state.value,
        "glasses_stats": handler.get_stats(),
        "broadcaster_stats": broadcaster.get_stats() if broadcaster else None,
    }


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle uncaught exceptions."""
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=os.getenv("EDULENS_API_HOST", "0.0.0.0"),
        port=int(os.getenv("EDULENS_API_PORT", "8000")),
        reload=True
    )
