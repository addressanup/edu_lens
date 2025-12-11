"""
Context Budget Management for Claude Agents Orchestration System.

This module manages the 200k token context budget with allocation:
- 15% System context (30k)
- 20% Historical context (40k)
- 15% Task context (30k)
- 40% Processing (80k)
- 10% Reserved (20k)

Includes progressive summarization between phases.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import json


class BudgetCategory(str, Enum):
    """Context budget categories."""

    SYSTEM = "system"
    HISTORICAL = "historical"
    TASK = "task"
    PROCESSING = "processing"
    RESERVED = "reserved"


class AlertLevel(str, Enum):
    """Budget alert levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class BudgetAllocation:
    """Token budget allocation for a category."""

    category: BudgetCategory
    allocated: int
    used: int = 0
    reserved: int = 0

    @property
    def available(self) -> int:
        return self.allocated - self.used - self.reserved

    @property
    def utilization(self) -> float:
        if self.allocated == 0:
            return 0.0
        return self.used / self.allocated

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "allocated": self.allocated,
            "used": self.used,
            "reserved": self.reserved,
            "available": self.available,
            "utilization": self.utilization,
        }


@dataclass
class BudgetAlert:
    """Budget alert notification."""

    level: AlertLevel
    category: BudgetCategory
    message: str
    utilization: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "category": self.category.value,
            "message": self.message,
            "utilization": self.utilization,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class TokenUsageRecord:
    """Record of token usage."""

    agent_name: str
    phase: int
    category: BudgetCategory
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
            "category": self.category.value,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "timestamp": self.timestamp.isoformat(),
        }


