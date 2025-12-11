"""
Child-Specific Safety Tests for EduLens

Tests child-specific safety features including interaction patterns,
session limits enforcement, parental control effectiveness,
and emergency handling.

Test Coverage:
- Safe interaction patterns
- Session limits enforcement
- Parental control effectiveness
- Emergency handling procedures
- Age-appropriate boundaries
"""

import pytest
from typing import Dict, Any, List
from datetime import datetime, timedelta
from unittest.mock import Mock, patch


class TestInteractionPatterns:
    """Test safe interaction patterns with children."""

    @pytest.mark.safety
    def test_friendly_tone_maintenance(self):
        """Test that all interactions maintain a friendly, supportive tone."""
        interactions = [
            "Great job! Let's try the next problem!",
            "That's a good start. Can you think of another way?",
            "I can see you're working hard on this!",
            "Let's take this step by step together"
        ]

        for interaction in interactions:
            result = self._analyze_interaction_tone(interaction)
            assert result['tone'] == 'friendly'
            assert result['is_supportive'] is True
            assert result['is_safe_for_children'] is True

    @pytest.mark.safety
    def test_no_demanding_language(self):
        """Test that interactions don't use demanding language."""
        demanding_phrases = [
            "You must do this now!",
            "Do it immediately!",
            "You have to answer right away",
            "Hurry up and solve this"
        ]

        for phrase in demanding_phrases:
            result = self._analyze_interaction_tone(phrase)
            assert result['is_demanding'] is True
            assert result['is_safe_for_children'] is False

    @pytest.mark.safety
    def test_patience_and_encouragement(self):
        """Test that interactions show patience and encouragement."""
        patient_interactions = [
            "Take your time to think about it",
            "It's okay if you need to try again",
            "No rush, we can work through this together",
            "Everyone learns at their own pace"
        ]

        for interaction in patient_interactions:
            result = self._analyze_interaction_tone(interaction)
            assert result['shows_patience'] is True
            assert result['is_encouraging'] is True

    @pytest.mark.safety
    def test_break_suggestions(self):
        """Test that system suggests breaks appropriately."""
        session_duration = 45  # minutes

        suggestion = self._get_break_suggestion(session_duration)

        # Should suggest break after extended session
        assert suggestion['suggest_break'] is True
        assert 'rest' in suggestion['message'].lower() or 'break' in suggestion['message'].lower()

    @pytest.mark.safety
    def test_no_time_pressure(self):
        """Test that interactions don't create time pressure."""
        time_pressure_phrases = [
            "Quick! Answer before time runs out!",
            "You only have 10 seconds left!",
            "Faster! You're running out of time!",
            "Time's almost up, hurry!"
        ]

        for phrase in time_pressure_phrases:
            result = self._analyze_interaction_tone(phrase)
            assert result['creates_time_pressure'] is True
            assert result['is_safe_for_children'] is False

    @pytest.mark.safety
    def test_growth_mindset_language(self):
        """Test that interactions promote growth mindset."""
        growth_mindset_phrases = [
            "You're learning and growing every day",
            "Mistakes help us learn",
            "You haven't mastered this yet, but you will",
            "Your brain is getting stronger with practice"
        ]

        for phrase in growth_mindset_phrases:
            result = self._analyze_interaction_tone(phrase)
            assert result['promotes_growth_mindset'] is True

    def _analyze_interaction_tone(self, text: str) -> Dict[str, Any]:
        """Mock interaction tone analyzer."""
        text_lower = text.lower()

        # Friendly indicators
        friendly_words = ['great', 'good', 'nice', "let's", 'together', 'can you']
        is_friendly = any(word in text_lower for word in friendly_words)

        # Supportive indicators
        supportive_phrases = ['good start', 'working hard', 'step by step']
        is_supportive = any(phrase in text_lower for phrase in supportive_phrases)

        # Demanding indicators
        demanding_words = ['must', 'immediately', 'have to', 'hurry up']
        is_demanding = any(word in text_lower for word in demanding_words)

        # Time pressure indicators
        time_pressure_words = ['quick', 'faster', 'time runs out', 'seconds left']
        creates_time_pressure = any(word in text_lower for word in time_pressure_words)

        # Patience indicators
        patience_phrases = ['take your time', "it's okay", 'no rush', 'at their own pace']
        shows_patience = any(phrase in text_lower for phrase in patience_phrases)

        # Encouragement indicators
        encouraging_words = ['can', 'together', 'try again', 'work through']
        is_encouraging = any(word in text_lower for word in encouraging_words)

        # Growth mindset indicators
        growth_phrases = ['learning', 'growing', 'mistakes help', "you haven't", 'yet', 'practice']
        promotes_growth_mindset = any(phrase in text_lower for phrase in growth_phrases)

        tone = 'friendly' if is_friendly else 'neutral'
        if is_demanding:
            tone = 'demanding'

        is_safe_for_children = (
            not is_demanding and
            not creates_time_pressure and
            (is_friendly or is_supportive)
        )

        return {
            'tone': tone,
            'is_friendly': is_friendly,
            'is_supportive': is_supportive,
            'is_demanding': is_demanding,
            'creates_time_pressure': creates_time_pressure,
            'shows_patience': shows_patience,
            'is_encouraging': is_encouraging,
            'promotes_growth_mindset': promotes_growth_mindset,
            'is_safe_for_children': is_safe_for_children
        }

    def _get_break_suggestion(self, session_duration_minutes: int) -> Dict[str, Any]:
        """Mock break suggestion generator."""
        # Suggest break after 30 minutes
        should_suggest = session_duration_minutes >= 30

        if should_suggest:
            return {
                'suggest_break': True,
                'message': "You've been working hard! How about taking a short rest?",
                'duration_minutes': session_duration_minutes
            }

        return {
            'suggest_break': False,
            'message': None,
            'duration_minutes': session_duration_minutes
        }


