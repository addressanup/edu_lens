"""
Cost Tracker for Claude Agents Orchestration System.

This module tracks and calculates costs for Claude API usage
based on token consumption.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class ModelTier(str, Enum):
    """Claude model tiers with different pricing."""

    OPUS = "opus"
    SONNET = "sonnet"
    HAIKU = "haiku"


@dataclass
class PricingConfig:
    """Pricing configuration per 1M tokens."""

    input_price: float  # USD per 1M input tokens
    output_price: float  # USD per 1M output tokens

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for token usage."""
        input_cost = (input_tokens / 1_000_000) * self.input_price
        output_cost = (output_tokens / 1_000_000) * self.output_price
        return input_cost + output_cost


# Default pricing (as of early 2024 - update as needed)
DEFAULT_PRICING = {
    ModelTier.OPUS: PricingConfig(input_price=15.0, output_price=75.0),
    ModelTier.SONNET: PricingConfig(input_price=3.0, output_price=15.0),
    ModelTier.HAIKU: PricingConfig(input_price=0.25, output_price=1.25),
}


@dataclass
class CostRecord:
    """Record of cost for a single operation."""

    agent_name: str
    phase: int
    input_tokens: int
    output_tokens: int
    model: ModelTier
    cost_usd: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "phase": self.phase,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.input_tokens + self.output_tokens,
            "model": self.model.value,
            "cost_usd": self.cost_usd,
            "timestamp": self.timestamp.isoformat(),
        }