class ContextCompressor:
    """
    Utility for compressing and summarizing context.

    Uses progressive summarization to maintain information density
    while reducing token count.
    """

    # Patterns for identifying low-value content
    LOW_VALUE_PATTERNS = [
        r'\n{3,}',  # Multiple blank lines
        r'#{3,}.*?\n',  # Decorative headers
        r'[-=]{5,}',  # Separator lines
        r'```\s*```',  # Empty code blocks
    ]

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estimate token count for text.

        Uses a simple heuristic: ~4 characters per token for English text.
        """
        if not text:
            return 0
        # Simple estimation: words * 1.3 (average tokens per word)
        words = len(text.split())
        return int(words * 1.3)

    @staticmethod
    def calculate_info_density(text: str) -> float:
        """
        Calculate information density score (0-1).

        Higher scores indicate more valuable content.
        """
        if not text:
            return 0.0

        # Factors that increase density
        code_blocks = len(re.findall(r'```[\s\S]*?```', text))
        bullet_points = len(re.findall(r'^\s*[-*•]\s+', text, re.MULTILINE))
        key_terms = len(re.findall(r'\b(API|error|config|function|class|module)\b', text, re.I))

        # Factors that decrease density
        whitespace_ratio = len(re.findall(r'\s', text)) / len(text) if text else 0
        repetition = len(re.findall(r'(.{10,})\1', text))

        # Calculate score
        positive = (code_blocks * 0.1) + (bullet_points * 0.05) + (key_terms * 0.02)
        negative = (whitespace_ratio * 0.3) + (repetition * 0.1)

        return min(1.0, max(0.0, 0.5 + positive - negative))

    @classmethod
    def compress(cls, text: str, target_ratio: float = 0.5) -> str:
        """
        Compress text while preserving important information.

        Args:
            text: Text to compress
            target_ratio: Target size as ratio of original

        Returns:
            Compressed text
        """
        if not text:
            return ""

        original_tokens = cls.estimate_tokens(text)
        target_tokens = int(original_tokens * target_ratio)

        # Step 1: Remove low-value patterns
        compressed = text
        for pattern in cls.LOW_VALUE_PATTERNS:
            compressed = re.sub(pattern, '\n', compressed)

        # Step 2: Normalize whitespace
        compressed = re.sub(r'\n{2,}', '\n\n', compressed)
        compressed = re.sub(r' {2,}', ' ', compressed)

        # Step 3: If still over target, truncate intelligently
        current_tokens = cls.estimate_tokens(compressed)
        if current_tokens > target_tokens:
            # Split into paragraphs and keep most valuable
            paragraphs = compressed.split('\n\n')
            scored = [(p, cls.calculate_info_density(p)) for p in paragraphs]
            scored.sort(key=lambda x: x[1], reverse=True)

            # Keep high-value paragraphs until target reached
            kept = []
            running_tokens = 0
            for para, score in scored:
                para_tokens = cls.estimate_tokens(para)
                if running_tokens + para_tokens <= target_tokens:
                    kept.append(para)
                    running_tokens += para_tokens

            compressed = '\n\n'.join(kept)

        return compressed.strip()

    @classmethod
    def summarize_for_phase_transition(
        cls,
        context: Dict[str, Any],
        from_phase: int,
        to_phase: int,
    ) -> Dict[str, Any]:
        """
        Summarize context for phase transition.

        Args:
            context: Current context dictionary
            from_phase: Source phase
            to_phase: Target phase

        Returns:
            Summarized context
        """
        summarized = {}

        for key, value in context.items():
            if isinstance(value, str):
                # Compress string values
                summarized[key] = cls.compress(value, target_ratio=0.6)
            elif isinstance(value, dict):
                # Recursively summarize nested dicts
                summarized[key] = cls.summarize_for_phase_transition(
                    value, from_phase, to_phase
                )
            elif isinstance(value, list):
                # Keep lists but limit length
                if len(value) > 10:
                    summarized[key] = value[:10]
                    summarized[f"{key}_truncated"] = True
                    summarized[f"{key}_original_count"] = len(value)
                else:
                    summarized[key] = value
            else:
                summarized[key] = value

        # Add metadata
        summarized["_summarized"] = True
        summarized["_from_phase"] = from_phase
        summarized["_to_phase"] = to_phase

        return summarized


class ContextBudgetManager:
    """
    Manager for context token budget.

    Allocates and tracks token usage across categories:
    - System (15%): Prompts, instructions, system context
    - Historical (20%): Previous phase outputs, history
    - Task (15%): Current task context
    - Processing (40%): Agent processing space
    - Reserved (10%): Safety buffer

    Example:
        budget_manager = ContextBudgetManager(total_budget=200000)

        # Track usage
        budget_manager.use_tokens(
            agent="BackendEngineer",
            phase=4,
            category=BudgetCategory.PROCESSING,
            input_tokens=5000,
            output_tokens=3000,
        )

        # Check availability
        available = budget_manager.get_available(BudgetCategory.PROCESSING)

        # Get alerts
        alerts = budget_manager.get_alerts()
    """

    # Default allocation percentages
    DEFAULT_ALLOCATIONS = {
        BudgetCategory.SYSTEM: 0.15,
        BudgetCategory.HISTORICAL: 0.20,
        BudgetCategory.TASK: 0.15,
        BudgetCategory.PROCESSING: 0.40,
        BudgetCategory.RESERVED: 0.10,
    }

    # Alert thresholds
    WARNING_THRESHOLD = 0.75
    CRITICAL_THRESHOLD = 0.90

    def __init__(
        self,
        total_budget: int = 200000,
        allocations: Optional[Dict[BudgetCategory, float]] = None,
    ):
        """
        Initialize the budget manager.

        Args:
            total_budget: Total token budget
            allocations: Custom allocation percentages (must sum to 1.0)
        """
        self.total_budget = total_budget
        self._allocations = allocations or self.DEFAULT_ALLOCATIONS

        # Validate allocations
        total_percent = sum(self._allocations.values())
        if abs(total_percent - 1.0) > 0.001:
            raise ValueError(f"Allocations must sum to 1.0, got {total_percent}")

        # Initialize budgets
        self._budgets: Dict[BudgetCategory, BudgetAllocation] = {}
        for category, percent in self._allocations.items():
            allocated = int(total_budget * percent)
            self._budgets[category] = BudgetAllocation(
                category=category,
                allocated=allocated,
            )

        # Usage tracking
        self._usage_history: List[TokenUsageRecord] = []
        self._alerts: List[BudgetAlert] = []
        self._compressor = ContextCompressor()

    def get_allocation(self, category: BudgetCategory) -> BudgetAllocation:
        """Get the budget allocation for a category."""
        return self._budgets[category]

    def get_available(self, category: BudgetCategory) -> int:
        """Get available tokens for a category."""
        return self._budgets[category].available

    def get_total_used(self) -> int:
        """Get total tokens used across all categories."""
        return sum(b.used for b in self._budgets.values())

    def get_total_available(self) -> int:
        """Get total available tokens across all categories."""
        return self.total_budget - self.get_total_used()

    def use_tokens(
        self,
        agent: str,
        phase: int,
        category: BudgetCategory,
        input_tokens: int,
        output_tokens: int,
    ) -> bool:
        """
        Record token usage.

        Args:
            agent: Agent name
            phase: Current phase
            category: Budget category
            input_tokens: Input tokens used
            output_tokens: Output tokens used

        Returns:
            True if within budget, False if exceeded
        """
        total = input_tokens + output_tokens
        budget = self._budgets[category]

        # Check if within budget
        within_budget = budget.used + total <= budget.allocated

        # Record usage regardless
        budget.used += total

        # Create usage record
        record = TokenUsageRecord(
            agent_name=agent,
            phase=phase,
            category=category,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        self._usage_history.append(record)

        # Check for alerts
        self._check_alerts(category)

        return within_budget

    def reserve_tokens(self, category: BudgetCategory, amount: int) -> bool:
        """
        Reserve tokens for future use.

        Args:
            category: Budget category
            amount: Tokens to reserve

        Returns:
            True if reservation successful
        """
        budget = self._budgets[category]

        if budget.available >= amount:
            budget.reserved += amount
            return True
        return False

    def release_reservation(self, category: BudgetCategory, amount: int) -> None:
        """Release previously reserved tokens."""
        budget = self._budgets[category]
        budget.reserved = max(0, budget.reserved - amount)

    def _check_alerts(self, category: BudgetCategory) -> None:
        """Check and generate budget alerts."""
        budget = self._budgets[category]
        utilization = budget.utilization

        if utilization >= self.CRITICAL_THRESHOLD:
            self._alerts.append(BudgetAlert(
                level=AlertLevel.CRITICAL,
                category=category,
                message=f"Critical: {category.value} budget at {utilization:.0%} utilization",
                utilization=utilization,
            ))
        elif utilization >= self.WARNING_THRESHOLD:
            self._alerts.append(BudgetAlert(
                level=AlertLevel.WARNING,
                category=category,
                message=f"Warning: {category.value} budget at {utilization:.0%} utilization",
                utilization=utilization,
            ))

    def get_alerts(self, level: Optional[AlertLevel] = None) -> List[BudgetAlert]:
        """Get budget alerts, optionally filtered by level."""
        if level:
            return [a for a in self._alerts if a.level == level]
        return self._alerts.copy()

    def clear_alerts(self) -> None:
        """Clear all alerts."""
        self._alerts.clear()

    def get_usage_by_agent(self, agent: str) -> Dict[str, int]:
        """Get token usage breakdown by agent."""
        records = [r for r in self._usage_history if r.agent_name == agent]
        return {
            "input_tokens": sum(r.input_tokens for r in records),
            "output_tokens": sum(r.output_tokens for r in records),
            "total_tokens": sum(r.total_tokens for r in records),
        }

    def get_usage_by_phase(self, phase: int) -> Dict[str, int]:
        """Get token usage breakdown by phase."""
        records = [r for r in self._usage_history if r.phase == phase]
        return {
            "input_tokens": sum(r.input_tokens for r in records),
            "output_tokens": sum(r.output_tokens for r in records),
            "total_tokens": sum(r.total_tokens for r in records),
        }

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        return self._compressor.estimate_tokens(text)

    def compress_context(
        self,
        context: str,
        target_category: BudgetCategory,
    ) -> str:
        """
        Compress context to fit within category budget.

        Args:
            context: Context string to compress
            target_category: Category to fit within

        Returns:
            Compressed context string
        """
        available = self.get_available(target_category)
        current_tokens = self.estimate_tokens(context)

        if current_tokens <= available:
            return context

        target_ratio = available / current_tokens
        return self._compressor.compress(context, target_ratio)

    def summarize_phase_context(
        self,
        context: Dict[str, Any],
        from_phase: int,
        to_phase: int,
    ) -> Dict[str, Any]:
        """
        Summarize context for phase transition.

        Args:
            context: Context from completed phase
            from_phase: Source phase number
            to_phase: Target phase number

        Returns:
            Summarized context for next phase
        """
        return self._compressor.summarize_for_phase_transition(
            context, from_phase, to_phase
        )

    def get_budget_report(self) -> Dict[str, Any]:
        """Get comprehensive budget report."""
        return {
            "total_budget": self.total_budget,
            "total_used": self.get_total_used(),
            "total_available": self.get_total_available(),
            "utilization": self.get_total_used() / self.total_budget,
            "categories": {
                cat.value: alloc.to_dict()
                for cat, alloc in self._budgets.items()
            },
            "alerts": [a.to_dict() for a in self._alerts],
            "usage_records": len(self._usage_history),
        }

    def can_proceed(self, required_tokens: int, category: BudgetCategory) -> bool:
        """
        Check if operation can proceed with required tokens.

        Args:
            required_tokens: Tokens needed for operation
            category: Budget category

        Returns:
            True if sufficient budget available
        """
        return self.get_available(category) >= required_tokens

    def reset(self) -> None:
        """Reset all usage tracking (keeps allocations)."""
        for budget in self._budgets.values():
            budget.used = 0
            budget.reserved = 0
        self._usage_history.clear()
        self._alerts.clear()

    def transfer_budget(
        self,
        from_category: BudgetCategory,
        to_category: BudgetCategory,
        amount: int,
    ) -> bool:
        """
        Transfer budget between categories.

        Args:
            from_category: Source category
            to_category: Destination category
            amount: Tokens to transfer

        Returns:
            True if transfer successful
        """
        from_budget = self._budgets[from_category]
        to_budget = self._budgets[to_category]

        # Check if source has available tokens
        if from_budget.available < amount:
            return False

        # Cannot transfer from reserved
        if from_category == BudgetCategory.RESERVED:
            return False

        from_budget.allocated -= amount
        to_budget.allocated += amount

        return True