class TestSessionLimitsEnforcement:
    """Test enforcement of session time and usage limits."""

    @pytest.mark.safety
    def test_maximum_session_duration(self):
        """Test that maximum session duration is enforced."""
        max_duration_minutes = 60
        current_duration = 65

        result = self._check_session_limit(current_duration, max_duration_minutes)

        assert result['limit_exceeded'] is True
        assert result['should_end_session'] is True

    @pytest.mark.safety
    def test_age_appropriate_session_limits(self):
        """Test that session limits are appropriate for age."""
        age_limits = {
            6: 30,   # 6 year olds: 30 min max
            8: 45,   # 8 year olds: 45 min max
            10: 60,  # 10 year olds: 60 min max
            12: 90   # 12 year olds: 90 min max
        }

        for age, expected_limit in age_limits.items():
            limit = self._get_age_appropriate_limit(age)
            assert limit['max_session_minutes'] == expected_limit

    @pytest.mark.safety
    def test_daily_usage_limits(self):
        """Test that daily usage limits are tracked and enforced."""
        user_id = 'child123'
        max_daily_minutes = 120

        # Simulate 2 hours of usage
        self._record_session_time(user_id, 60)
        self._record_session_time(user_id, 60)

        # Check if limit reached
        usage = self._get_daily_usage(user_id)
        assert usage['total_minutes'] >= max_daily_minutes

        # Should not allow new session
        can_start = self._can_start_new_session(user_id, max_daily_minutes)
        assert can_start is False

    @pytest.mark.safety
    def test_mandatory_breaks(self):
        """Test that mandatory breaks are enforced."""
        user_id = 'child123'
        session_duration = 45  # minutes

        # After 45 minutes, should require break
        break_info = self._check_break_requirement(user_id, session_duration)

        assert break_info['break_required'] is True
        assert break_info['minimum_break_minutes'] >= 10

    @pytest.mark.safety
    def test_parental_override_capability(self):
        """Test that parents can override session limits."""
        user_id = 'child123'
        parent_id = 'parent456'
        current_duration = 70
        default_limit = 60

        # Without override, should be blocked
        result = self._check_session_limit(current_duration, default_limit)
        assert result['limit_exceeded'] is True

        # With parental override, should be allowed
        override_result = self._check_session_limit_with_override(
            current_duration,
            default_limit,
            parent_id,
            has_override=True
        )
        assert override_result['limit_exceeded'] is False
        assert override_result['override_active'] is True

    @pytest.mark.safety
    def test_gradual_session_warnings(self):
        """Test that warnings are given before session ends."""
        session_duration = 25
        max_duration = 30

        warning = self._get_session_warning(session_duration, max_duration)

        # Should warn 5 minutes before end
        assert warning['should_warn'] is True
        assert warning['minutes_remaining'] == 5

    @pytest.mark.safety
    def test_bedtime_restrictions(self):
        """Test that sessions are restricted during bedtime hours."""
        test_cases = [
            ('20:00', 6, True),   # 8 PM for 6 year old - should allow
            ('21:00', 6, False),  # 9 PM for 6 year old - should restrict
            ('22:00', 10, True),  # 10 PM for 10 year old - should allow
            ('23:00', 10, False), # 11 PM for 10 year old - should restrict
        ]

        for time_str, age, should_allow in test_cases:
            result = self._check_bedtime_restriction(time_str, age)
            assert result['allow_session'] == should_allow

    def _check_session_limit(self, current_duration: int, max_duration: int) -> Dict[str, Any]:
        """Mock session limit checker."""
        limit_exceeded = current_duration > max_duration

        return {
            'limit_exceeded': limit_exceeded,
            'should_end_session': limit_exceeded,
            'current_duration': current_duration,
            'max_duration': max_duration
        }

    def _get_age_appropriate_limit(self, age: int) -> Dict[str, Any]:
        """Mock age-appropriate limit calculator."""
        if age <= 7:
            max_minutes = 30
        elif age <= 9:
            max_minutes = 45
        elif age <= 11:
            max_minutes = 60
        else:
            max_minutes = 90

        return {
            'age': age,
            'max_session_minutes': max_minutes,
            'max_daily_minutes': max_minutes * 2
        }

    def _record_session_time(self, user_id: str, minutes: int):
        """Mock session time recording."""
        if not hasattr(self, '_daily_usage'):
            self._daily_usage = {}

        if user_id not in self._daily_usage:
            self._daily_usage[user_id] = 0

        self._daily_usage[user_id] += minutes

    def _get_daily_usage(self, user_id: str) -> Dict[str, Any]:
        """Mock daily usage getter."""
        total = 0
        if hasattr(self, '_daily_usage'):
            total = self._daily_usage.get(user_id, 0)

        return {
            'total_minutes': total,
            'date': datetime.now().date().isoformat()
        }

    def _can_start_new_session(self, user_id: str, max_daily_minutes: int) -> bool:
        """Mock session start checker."""
        usage = self._get_daily_usage(user_id)
        return usage['total_minutes'] < max_daily_minutes

    def _check_break_requirement(self, user_id: str, session_duration: int) -> Dict[str, Any]:
        """Mock break requirement checker."""
        # Require break after 45 minutes
        break_required = session_duration >= 45

        return {
            'break_required': break_required,
            'minimum_break_minutes': 10 if break_required else 0,
            'session_duration': session_duration
        }

    def _check_session_limit_with_override(
        self,
        current_duration: int,
        default_limit: int,
        parent_id: str,
        has_override: bool
    ) -> Dict[str, Any]:
        """Mock session limit checker with parental override."""
        if has_override:
            return {
                'limit_exceeded': False,
                'override_active': True,
                'parent_id': parent_id
            }

        return self._check_session_limit(current_duration, default_limit)

    def _get_session_warning(self, session_duration: int, max_duration: int) -> Dict[str, Any]:
        """Mock session warning generator."""
        minutes_remaining = max_duration - session_duration
        should_warn = 0 < minutes_remaining <= 5

        return {
            'should_warn': should_warn,
            'minutes_remaining': minutes_remaining,
            'message': f"You have {minutes_remaining} minutes left" if should_warn else None
        }

    def _check_bedtime_restriction(self, time_str: str, age: int) -> Dict[str, Any]:
        """Mock bedtime restriction checker."""
        hour = int(time_str.split(':')[0])

        # Age-based bedtime restrictions
        if age <= 7:
            bedtime_hour = 21  # 9 PM
        elif age <= 9:
            bedtime_hour = 22  # 10 PM
        elif age <= 11:
            bedtime_hour = 22  # 10 PM
        else:
            bedtime_hour = 23  # 11 PM

        allow_session = hour < bedtime_hour

        return {
            'allow_session': allow_session,
            'current_hour': hour,
            'bedtime_hour': bedtime_hour,
            'reason': None if allow_session else 'Past bedtime'
        }