class CostTracker:
    """
    Cost tracking and analysis for Claude API usage.

    Tracks costs per agent, per phase, and provides budget alerts
    and ROI analysis.

    Example:
        tracker = CostTracker(default_model=ModelTier.SONNET)
        tracker.set_budget(100.0)  # $100 budget

        # Track usage
        tracker.track(
            agent_name="ConceptDesigner",
            phase=1,
            input_tokens=5000,
            output_tokens=2000
        )

        # Check costs
        total = tracker.get_total_cost()
        remaining = tracker.get_remaining_budget()

        # Get breakdown
        by_agent = tracker.get_cost_by_agent()
        by_phase = tracker.get_cost_by_phase()
    """

    def __init__(
        self,
        default_model: ModelTier = ModelTier.SONNET,
        pricing: Optional[Dict[ModelTier, PricingConfig]] = None,
    ):
        """
        Initialize the cost tracker.

        Args:
            default_model: Default model tier for cost calculation
            pricing: Custom pricing configuration (optional)
        """
        self._default_model = default_model
        self._pricing = pricing or DEFAULT_PRICING
        self._records: List[CostRecord] = []
        self._budget: Optional[float] = None
        self._alerts: List[Dict[str, Any]] = []

    def set_budget(self, budget_usd: float) -> None:
        """Set the cost budget in USD."""
        self._budget = budget_usd

    def track(
        self,
        agent_name: str,
        phase: int,
        input_tokens: int,
        output_tokens: int,
        model: Optional[ModelTier] = None,
    ) -> CostRecord:
        """
        Track cost for a token usage event.

        Args:
            agent_name: Name of the agent
            phase: Current phase
            input_tokens: Input tokens used
            output_tokens: Output tokens generated
            model: Model tier (uses default if not specified)

        Returns:
            CostRecord for this usage
        """
        model = model or self._default_model
        pricing = self._pricing.get(model, self._pricing[ModelTier.SONNET])

        cost = pricing.calculate_cost(input_tokens, output_tokens)

        record = CostRecord(
            agent_name=agent_name,
            phase=phase,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
            cost_usd=cost,
        )

        self._records.append(record)
        self._check_budget_alerts()

        return record

    def _check_budget_alerts(self) -> None:
        """Check and generate budget alerts."""
        if self._budget is None:
            return

        total = self.get_total_cost()
        utilization = total / self._budget

        # Warning at 75%
        if utilization >= 0.75 and not any(a.get("level") == "warning" for a in self._alerts):
            self._alerts.append(
                {
                    "level": "warning",
                    "message": f"Budget utilization at {utilization:.0%}",
                    "cost": total,
                    "budget": self._budget,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

        # Critical at 90%
        if utilization >= 0.90 and not any(a.get("level") == "critical" for a in self._alerts):
            self._alerts.append(
                {
                    "level": "critical",
                    "message": f"Budget utilization at {utilization:.0%}",
                    "cost": total,
                    "budget": self._budget,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

    def get_total_cost(self) -> float:
        """Get total cost across all records."""
        return sum(r.cost_usd for r in self._records)

    def get_remaining_budget(self) -> Optional[float]:
        """Get remaining budget."""
        if self._budget is None:
            return None
        return max(0.0, self._budget - self.get_total_cost())

    def get_budget_utilization(self) -> Optional[float]:
        """Get budget utilization as ratio (0-1)."""
        if self._budget is None or self._budget == 0:
            return None
        return min(1.0, self.get_total_cost() / self._budget)

    def get_cost_by_agent(self) -> Dict[str, Dict[str, Any]]:
        """Get cost breakdown by agent."""
        by_agent: Dict[str, Dict[str, Any]] = {}

        for record in self._records:
            if record.agent_name not in by_agent:
                by_agent[record.agent_name] = {
                    "cost_usd": 0.0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "invocations": 0,
                }

            by_agent[record.agent_name]["cost_usd"] += record.cost_usd
            by_agent[record.agent_name]["input_tokens"] += record.input_tokens
            by_agent[record.agent_name]["output_tokens"] += record.output_tokens
            by_agent[record.agent_name]["invocations"] += 1

        return by_agent

    def get_cost_by_phase(self) -> Dict[int, Dict[str, Any]]:
        """Get cost breakdown by phase."""
        by_phase: Dict[int, Dict[str, Any]] = {}

        for record in self._records:
            if record.phase not in by_phase:
                by_phase[record.phase] = {
                    "cost_usd": 0.0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "agents": set(),
                }

            by_phase[record.phase]["cost_usd"] += record.cost_usd
            by_phase[record.phase]["input_tokens"] += record.input_tokens
            by_phase[record.phase]["output_tokens"] += record.output_tokens
            by_phase[record.phase]["agents"].add(record.agent_name)

        # Convert sets to counts
        for phase in by_phase:
            by_phase[phase]["agent_count"] = len(by_phase[phase]["agents"])
            del by_phase[phase]["agents"]

        return by_phase

    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive cost summary."""
        total_input = sum(r.input_tokens for r in self._records)
        total_output = sum(r.output_tokens for r in self._records)

        return {
            "total_cost_usd": self.get_total_cost(),
            "budget_usd": self._budget,
            "remaining_usd": self.get_remaining_budget(),
            "utilization": self.get_budget_utilization(),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "record_count": len(self._records),
            "by_agent": self.get_cost_by_agent(),
            "by_phase": self.get_cost_by_phase(),
            "alerts": self._alerts,
        }

    def estimate_project_cost(
        self,
        estimated_tokens: int,
        input_ratio: float = 0.6,
    ) -> Dict[str, float]:
        """
        Estimate project cost based on expected token usage.

        Args:
            estimated_tokens: Total estimated tokens
            input_ratio: Ratio of input to total tokens

        Returns:
            Estimated costs by model tier
        """
        input_tokens = int(estimated_tokens * input_ratio)
        output_tokens = estimated_tokens - input_tokens

        estimates = {}
        for model, pricing in self._pricing.items():
            cost = pricing.calculate_cost(input_tokens, output_tokens)
            estimates[model.value] = cost

        return estimates

    def get_roi_analysis(
        self,
        manual_hours_saved: float,
        hourly_rate: float = 100.0,
    ) -> Dict[str, Any]:
        """
        Calculate ROI based on time saved.

        Args:
            manual_hours_saved: Estimated hours saved vs manual work
            hourly_rate: Cost per hour of manual work

        Returns:
            ROI analysis
        """
        total_cost = self.get_total_cost()
        manual_cost = manual_hours_saved * hourly_rate
        savings = manual_cost - total_cost
        roi = (savings / total_cost * 100) if total_cost > 0 else 0

        return {
            "api_cost_usd": total_cost,
            "manual_cost_usd": manual_cost,
            "savings_usd": savings,
            "roi_percent": roi,
            "hours_saved": manual_hours_saved,
            "effective_hourly_rate": (
                total_cost / manual_hours_saved if manual_hours_saved > 0 else 0
            ),
        }

    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get all budget alerts."""
        return self._alerts.copy()

    def clear_alerts(self) -> None:
        """Clear all alerts."""
        self._alerts.clear()

    def clear_records(self) -> None:
        """Clear all cost records."""
        self._records.clear()
        self._alerts.clear()

    def export_records(self) -> List[Dict[str, Any]]:
        """Export all records as dictionaries."""
        return [r.to_dict() for r in self._records]
