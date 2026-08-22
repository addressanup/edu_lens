"""
Content Filter for EduLens Parental Controls

Manages content filtering based on subject, difficulty, and content type.
"""

import json
import logging
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class FilterMode(Enum):
    """Filtering modes"""

    WHITELIST = "whitelist"  # Only allow specified items
    BLACKLIST = "blacklist"  # Block specified items
    UNRESTRICTED = "unrestricted"  # No filtering


class DifficultyLevel(Enum):
    """Content difficulty levels"""

    ELEMENTARY = 1
    MIDDLE_SCHOOL = 2
    HIGH_SCHOOL = 3
    COLLEGE = 4
    ADVANCED = 5


class ContentType(Enum):
    """Types of educational content"""

    MULTIPLE_CHOICE = "multiple_choice"
    FREE_RESPONSE = "free_response"
    ESSAY = "essay"
    MATH_PROBLEM = "math_problem"
    CODING_EXERCISE = "coding_exercise"
    VIDEO = "video"
    READING = "reading"
    INTERACTIVE = "interactive"


class AgeGroup(Enum):
    """Age-based content groups"""

    AGES_5_7 = "5-7"
    AGES_8_10 = "8-10"
    AGES_11_13 = "11-13"
    AGES_14_16 = "14-16"
    AGES_17_PLUS = "17+"


