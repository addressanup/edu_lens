"""
Token Counter for Claude Agents Orchestration System.

This module provides token estimation and tracking functionality
compatible with Claude's tokenization.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class TokenUsage:
    """Token usage record."""

    agent_name: str
    phase: int
    input_tokens: int
    output_tokens: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "phase": self.phase,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "timestamp": self.timestamp.isoformat(),
        }


class TokenCounter:
    """
    Token estimation and tracking utility.

    Provides Claude-compatible token estimation using a character/word-based
    heuristic. Actual token counts may vary slightly from Claude's tokenizer.

    Example:
        counter = TokenCounter()

        # Estimate tokens
        tokens = counter.estimate_tokens("Hello, world!")

        # Track usage
        counter.track_usage(
            agent_name="ConceptDesigner",
            phase=1,
            input_tokens=1000,
            output_tokens=500
        )

        # Get statistics
        stats = counter.get_statistics()
    """

    # Average characters per token for English text
    CHARS_PER_TOKEN = 4.0

    # Multipliers for different content types
    MULTIPLIERS = {
        "code": 0.8,  # Code tends to have more tokens per character
        "json": 0.7,  # JSON has lots of brackets/quotes
        "markdown": 0.9,  # Markdown is mostly text
        "text": 1.0,  # Plain text baseline
    }

    def __init__(self):
        """Initialize the token counter."""
        self._usage_history: List[TokenUsage] = []
        self._budget: Optional[int] = None

    def estimate_tokens(
        self,
        text: str,
        content_type: str = "text",
    ) -> int:
        """
        Estimate token count for text.

        Uses a heuristic based on character count and content type.
        Claude's actual tokenizer may produce slightly different counts.

        Args:
            text: Text to estimate tokens for
            content_type: Type of content (code, json, markdown, text)

        Returns:
            Estimated token count
        """
        if not text:
            return 0

        # Get content type multiplier
        multiplier = self.MULTIPLIERS.get(content_type, 1.0)

        # Base estimation on characters
        char_count = len(text)
        base_tokens = char_count / self.CHARS_PER_TOKEN

        # Adjust for content type
        estimated = int(base_tokens * multiplier)

        # Account for special tokens (newlines, etc.)
        newlines = text.count("\n")
        special_chars = len(re.findall(r"[{}[\]()<>]", text))

        # Add overhead for structural characters
        estimated += int(newlines * 0.5)
        estimated += int(special_chars * 0.3)

        return max(1, estimated)

    def estimate_tokens_detailed(
        self,
        text: str,
    ) -> Dict[str, Any]:
        """
        Estimate tokens with detailed breakdown.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with token estimation details
        """
        if not text:
            return {
                "total_tokens": 0,
                "char_count": 0,
                "word_count": 0,
                "line_count": 0,
                "content_type": "empty",
            }

        # Detect content type
        content_type = self._detect_content_type(text)

        # Calculate metrics
        char_count = len(text)
        word_count = len(text.split())
        line_count = text.count("\n") + 1

        # Estimate tokens
        tokens = self.estimate_tokens(text, content_type)

        return {
            "total_tokens": tokens,
            "char_count": char_count,
            "word_count": word_count,
            "line_count": line_count,
            "content_type": content_type,
            "chars_per_token": char_count / tokens if tokens > 0 else 0,
            "words_per_token": word_count / tokens if tokens > 0 else 0,
        }

    def _detect_content_type(self, text: str) -> str:
        """Detect the type of content."""
        # Check for JSON
        if text.strip().startswith("{") or text.strip().startswith("["):
            return "json"

        # Check for code indicators
        code_patterns = [
            r"def\s+\w+\(",  # Python function
            r"function\s+\w+\(",  # JavaScript function
            r"class\s+\w+",  # Class definition
            r"import\s+\w+",  # Import statement
            r"const\s+\w+\s*=",  # JS const
            r"let\s+\w+\s*=",  # JS let
        ]
        for pattern in code_patterns:
            if re.search(pattern, text):
                return "code"

        # Check for markdown
        md_patterns = [
            r"^#+\s",  # Headers
            r"^\s*[-*]\s",  # Lists
            r"```",  # Code blocks
            r"\[.*\]\(.*\)",  # Links
        ]
        for pattern in md_patterns:
            if re.search(pattern, text, re.MULTILINE):
                return "markdown"

        return "text"

    def track_usage(
        self,
        agent_name: str,
        phase: int,
        input_tokens: int,
        output_tokens: int,
    ) -> TokenUsage:
        """
        Track token usage for an agent.

        Args:
            agent_name: Name of the agent
            phase: Current phase
            input_tokens: Input tokens used
            output_tokens: Output tokens generated

        Returns:
            TokenUsage record
        """
        usage = TokenUsage(
            agent_name=agent_name,
            phase=phase,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        self._usage_history.append(usage)
        return usage

    def set_budget(self, total_tokens: int) -> None:
        """Set the total token budget."""
        self._budget = total_tokens

    def get_remaining_budget(self) -> Optional[int]:
        """Get remaining token budget."""
        if self._budget is None:
            return None

        used = self.get_total_tokens_used()
        return max(0, self._budget - used)

    def get_total_tokens_used(self) -> int:
        """Get total tokens used across all agents."""
        return sum(u.total_tokens for u in self._usage_history)

    def get_usage_by_agent(self, agent_name: str) -> Dict[str, int]:
        """Get token usage for a specific agent."""
        agent_usage = [u for u in self._usage_history if u.agent_name == agent_name]

        return {
            "input_tokens": sum(u.input_tokens for u in agent_usage),
            "output_tokens": sum(u.output_tokens for u in agent_usage),
            "total_tokens": sum(u.total_tokens for u in agent_usage),
            "invocations": len(agent_usage),
        }

    def get_usage_by_phase(self, phase: int) -> Dict[str, int]:
        """Get token usage for a specific phase."""
        phase_usage = [u for u in self._usage_history if u.phase == phase]

        return {
            "input_tokens": sum(u.input_tokens for u in phase_usage),
            "output_tokens": sum(u.output_tokens for u in phase_usage),
            "total_tokens": sum(u.total_tokens for u in phase_usage),
            "agents": len(set(u.agent_name for u in phase_usage)),
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive token usage statistics."""
        if not self._usage_history:
            return {
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "invocations": 0,
                "budget": self._budget,
                "remaining": self._budget,
                "by_agent": {},
                "by_phase": {},
            }

        # Aggregate by agent
        agents = set(u.agent_name for u in self._usage_history)
        by_agent = {agent: self.get_usage_by_agent(agent) for agent in agents}

        # Aggregate by phase
        phases = set(u.phase for u in self._usage_history)
        by_phase = {phase: self.get_usage_by_phase(phase) for phase in phases}

        total_input = sum(u.input_tokens for u in self._usage_history)
        total_output = sum(u.output_tokens for u in self._usage_history)

        return {
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "invocations": len(self._usage_history),
            "budget": self._budget,
            "remaining": self.get_remaining_budget(),
            "by_agent": by_agent,
            "by_phase": by_phase,
        }

    def is_over_budget(self) -> bool:
        """Check if token usage exceeds budget."""
        if self._budget is None:
            return False
        return self.get_total_tokens_used() > self._budget

    def clear_history(self) -> None:
        """Clear usage history."""
        self._usage_history.clear()

    def get_history(self) -> List[TokenUsage]:
        """Get usage history."""
        return self._usage_history.copy()
