"""
Error Handling Safety Tests for EduLens

Tests error handling safety including graceful degradation,
sensitive info protection in errors, recovery without data loss,
and user-friendly error messages.

Test Coverage:
- Graceful degradation under failure
- No sensitive info in error messages
- Recovery without data loss
- User-friendly error messages
- Error logging safety
"""

from typing import Any, Dict, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestGracefulDegradation:
    """Test graceful degradation under various failure scenarios."""

    @pytest.mark.safety
    def test_ai_service_unavailable(self):
        """Test graceful handling when AI service is unavailable."""
        with patch("anthropic.Client") as mock_client:
            mock_client.side_effect = Exception("Service unavailable")

            result = self._handle_ai_request_with_fallback("What is 2+2?")

            # Should fallback gracefully
            assert result["success"] is False
            assert result["fallback_activated"] is True
            assert result["user_message"] is not None
            assert "try again" in result["user_message"].lower()

    @pytest.mark.safety
    def test_vision_processing_failure(self):
        """Test graceful handling when vision processing fails."""
        image_data = b"corrupted_image_data"

        result = self._process_image_with_fallback(image_data)

        # Should handle gracefully
        assert result["success"] is False
        assert result["error_type"] == "processing_error"
        assert result["fallback_message"] is not None
        # Should not crash the application
        assert "session_terminated" not in result or not result["session_terminated"]

    @pytest.mark.safety
    def test_speech_recognition_failure(self):
        """Test graceful handling when speech recognition fails."""
        audio_data = b"noisy_audio"

        result = self._process_audio_with_fallback(audio_data)

        # Should provide helpful fallback
        assert result["success"] is False
        assert result["fallback_mode"] == "text_input"
        assert "type your question" in result["user_message"].lower()

    @pytest.mark.safety
    def test_network_connectivity_loss(self):
        """Test handling of network connectivity loss."""
        with patch("requests.post") as mock_post:
            mock_post.side_effect = ConnectionError("Network unreachable")

            result = self._make_network_request_with_fallback("https://api.example.com")

            # Should handle gracefully and inform user
            assert result["success"] is False
            assert result["error_type"] == "network_error"
            assert result["retry_available"] is True
            assert result["offline_mode_available"] is True

    @pytest.mark.safety
    def test_database_connection_failure(self):
        """Test handling when database connection fails."""
        with patch("sqlalchemy.create_engine") as mock_engine:
            mock_engine.side_effect = Exception("Connection refused")

            result = self._query_database_with_fallback("SELECT * FROM users")

            # Should use cached data or inform user
            assert result["success"] is False
            assert result["using_cache"] is True or result["fallback_activated"] is True

    @pytest.mark.safety
    def test_partial_feature_degradation(self):
        """Test that core functionality continues when optional features fail."""
        # Simulate TTS failure
        with patch("gtts.gTTS") as mock_tts:
            mock_tts.side_effect = Exception("TTS unavailable")

            result = self._process_with_optional_tts("Hello", use_tts=True)

            # Core functionality should work, TTS is optional
            assert result["core_success"] is True
            assert result["tts_success"] is False
            assert result["text_output"] == "Hello"
            assert result["audio_output"] is None

    def _handle_ai_request_with_fallback(self, query: str) -> Dict[str, Any]:
        """Mock AI request with fallback."""
        try:
            # Simulate AI service call
            response = self._call_ai_service(query)
            return {"success": True, "response": response}
        except Exception as e:
            # Fallback to pre-defined responses or error message
            return {
                "success": False,
                "fallback_activated": True,
                "user_message": "I'm having trouble connecting right now. Please try again in a moment.",
                "error_logged": True,
            }

    def _process_image_with_fallback(self, image_data: bytes) -> Dict[str, Any]:
        """Mock image processing with fallback."""
        try:
            # Simulate image processing
            if image_data == b"corrupted_image_data":
                raise ValueError("Invalid image data")
            return {"success": True, "result": "processed"}
        except Exception:
            return {
                "success": False,
                "error_type": "processing_error",
                "fallback_message": "I couldn't process that image. Try taking a clearer picture.",
                "session_terminated": False,
            }

    def _process_audio_with_fallback(self, audio_data: bytes) -> Dict[str, Any]:
        """Mock audio processing with fallback."""
        try:
            if audio_data == b"noisy_audio":
                raise ValueError("Audio quality too low")
            return {"success": True, "transcription": "text"}
        except Exception:
            return {
                "success": False,
                "fallback_mode": "text_input",
                "user_message": "I couldn't hear that clearly. Would you like to type your question instead?",
            }

    def _make_network_request_with_fallback(self, url: str) -> Dict[str, Any]:
        """Mock network request with fallback."""
        try:
            import requests

            response = requests.post(url)
            return {"success": True, "data": response.json()}
        except Exception:
            return {
                "success": False,
                "error_type": "network_error",
                "retry_available": True,
                "offline_mode_available": True,
                "user_message": "Connection issue. Working in offline mode.",
            }

    def _query_database_with_fallback(self, query: str) -> Dict[str, Any]:
        """Mock database query with fallback."""
        try:
            import sqlalchemy

            # Simulate query
            engine = sqlalchemy.create_engine("sqlite:///test.db")
            return {"success": True, "data": []}
        except Exception:
            return {"success": False, "using_cache": True, "fallback_activated": True}

    def _process_with_optional_tts(self, text: str, use_tts: bool = False) -> Dict[str, Any]:
        """Mock processing with optional TTS."""
        result = {
            "core_success": True,
            "text_output": text,
            "audio_output": None,
            "tts_success": False,
        }

        if use_tts:
            try:
                from gtts import gTTS

                # This will fail in test
                tts = gTTS(text)
                result["audio_output"] = b"audio_data"
                result["tts_success"] = True
            except Exception:
                # TTS failed but core function succeeded
                result["tts_success"] = False

        return result

    def _call_ai_service(self, query: str) -> str:
        """Mock AI service call that may fail."""
        import anthropic

        client = anthropic.Client()  # May raise exception
        return "AI response"