class ContentFilter:
    """
    Manages content filtering for parental controls.

    Features:
    - Subject-based filtering (whitelist/blacklist)
    - Difficulty level restrictions
    - Content type filtering
    - Age-appropriate defaults
    - Flexible allow/block rules
    """

    def __init__(self, user_id: str, storage_path: Optional[Path] = None):
        """
        Initialize ContentFilter.

        Args:
            user_id: Unique identifier for the user
            storage_path: Path to store filter settings
        """
        self.user_id = user_id
        self.storage_path = storage_path or Path(f"/tmp/edulens/filters/{user_id}")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Subject filtering
        self.subject_mode: FilterMode = FilterMode.UNRESTRICTED
        self.allowed_subjects: Set[str] = set()
        self.blocked_subjects: Set[str] = set()

        # Difficulty filtering
        self.min_difficulty: Optional[DifficultyLevel] = None
        self.max_difficulty: Optional[DifficultyLevel] = None

        # Content type filtering
        self.content_type_mode: FilterMode = FilterMode.UNRESTRICTED
        self.allowed_content_types: Set[ContentType] = set()
        self.blocked_content_types: Set[ContentType] = set()

        # Keywords filtering
        self.blocked_keywords: Set[str] = set()

        # Custom rules
        self.custom_rules: List[Dict] = []

        self._load_state()

    def filter_subjects(self, mode: FilterMode, subjects: Optional[List[str]] = None) -> None:
        """
        Configure subject filtering.

        Args:
            mode: Filter mode (whitelist, blacklist, or unrestricted)
            subjects: List of subjects (required for whitelist/blacklist modes)

        Raises:
            ValueError: If subjects not provided for whitelist/blacklist mode
        """
        if mode in [FilterMode.WHITELIST, FilterMode.BLACKLIST] and not subjects:
            raise ValueError(f"{mode.value} mode requires a list of subjects")

        self.subject_mode = mode

        if mode == FilterMode.WHITELIST:
            self.allowed_subjects = set(s.lower() for s in subjects)
            self.blocked_subjects = set()
            logger.info(f"Set subject whitelist for user {self.user_id}: {self.allowed_subjects}")
        elif mode == FilterMode.BLACKLIST:
            self.blocked_subjects = set(s.lower() for s in subjects)
            self.allowed_subjects = set()
            logger.info(f"Set subject blacklist for user {self.user_id}: {self.blocked_subjects}")
        else:
            self.allowed_subjects = set()
            self.blocked_subjects = set()
            logger.info(f"Removed subject restrictions for user {self.user_id}")

        self._save_state()

    def add_allowed_subject(self, subject: str) -> None:
        """Add a subject to the whitelist."""
        if self.subject_mode != FilterMode.WHITELIST:
            self.subject_mode = FilterMode.WHITELIST

        self.allowed_subjects.add(subject.lower())
        logger.info(f"Added allowed subject '{subject}' for user {self.user_id}")
        self._save_state()

    def add_blocked_subject(self, subject: str) -> None:
        """Add a subject to the blacklist."""
        if self.subject_mode != FilterMode.BLACKLIST:
            self.subject_mode = FilterMode.BLACKLIST

        self.blocked_subjects.add(subject.lower())
        logger.info(f"Added blocked subject '{subject}' for user {self.user_id}")
        self._save_state()

    def filter_difficulty(
        self,
        min_level: Optional[DifficultyLevel] = None,
        max_level: Optional[DifficultyLevel] = None,
    ) -> None:
        """
        Set difficulty level restrictions.

        Args:
            min_level: Minimum allowed difficulty (None = no minimum)
            max_level: Maximum allowed difficulty (None = no maximum)

        Raises:
            ValueError: If min_level > max_level
        """
        if min_level and max_level and min_level.value > max_level.value:
            raise ValueError("Minimum difficulty cannot exceed maximum difficulty")

        self.min_difficulty = min_level
        self.max_difficulty = max_level

        logger.info(
            f"Set difficulty range for user {self.user_id}: "
            f"{min_level.name if min_level else 'None'} to "
            f"{max_level.name if max_level else 'None'}"
        )
        self._save_state()

    def filter_content_type(
        self, mode: FilterMode, content_types: Optional[List[ContentType]] = None
    ) -> None:
        """
        Configure content type filtering.

        Args:
            mode: Filter mode (whitelist, blacklist, or unrestricted)
            content_types: List of content types

        Raises:
            ValueError: If content_types not provided for whitelist/blacklist mode
        """
        if mode in [FilterMode.WHITELIST, FilterMode.BLACKLIST] and not content_types:
            raise ValueError(f"{mode.value} mode requires a list of content types")

        self.content_type_mode = mode

        if mode == FilterMode.WHITELIST:
            self.allowed_content_types = set(content_types)
            self.blocked_content_types = set()
            logger.info(f"Set content type whitelist for user {self.user_id}")
        elif mode == FilterMode.BLACKLIST:
            self.blocked_content_types = set(content_types)
            self.allowed_content_types = set()
            logger.info(f"Set content type blacklist for user {self.user_id}")
        else:
            self.allowed_content_types = set()
            self.blocked_content_types = set()
            logger.info(f"Removed content type restrictions for user {self.user_id}")

        self._save_state()

    def add_blocked_keyword(self, keyword: str) -> None:
        """
        Add a keyword to block in content.

        Args:
            keyword: Keyword to block
        """
        self.blocked_keywords.add(keyword.lower())
        logger.info(f"Added blocked keyword '{keyword}' for user {self.user_id}")
        self._save_state()

    def remove_blocked_keyword(self, keyword: str) -> None:
        """
        Remove a keyword from the block list.

        Args:
            keyword: Keyword to unblock
        """
        self.blocked_keywords.discard(keyword.lower())
        logger.info(f"Removed blocked keyword '{keyword}' for user {self.user_id}")
        self._save_state()

    def check_content(
        self,
        subject: Optional[str] = None,
        difficulty: Optional[DifficultyLevel] = None,
        content_type: Optional[ContentType] = None,
        keywords: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if content is allowed based on current filters.

        Args:
            subject: Subject of the content
            difficulty: Difficulty level
            content_type: Type of content
            keywords: List of keywords in the content
            metadata: Additional metadata for custom rules

        Returns:
            Tuple of (is_allowed, reason_if_blocked)
        """
        # Check subject filter
        if subject:
            subject_lower = subject.lower()

            if self.subject_mode == FilterMode.WHITELIST:
                if subject_lower not in self.allowed_subjects:
                    return False, f"Subject '{subject}' is not in allowed list"
            elif self.subject_mode == FilterMode.BLACKLIST:
                if subject_lower in self.blocked_subjects:
                    return False, f"Subject '{subject}' is blocked"

        # Check difficulty filter
        if difficulty:
            if self.min_difficulty and difficulty.value < self.min_difficulty.value:
                return False, f"Content too easy (below {self.min_difficulty.name})"
            if self.max_difficulty and difficulty.value > self.max_difficulty.value:
                return False, f"Content too difficult (above {self.max_difficulty.name})"

        # Check content type filter
        if content_type:
            if self.content_type_mode == FilterMode.WHITELIST:
                if content_type not in self.allowed_content_types:
                    return False, f"Content type '{content_type.value}' is not allowed"
            elif self.content_type_mode == FilterMode.BLACKLIST:
                if content_type in self.blocked_content_types:
                    return False, f"Content type '{content_type.value}' is blocked"

        # Check blocked keywords
        if keywords:
            keywords_lower = [k.lower() for k in keywords]
            for blocked in self.blocked_keywords:
                if any(blocked in kw for kw in keywords_lower):
                    return False, f"Content contains blocked keyword"

        # Check custom rules
        for rule in self.custom_rules:
            if not self._evaluate_custom_rule(rule, subject, difficulty, content_type, metadata):
                return False, rule.get("reason", "Custom rule violation")

        return True, None

    def add_custom_rule(self, rule_name: str, condition: Dict, reason: str) -> None:
        """
        Add a custom filtering rule.

        Args:
            rule_name: Name of the rule
            condition: Dictionary defining the rule condition
            reason: Reason shown when content is blocked
        """
        rule = {"name": rule_name, "condition": condition, "reason": reason}
        self.custom_rules.append(rule)
        logger.info(f"Added custom rule '{rule_name}' for user {self.user_id}")
        self._save_state()

    def remove_custom_rule(self, rule_name: str) -> bool:
        """
        Remove a custom rule by name.

        Args:
            rule_name: Name of the rule to remove

        Returns:
            True if rule was found and removed
        """
        original_length = len(self.custom_rules)
        self.custom_rules = [r for r in self.custom_rules if r["name"] != rule_name]

        if len(self.custom_rules) < original_length:
            logger.info(f"Removed custom rule '{rule_name}' for user {self.user_id}")
            self._save_state()
            return True
        return False

    def set_age_appropriate_defaults(self, age_group: AgeGroup) -> None:
        """
        Set age-appropriate default filters.

        Args:
            age_group: Age group for default settings
        """
        logger.info(
            f"Setting age-appropriate defaults for {age_group.value} for user {self.user_id}"
        )

        if age_group == AgeGroup.AGES_5_7:
            self.filter_difficulty(max_level=DifficultyLevel.ELEMENTARY)
            self.filter_content_type(
                FilterMode.WHITELIST,
                [ContentType.MULTIPLE_CHOICE, ContentType.INTERACTIVE, ContentType.VIDEO],
            )

        elif age_group == AgeGroup.AGES_8_10:
            self.filter_difficulty(max_level=DifficultyLevel.MIDDLE_SCHOOL)
            self.filter_content_type(
                FilterMode.WHITELIST,
                [
                    ContentType.MULTIPLE_CHOICE,
                    ContentType.FREE_RESPONSE,
                    ContentType.MATH_PROBLEM,
                    ContentType.INTERACTIVE,
                    ContentType.VIDEO,
                    ContentType.READING,
                ],
            )

        elif age_group == AgeGroup.AGES_11_13:
            self.filter_difficulty(max_level=DifficultyLevel.HIGH_SCHOOL)
            self.filter_content_type(FilterMode.UNRESTRICTED)

        elif age_group == AgeGroup.AGES_14_16:
            self.filter_difficulty(max_level=DifficultyLevel.COLLEGE)
            self.filter_content_type(FilterMode.UNRESTRICTED)

        else:  # AGES_17_PLUS
            self.filter_difficulty()  # No restrictions
            self.filter_content_type(FilterMode.UNRESTRICTED)

        self._save_state()

    def reset_all_filters(self) -> None:
        """Reset all filters to unrestricted."""
        self.subject_mode = FilterMode.UNRESTRICTED
        self.allowed_subjects = set()
        self.blocked_subjects = set()
        self.min_difficulty = None
        self.max_difficulty = None
        self.content_type_mode = FilterMode.UNRESTRICTED
        self.allowed_content_types = set()
        self.blocked_content_types = set()
        self.blocked_keywords = set()
        self.custom_rules = []

        logger.info(f"Reset all filters for user {self.user_id}")
        self._save_state()

    def get_filter_summary(self) -> Dict:
        """
        Get summary of current filter settings.

        Returns:
            Dictionary with filter configuration
        """
        return {
            "user_id": self.user_id,
            "subject_filter": {
                "mode": self.subject_mode.value,
                "allowed": list(self.allowed_subjects),
                "blocked": list(self.blocked_subjects),
            },
            "difficulty_filter": {
                "min": self.min_difficulty.name if self.min_difficulty else None,
                "max": self.max_difficulty.name if self.max_difficulty else None,
            },
            "content_type_filter": {
                "mode": self.content_type_mode.value,
                "allowed": [ct.value for ct in self.allowed_content_types],
                "blocked": [ct.value for ct in self.blocked_content_types],
            },
            "blocked_keywords": list(self.blocked_keywords),
            "custom_rules": [r["name"] for r in self.custom_rules],
        }

    def _evaluate_custom_rule(
        self,
        rule: Dict,
        subject: Optional[str],
        difficulty: Optional[DifficultyLevel],
        content_type: Optional[ContentType],
        metadata: Optional[Dict],
    ) -> bool:
        """
        Evaluate a custom rule against content.

        Returns:
            True if content passes the rule (is allowed)
        """
        # Simple rule evaluation - can be extended
        condition = rule.get("condition", {})

        # This is a placeholder for more complex rule evaluation
        # In production, you might use a rule engine
        return True

    def _save_state(self) -> None:
        """Save filter state to disk."""
        state = {
            "subject_mode": self.subject_mode.value,
            "allowed_subjects": list(self.allowed_subjects),
            "blocked_subjects": list(self.blocked_subjects),
            "min_difficulty": self.min_difficulty.value if self.min_difficulty else None,
            "max_difficulty": self.max_difficulty.value if self.max_difficulty else None,
            "content_type_mode": self.content_type_mode.value,
            "allowed_content_types": [ct.value for ct in self.allowed_content_types],
            "blocked_content_types": [ct.value for ct in self.blocked_content_types],
            "blocked_keywords": list(self.blocked_keywords),
            "custom_rules": self.custom_rules,
        }

        state_file = self.storage_path / "filter_state.json"
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

    def _load_state(self) -> None:
        """Load filter state from disk."""
        state_file = self.storage_path / "filter_state.json"

        if not state_file.exists():
            return

        try:
            with open(state_file, "r") as f:
                state = json.load(f)

            self.subject_mode = FilterMode(state.get("subject_mode", "unrestricted"))
            self.allowed_subjects = set(state.get("allowed_subjects", []))
            self.blocked_subjects = set(state.get("blocked_subjects", []))

            min_diff = state.get("min_difficulty")
            self.min_difficulty = DifficultyLevel(min_diff) if min_diff else None

            max_diff = state.get("max_difficulty")
            self.max_difficulty = DifficultyLevel(max_diff) if max_diff else None

            self.content_type_mode = FilterMode(state.get("content_type_mode", "unrestricted"))
            self.allowed_content_types = {
                ContentType(ct) for ct in state.get("allowed_content_types", [])
            }
            self.blocked_content_types = {
                ContentType(ct) for ct in state.get("blocked_content_types", [])
            }

            self.blocked_keywords = set(state.get("blocked_keywords", []))
            self.custom_rules = state.get("custom_rules", [])

            logger.info(f"Loaded filter state for user {self.user_id}")
        except Exception as e:
            logger.error(f"Error loading filter state for user {self.user_id}: {e}")