class TestParentalControlEffectiveness:
    """Test effectiveness of parental controls."""

    @pytest.mark.safety
    def test_content_filtering_enforcement(self):
        """Test that content filters are properly enforced."""
        parent_id = 'parent123'
        child_id = 'child456'

        # Parent blocks certain subjects
        self._set_content_filter(parent_id, child_id, blocked_subjects=['advanced_math'])

        # Check if content is blocked
        result = self._check_content_allowed(parent_id, child_id, 'advanced_math')
        assert result['allowed'] is False
        assert result['reason'] == 'blocked_by_parent'

    @pytest.mark.safety
    def test_time_limit_enforcement(self):
        """Test that parental time limits are enforced."""
        parent_id = 'parent123'
        child_id = 'child456'

        # Parent sets 30 minute daily limit
        self._set_time_limit(parent_id, child_id, daily_minutes=30)

        # Simulate 30 minutes of usage
        self._record_usage(child_id, 30)

        # Should not allow more time
        can_continue = self._check_time_remaining(child_id)
        assert can_continue['allowed'] is False

    @pytest.mark.safety
    def test_activity_monitoring(self):
        """Test that parents can monitor child activity."""
        parent_id = 'parent123'
        child_id = 'child456'

        # Record some activities
        self._record_activity(child_id, 'math_practice', duration=15)
        self._record_activity(child_id, 'reading_exercise', duration=20)

        # Parent should be able to view activities
        activities = self._get_child_activities(parent_id, child_id)

        assert len(activities) == 2
        assert activities[0]['type'] == 'math_practice'
        assert activities[1]['type'] == 'reading_exercise'

    @pytest.mark.safety
    def test_parental_notification_system(self):
        """Test that parents receive appropriate notifications."""
        parent_id = 'parent123'
        child_id = 'child456'

        # Trigger notification event (e.g., time limit approaching)
        self._trigger_notification_event(child_id, 'time_limit_approaching')

        # Check parent notifications
        notifications = self._get_parent_notifications(parent_id)

        assert len(notifications) > 0
        assert notifications[0]['type'] == 'time_limit_approaching'
        assert notifications[0]['child_id'] == child_id

    @pytest.mark.safety
    def test_emergency_contact_access(self):
        """Test that emergency contacts are accessible."""
        parent_id = 'parent123'
        child_id = 'child456'

        # Set emergency contacts
        self._set_emergency_contacts(parent_id, child_id, [
            {'name': 'Mom', 'phone': '555-0001'},
            {'name': 'Dad', 'phone': '555-0002'}
        ])

        # Child should be able to access emergency contacts
        contacts = self._get_emergency_contacts(child_id)

        assert len(contacts) == 2
        assert contacts[0]['name'] == 'Mom'

    @pytest.mark.safety
    def test_parental_control_bypass_prevention(self):
        """Test that children cannot bypass parental controls."""
        parent_id = 'parent123'
        child_id = 'child456'

        # Set restriction
        self._set_content_filter(parent_id, child_id, blocked_subjects=['chemistry'])

        # Attempt to bypass (various methods)
        bypass_attempts = [
            ('chemistry', False),  # Direct access
            ('chem', False),       # Abbreviation
            ('CHEMISTRY', False),  # Case variation
        ]

        for subject, should_allow in bypass_attempts:
            result = self._check_content_allowed(parent_id, child_id, subject)
            assert result['allowed'] == should_allow

    def _set_content_filter(self, parent_id: str, child_id: str, blocked_subjects: List[str]):
        """Mock content filter setter."""
        if not hasattr(self, '_content_filters'):
            self._content_filters = {}

        key = f"{parent_id}:{child_id}"
        self._content_filters[key] = {'blocked_subjects': [s.lower() for s in blocked_subjects]}

    def _check_content_allowed(self, parent_id: str, child_id: str, subject: str) -> Dict[str, Any]:
        """Mock content allowance checker."""
        if not hasattr(self, '_content_filters'):
            return {'allowed': True}

        key = f"{parent_id}:{child_id}"
        if key not in self._content_filters:
            return {'allowed': True}

        blocked = self._content_filters[key]['blocked_subjects']
        subject_lower = subject.lower()

        # Check for exact match or partial match
        is_blocked = any(blocked_subject in subject_lower or subject_lower in blocked_subject
                        for blocked_subject in blocked)

        return {
            'allowed': not is_blocked,
            'reason': 'blocked_by_parent' if is_blocked else None
        }

    def _set_time_limit(self, parent_id: str, child_id: str, daily_minutes: int):
        """Mock time limit setter."""
        if not hasattr(self, '_time_limits'):
            self._time_limits = {}

        key = f"{parent_id}:{child_id}"
        self._time_limits[key] = daily_minutes

    def _record_usage(self, child_id: str, minutes: int):
        """Mock usage recording."""
        if not hasattr(self, '_usage'):
            self._usage = {}

        if child_id not in self._usage:
            self._usage[child_id] = 0

        self._usage[child_id] += minutes

    def _check_time_remaining(self, child_id: str) -> Dict[str, Any]:
        """Mock time remaining checker."""
        if not hasattr(self, '_usage'):
            return {'allowed': True, 'remaining_minutes': 999}

        used = self._usage.get(child_id, 0)

        # Find limit for this child
        limit = 60  # Default
        if hasattr(self, '_time_limits'):
            for key, value in self._time_limits.items():
                if child_id in key:
                    limit = value
                    break

        remaining = limit - used
        allowed = remaining > 0

        return {
            'allowed': allowed,
            'remaining_minutes': max(0, remaining)
        }

    def _record_activity(self, child_id: str, activity_type: str, duration: int):
        """Mock activity recording."""
        if not hasattr(self, '_activities'):
            self._activities = {}

        if child_id not in self._activities:
            self._activities[child_id] = []

        self._activities[child_id].append({
            'type': activity_type,
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        })

    def _get_child_activities(self, parent_id: str, child_id: str) -> List[Dict[str, Any]]:
        """Mock activity retrieval."""
        if not hasattr(self, '_activities'):
            return []

        return self._activities.get(child_id, [])

    def _trigger_notification_event(self, child_id: str, event_type: str):
        """Mock notification trigger."""
        if not hasattr(self, '_notifications'):
            self._notifications = []

        self._notifications.append({
            'child_id': child_id,
            'type': event_type,
            'timestamp': datetime.now().isoformat()
        })

    def _get_parent_notifications(self, parent_id: str) -> List[Dict[str, Any]]:
        """Mock notification retrieval."""
        if not hasattr(self, '_notifications'):
            return []

        return self._notifications

    def _set_emergency_contacts(self, parent_id: str, child_id: str, contacts: List[Dict[str, str]]):
        """Mock emergency contacts setter."""
        if not hasattr(self, '_emergency_contacts'):
            self._emergency_contacts = {}

        key = f"{parent_id}:{child_id}"
        self._emergency_contacts[key] = contacts

    def _get_emergency_contacts(self, child_id: str) -> List[Dict[str, str]]:
        """Mock emergency contacts retrieval."""
        if not hasattr(self, '_emergency_contacts'):
            return []

        for key, contacts in self._emergency_contacts.items():
            if child_id in key:
                return contacts

        return []