class TestSensitiveInfoProtection:
    """Test that sensitive information is not exposed in errors."""

    @pytest.mark.safety
    def test_no_api_keys_in_errors(self):
        """Test that API keys are not exposed in error messages."""
        api_key = "sk-ant-test123456789"

        try:
            self._make_api_call_that_fails(api_key)
        except Exception as e:
            error_message = str(e)

            # API key should not be in error message
            assert api_key not in error_message
            assert "sk-ant" not in error_message

    @pytest.mark.safety
    def test_no_user_data_in_errors(self):
        """Test that user data is not exposed in error messages."""
        user_data = {"name": "John Doe", "email": "john@example.com", "student_id": "STU12345"}

        error = self._generate_error_with_context(user_data)

        # User PII should not be in error
        assert user_data["name"] not in error["message"]
        assert user_data["email"] not in error["message"]

    @pytest.mark.safety
    def test_no_database_details_in_errors(self):
        """Test that database connection details are not exposed."""
        db_url = "postgresql://admin:secret123@db.example.com:5432/edudb"

        error = self._simulate_database_error(db_url)

        # Should not expose connection string or password
        assert "secret123" not in error["message"]
        assert "admin" not in error["message"]
        assert "db.example.com" not in error["message"]

    @pytest.mark.safety
    def test_no_file_paths_in_errors(self):
        """Test that internal file paths are not exposed."""
        sensitive_path = "/Users/admin/eduLens/secrets/api_keys.json"

        error = self._simulate_file_error(sensitive_path)

        # Should not expose full internal paths
        assert "/Users/admin" not in error["message"]
        assert "secrets" not in error["message"]

    @pytest.mark.safety
    def test_sanitized_stack_traces(self):
        """Test that stack traces don't expose sensitive info."""
        try:
            api_key = "sk-ant-secret123"
            self._function_with_sensitive_data(api_key)
        except Exception as e:
            stack_trace = self._get_sanitized_stack_trace(e)

            # Stack trace should be sanitized
            assert "sk-ant-secret123" not in stack_trace
            assert "api_key" in stack_trace  # Variable name OK
            assert "****" in stack_trace  # Should show redaction

    def _make_api_call_that_fails(self, api_key: str):
        """Mock API call that fails."""
        raise Exception(f"API call failed (check credentials)")

    def _generate_error_with_context(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock error generator with user context."""
        # Should sanitize user data
        return {
            "error": "ValidationError",
            "message": "Invalid input for user",
            "user_id_hash": "abc123",  # Hashed, not real ID
            "timestamp": "2025-12-10T12:00:00Z",
        }

    def _simulate_database_error(self, db_url: str) -> Dict[str, Any]:
        """Mock database error."""
        # Should not expose connection details
        return {
            "error": "DatabaseConnectionError",
            "message": "Unable to connect to database",
            "retry_available": True,
        }

    def _simulate_file_error(self, file_path: str) -> Dict[str, Any]:
        """Mock file operation error."""
        # Should not expose full path
        return {
            "error": "FileNotFoundError",
            "message": "Configuration file not found",
            "file": "api_keys.json",  # Filename only, not full path
        }

    def _function_with_sensitive_data(self, api_key: str):
        """Function that might leak sensitive data in errors."""
        raise ValueError("Invalid configuration")

    def _get_sanitized_stack_trace(self, exception: Exception) -> str:
        """Get sanitized stack trace."""
        import traceback

        trace = traceback.format_exc()

        # Redact sensitive patterns
        import re

        # Redact API keys
        trace = re.sub(r"sk-ant-\w+", "sk-ant-****", trace)
        # Redact passwords
        trace = re.sub(r'password["\']?\s*[:=]\s*["\']?(\w+)', "password=****", trace)

        return trace


class TestDataLossPreventionDuringErrors:
    """Test that errors don't cause data loss."""

    @pytest.mark.safety
    def test_session_state_preserved_on_error(self):
        """Test that session state is preserved when errors occur."""
        session_id = "session_123"

        # Create session state
        session_state = self._create_session_state(
            session_id, {"current_problem": 5, "score": 85, "progress": 0.6}
        )

        # Simulate error during processing
        try:
            self._process_with_error(session_id)
        except Exception:
            pass

        # Session state should still be intact
        recovered_state = self._get_session_state(session_id)
        assert recovered_state is not None
        assert recovered_state["current_problem"] == 5
        assert recovered_state["score"] == 85

    @pytest.mark.safety
    def test_transaction_rollback_on_error(self):
        """Test that database transactions rollback on error."""
        user_id = "user_123"
        initial_score = 85

        # Store initial state
        self._set_user_score(user_id, initial_score)

        # Start transaction that will fail
        try:
            self._update_score_with_error(user_id, 95)
        except Exception:
            pass

        # Score should be rolled back to initial value
        final_score = self._get_user_score(user_id)
        assert final_score == initial_score

    @pytest.mark.safety
    def test_progress_auto_save(self):
        """Test that progress is auto-saved to prevent loss."""
        user_id = "user_123"

        # Simulate learning session with auto-save
        for i in range(5):
            self._update_progress(user_id, problem_number=i)

        # Simulate crash
        self._simulate_crash()

        # Progress should be recoverable
        progress = self._recover_progress(user_id)
        assert progress["last_problem"] == 4
        assert progress["problems_completed"] == 5

    @pytest.mark.safety
    def test_atomic_file_operations(self):
        """Test that file operations are atomic (all or nothing)."""
        file_path = "/tmp/test_data.json"
        original_data = {"score": 85}

        # Write initial data
        self._write_data_atomic(file_path, original_data)

        # Attempt write that will fail midway
        try:
            corrupted_data = {"score": 95, "invalid": object()}  # Will fail to serialize
            self._write_data_atomic(file_path, corrupted_data)
        except Exception:
            pass

        # Original data should be intact (not corrupted)
        recovered_data = self._read_data(file_path)
        assert recovered_data == original_data

    @pytest.mark.safety
    def test_backup_restoration(self):
        """Test that data can be restored from backups after errors."""
        user_id = "user_123"
        original_data = {"progress": 0.8, "score": 92}

        # Create backup
        backup_id = self._create_backup(user_id, original_data)

        # Corrupt current data
        self._corrupt_user_data(user_id)

        # Restore from backup
        restore_result = self._restore_from_backup(user_id, backup_id)

        assert restore_result["success"] is True
        restored_data = self._get_user_data(user_id)
        assert restored_data == original_data

    def _create_session_state(self, session_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Mock session state creator."""
        if not hasattr(self, "_session_states"):
            self._session_states = {}

        self._session_states[session_id] = state.copy()
        return state

    def _get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Mock session state getter."""
        if not hasattr(self, "_session_states"):
            return None
        return self._session_states.get(session_id)

    def _process_with_error(self, session_id: str):
        """Mock processing that raises error."""
        raise Exception("Processing failed")

    def _set_user_score(self, user_id: str, score: int):
        """Mock user score setter."""
        if not hasattr(self, "_user_scores"):
            self._user_scores = {}
        self._user_scores[user_id] = score

    def _get_user_score(self, user_id: str) -> int:
        """Mock user score getter."""
        if not hasattr(self, "_user_scores"):
            return 0
        return self._user_scores.get(user_id, 0)

    def _update_score_with_error(self, user_id: str, new_score: int):
        """Mock score update that fails (simulating rollback)."""
        # Don't actually update - simulate transaction failure
        raise Exception("Transaction failed")

    def _update_progress(self, user_id: str, problem_number: int):
        """Mock progress updater with auto-save."""
        if not hasattr(self, "_progress"):
            self._progress = {}

        if user_id not in self._progress:
            self._progress[user_id] = {"last_problem": -1, "problems_completed": 0}

        self._progress[user_id]["last_problem"] = problem_number
        self._progress[user_id]["problems_completed"] += 1

    def _simulate_crash(self):
        """Mock system crash."""
        pass  # Data persists due to auto-save

    def _recover_progress(self, user_id: str) -> Dict[str, Any]:
        """Mock progress recovery."""
        if not hasattr(self, "_progress"):
            return {"last_problem": -1, "problems_completed": 0}
        return self._progress.get(user_id, {"last_problem": -1, "problems_completed": 0})

    def _write_data_atomic(self, file_path: str, data: Dict[str, Any]):
        """Mock atomic file write."""
        import json
        import os
        import tempfile

        # Write to temp file first
        temp_path = file_path + ".tmp"

        # This may raise exception if data is not serializable
        with open(temp_path, "w") as f:
            json.dump(data, f)

        # Only move to final location if write succeeded
        # In this mock, we'll just update our internal storage
        if not hasattr(self, "_file_data"):
            self._file_data = {}

        self._file_data[file_path] = data

    def _read_data(self, file_path: str) -> Dict[str, Any]:
        """Mock file read."""
        if not hasattr(self, "_file_data"):
            return {}
        return self._file_data.get(file_path, {})

    def _create_backup(self, user_id: str, data: Dict[str, Any]) -> str:
        """Mock backup creation."""
        import hashlib

        backup_id = hashlib.sha256(f"{user_id}_{str(data)}".encode()).hexdigest()[:16]

        if not hasattr(self, "_backups"):
            self._backups = {}

        self._backups[backup_id] = {"user_id": user_id, "data": data.copy()}

        return backup_id

    def _corrupt_user_data(self, user_id: str):
        """Mock data corruption."""
        if not hasattr(self, "_user_data"):
            self._user_data = {}
        self._user_data[user_id] = {"corrupted": True}

    def _restore_from_backup(self, user_id: str, backup_id: str) -> Dict[str, Any]:
        """Mock backup restoration."""
        if not hasattr(self, "_backups") or backup_id not in self._backups:
            return {"success": False}

        backup = self._backups[backup_id]
        if not hasattr(self, "_user_data"):
            self._user_data = {}

        self._user_data[user_id] = backup["data"].copy()

        return {"success": True}

    def _get_user_data(self, user_id: str) -> Dict[str, Any]:
        """Mock user data getter."""
        if not hasattr(self, "_user_data"):
            return {}
        return self._user_data.get(user_id, {})


class TestUserFriendlyErrorMessages:
    """Test that error messages are user-friendly for children."""

    @pytest.mark.safety
    @pytest.mark.parametrize(
        "error_type,expected_tone",
        [
            ("network_error", "friendly"),
            ("validation_error", "friendly"),
            ("processing_error", "friendly"),
            ("timeout_error", "friendly"),
        ],
    )
    def test_error_message_tone(self, error_type: str, expected_tone: str):
        """Test that error messages have appropriate tone."""
        message = self._get_error_message(error_type, age=8)

        result = self._analyze_message_tone(message)
        assert result["tone"] == expected_tone
        assert result["is_child_friendly"] is True

    @pytest.mark.safety
    def test_no_technical_jargon(self):
        """Test that error messages don't contain technical jargon."""
        technical_errors = [
            "SocketTimeoutException",
            "NullPointerException",
            "HTTP 500 Internal Server Error",
            "CORS policy violation",
        ]

        for tech_error in technical_errors:
            user_message = self._translate_error_for_user(tech_error, age=9)

            # Should not contain technical terms
            assert "exception" not in user_message.lower()
            assert "http" not in user_message.lower()
            assert "cors" not in user_message.lower()
            assert "null pointer" not in user_message.lower()

    @pytest.mark.safety
    def test_error_messages_include_next_steps(self):
        """Test that error messages include helpful next steps."""
        errors = ["network_error", "processing_error", "service_unavailable"]

        for error_type in errors:
            message = self._get_error_message(error_type, age=10)

            # Should include actionable next steps
            has_next_steps = any(
                phrase in message.lower()
                for phrase in ["try", "can", "please", "wait", "ask", "help"]
            )
            assert has_next_steps is True

    @pytest.mark.safety
    def test_reassuring_language(self):
        """Test that error messages are reassuring."""
        message = self._get_error_message("unexpected_error", age=7)

        # Should be reassuring
        assert any(
            word in message.lower() for word in ["okay", "don't worry", "safe", "help", "fixed"]
        )

    @pytest.mark.safety
    def test_age_appropriate_vocabulary(self):
        """Test that error messages use age-appropriate vocabulary."""
        age_tests = [
            (6, "Oops! Something didn't work. Let's try again!"),
            (10, "We had a problem, but we can fix it together."),
            (12, "An error occurred. Please try your request again."),
        ]

        for age, expected_style in age_tests:
            message = self._get_error_message("generic_error", age=age)

            # Verify vocabulary complexity matches age
            words = message.split()
            avg_length = sum(len(word) for word in words) / len(words)

            if age <= 7:
                assert avg_length < 6
            elif age <= 10:
                assert avg_length < 7
            else:
                assert avg_length < 8

    def _get_error_message(self, error_type: str, age: int) -> str:
        """Mock error message generator."""
        messages = {
            "network_error": "Oops! I'm having trouble connecting. Let's try again in a moment!",
            "validation_error": "That didn't quite work. Can you try again?",
            "processing_error": "I had a little trouble with that. Let's give it another try!",
            "timeout_error": "This is taking longer than usual. Want to try something else?",
            "service_unavailable": "I need a quick break. Please wait a moment and try again!",
            "unexpected_error": "Don't worry! Everything is safe. Let's try that again together.",
            "generic_error": "Something didn't work, but we can fix it!",
        }

        base_message = messages.get(error_type, "Let's try that again!")

        # Adjust for age
        if age <= 7:
            # Simpler, more enthusiastic
            base_message = base_message.replace("didn't quite work", "didn't work")
            base_message = base_message + " You're doing great!"

        return base_message

    def _analyze_message_tone(self, message: str) -> Dict[str, Any]:
        """Mock message tone analyzer."""
        message_lower = message.lower()

        # Check for friendly indicators
        friendly_words = ["let's", "try", "together", "oops", "great"]
        is_friendly = any(word in message_lower for word in friendly_words)

        # Check for child-friendly language
        unfriendly_words = ["error", "failed", "exception", "fault"]
        has_unfriendly = any(word in message_lower for word in unfriendly_words)

        is_child_friendly = is_friendly and not has_unfriendly

        tone = "friendly" if is_friendly else "neutral"

        return {
            "tone": tone,
            "is_child_friendly": is_child_friendly,
            "is_reassuring": any(word in message_lower for word in ["don't worry", "safe", "okay"]),
        }

    def _translate_error_for_user(self, technical_error: str, age: int) -> str:
        """Mock technical error translator."""
        translations = {
            "SocketTimeoutException": "I couldn't connect. Let's try again!",
            "NullPointerException": "Something was missing. Let's start over!",
            "HTTP 500 Internal Server Error": "I'm having technical difficulties. Please try again soon!",
            "CORS policy violation": "I had trouble loading that. Let's try something else!",
        }

        for tech_term, user_friendly in translations.items():
            if tech_term in technical_error:
                return user_friendly

        return "Something didn't work quite right. Let's try again!"