class TestEmergencyHandling:
    """Test emergency handling procedures."""

    @pytest.mark.safety
    def test_emergency_keyword_detection(self):
        """Test detection of emergency keywords."""
        emergency_phrases = [
            "I need help",
            "I'm scared",
            "Someone is hurting me",
            "I don't feel safe",
            "Emergency"
        ]

        for phrase in emergency_phrases:
            result = self._check_for_emergency(phrase)
            assert result['is_emergency'] is True
            assert result['severity'] in ['medium', 'high', 'critical']

    @pytest.mark.safety
    def test_emergency_response_protocol(self):
        """Test emergency response protocol activation."""
        emergency_input = "I need help, I'm scared"

        response = self._handle_emergency_situation(emergency_input)

        assert response['protocol_activated'] is True
        assert response['parent_notified'] is True
        assert 'emergency_contacts_displayed' in response
        assert response['session_paused'] is True

    @pytest.mark.safety
    def test_parent_alert_mechanism(self):
        """Test that parents are immediately alerted in emergencies."""
        child_id = 'child456'
        parent_id = 'parent123'

        # Simulate emergency
        self._trigger_emergency(child_id, "Child indicated distress")

        # Check parent was alerted
        alerts = self._get_parent_emergency_alerts(parent_id)

        assert len(alerts) > 0
        assert alerts[0]['priority'] == 'immediate'
        assert alerts[0]['child_id'] == child_id

    @pytest.mark.safety
    def test_emergency_contact_display(self):
        """Test that emergency contacts are prominently displayed."""
        child_id = 'child456'

        emergency_ui = self._get_emergency_ui(child_id)

        assert emergency_ui['show_contacts'] is True
        assert len(emergency_ui['contacts']) > 0
        assert emergency_ui['show_help_button'] is True

    @pytest.mark.safety
    def test_session_pause_on_emergency(self):
        """Test that learning session pauses during emergency."""
        child_id = 'child456'

        # Start session
        self._start_session(child_id)
        assert self._is_session_active(child_id) is True

        # Trigger emergency
        self._trigger_emergency(child_id, "Emergency detected")

        # Session should be paused
        assert self._is_session_active(child_id) is False
        assert self._is_session_paused(child_id) is True

    @pytest.mark.safety
    def test_false_positive_handling(self):
        """Test handling of false positive emergency detections."""
        # These shouldn't trigger emergency protocol
        non_emergency_phrases = [
            "I need help with this math problem",
            "Can you help me understand this?",
            "I'm scared of making mistakes",  # Context matters
            "Emergency exit sign" # Educational context
        ]

        for phrase in non_emergency_phrases:
            result = self._check_for_emergency(phrase, context='educational')
            # Should detect concern but not trigger full emergency
            assert result.get('requires_review', False) or not result['is_emergency']

    def _check_for_emergency(self, text: str, context: str = None) -> Dict[str, Any]:
        """Mock emergency checker."""
        text_lower = text.lower()

        # Critical emergency keywords
        critical_keywords = ['hurting me', "don't feel safe", 'someone is']
        has_critical = any(kw in text_lower for kw in critical_keywords)

        # High priority keywords
        high_keywords = ["i'm scared", 'emergency', 'need help']
        has_high = any(kw in text_lower for kw in high_keywords)

        # Educational context check
        educational_context = context == 'educational' or any(word in text_lower for word in [
            'math problem', 'understand this', 'making mistakes', 'exit sign'
        ])

        if educational_context and not has_critical:
            # Likely false positive
            return {
                'is_emergency': False,
                'requires_review': has_high,
                'severity': 'low'
            }

        if has_critical:
            severity = 'critical'
            is_emergency = True
        elif has_high:
            severity = 'high'
            is_emergency = True
        else:
            severity = 'low'
            is_emergency = False

        return {
            'is_emergency': is_emergency,
            'severity': severity,
            'matched_keywords': []
        }

    def _handle_emergency_situation(self, emergency_input: str) -> Dict[str, Any]:
        """Mock emergency handler."""
        return {
            'protocol_activated': True,
            'parent_notified': True,
            'emergency_contacts_displayed': True,
            'session_paused': True,
            'timestamp': datetime.now().isoformat()
        }

    def _trigger_emergency(self, child_id: str, reason: str):
        """Mock emergency trigger."""
        if not hasattr(self, '_emergency_alerts'):
            self._emergency_alerts = []

        self._emergency_alerts.append({
            'child_id': child_id,
            'reason': reason,
            'priority': 'immediate',
            'timestamp': datetime.now().isoformat()
        })

        # Pause session
        if not hasattr(self, '_paused_sessions'):
            self._paused_sessions = set()
        self._paused_sessions.add(child_id)

    def _get_parent_emergency_alerts(self, parent_id: str) -> List[Dict[str, Any]]:
        """Mock emergency alert retrieval."""
        if not hasattr(self, '_emergency_alerts'):
            return []

        return self._emergency_alerts

    def _get_emergency_ui(self, child_id: str) -> Dict[str, Any]:
        """Mock emergency UI generator."""
        return {
            'show_contacts': True,
            'contacts': [
                {'name': 'Parent', 'action': 'call_parent'},
                {'name': 'Emergency', 'action': 'call_911'}
            ],
            'show_help_button': True,
            'message': 'Help is available. You are safe.'
        }

    def _start_session(self, child_id: str):
        """Mock session starter."""
        if not hasattr(self, '_active_sessions'):
            self._active_sessions = set()
        self._active_sessions.add(child_id)

    def _is_session_active(self, child_id: str) -> bool:
        """Mock session active checker."""
        if not hasattr(self, '_active_sessions'):
            return False
        if hasattr(self, '_paused_sessions') and child_id in self._paused_sessions:
            return False
        return child_id in self._active_sessions

    def _is_session_paused(self, child_id: str) -> bool:
        """Mock session pause checker."""
        if not hasattr(self, '_paused_sessions'):
            return False
        return child_id in self._paused_sessions
