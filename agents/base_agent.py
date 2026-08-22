"""
Base Agent for Claude Agents Orchestration System.

This module defines the abstract base class for all specialized agents,
providing common functionality for CLI invocation, message handling,
context management, and performance tracking.
"""

import asyncio
import json
import subprocess
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


class AgentStatus(str, Enum):
    """Agent operational status."""

    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    PAUSED = "paused"
    DISABLED = "disabled"


class AgentCapability(str, Enum):
    """Agent capabilities for task matching."""

    # Design capabilities
    REQUIREMENTS_ANALYSIS = "requirements_analysis"
    ARCHITECTURE_DESIGN = "architecture_design"
    TECH_STACK_SELECTION = "tech_stack_selection"

    # Data capabilities
    MCP_INTEGRATION = "mcp_integration"
    DATA_RETRIEVAL = "data_retrieval"
    SCHEMA_TRANSFORMATION = "schema_transformation"

    # Infrastructure capabilities
    CLOUD_PROVISIONING = "cloud_provisioning"
    DATABASE_SETUP = "database_setup"
    CICD_CONFIGURATION = "cicd_configuration"

    # Development capabilities
    API_DEVELOPMENT = "api_development"
    BACKEND_CODE = "backend_code"
    FRONTEND_CODE = "frontend_code"
    UI_COMPONENTS = "ui_components"

    # Quality capabilities
    SECURITY_SCANNING = "security_scanning"
    TEST_GENERATION = "test_generation"
    CODE_REVIEW = "code_review"

    # Operations capabilities
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"
    DISASTER_RECOVERY = "disaster_recovery"


@dataclass
class AgentMetrics:
    """Performance metrics for an agent."""

    total_invocations: int = 0
    successful_invocations: int = 0
    failed_invocations: int = 0
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    total_latency_ms: float = 0.0
    last_invocation_at: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        if self.total_invocations == 0:
            return 0.0
        return self.successful_invocations / self.total_invocations

    @property
    def average_latency_ms(self) -> float:
        if self.total_invocations == 0:
            return 0.0
        return self.total_latency_ms / self.total_invocations

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_invocations": self.total_invocations,
            "successful_invocations": self.successful_invocations,
            "failed_invocations": self.failed_invocations,
            "success_rate": self.success_rate,
            "total_tokens_input": self.total_tokens_input,
            "total_tokens_output": self.total_tokens_output,
            "average_latency_ms": self.average_latency_ms,
            "last_invocation_at": (
                self.last_invocation_at.isoformat() if self.last_invocation_at else None
            ),
        }


@dataclass
class AgentContext:
    """Context for agent execution."""

    project_id: str
    phase: int
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_description: str = ""
    input_data: Dict[str, Any] = field(default_factory=dict)
    previous_outputs: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Result from agent execution."""

    success: bool
    output: Dict[str, Any]
    artifacts: List[str] = field(default_factory=list)
    tokens_input: int = 0
    tokens_output: int = 0
    latency_ms: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "artifacts": self.artifacts,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "latency_ms": self.latency_ms,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


class BaseAgent(ABC):
    """
    Abstract base class for all orchestration agents.

    Provides common functionality for:
    - Claude CLI invocation
    - Message handling
    - Context management
    - Performance tracking
    - Error handling

    Example:
        class MyAgent(BaseAgent):
            agent_name = "my_agent"
            agent_description = "Does something useful"
            capabilities = [AgentCapability.API_DEVELOPMENT]

            async def execute(self, context: AgentContext) -> AgentResult:
                prompt = self.build_prompt(context)
                response = await self.invoke_claude(prompt)
                return AgentResult(success=True, output=response)
    """

    # Class attributes to be overridden by subclasses
    agent_name: str = "base_agent"
    agent_description: str = "Base agent class"
    capabilities: List[AgentCapability] = []
    skills_file: Optional[str] = None
    phase: int = 0

    def __init__(
        self,
        working_dir: Optional[Path] = None,
        claude_cli_path: str = "claude",
        timeout: int = 300,
        max_retries: int = 3,
    ):
        """
        Initialize the base agent.

        Args:
            working_dir: Working directory for file operations
            claude_cli_path: Path to Claude CLI executable
            timeout: Execution timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.working_dir = working_dir or Path.cwd()
        self.claude_cli_path = claude_cli_path
        self.timeout = timeout
        self.max_retries = max_retries

        self._status = AgentStatus.IDLE
        self._metrics = AgentMetrics()
        self._skills_content: Optional[str] = None

        # Load skills if file specified
        if self.skills_file:
            self._load_skills()

    def _load_skills(self) -> None:
        """Load skills from markdown file."""
        skills_path = self.working_dir / self.skills_file
        if skills_path.exists():
            self._skills_content = skills_path.read_text()

    @property
    def status(self) -> AgentStatus:
        """Get current agent status."""
        return self._status

    @property
    def metrics(self) -> AgentMetrics:
        """Get agent metrics."""
        return self._metrics

    def has_capability(self, capability: AgentCapability) -> bool:
        """Check if agent has a specific capability."""
        return capability in self.capabilities

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute the agent's primary task.

        Args:
            context: Execution context with task details

        Returns:
            AgentResult with output and metrics
        """
        pass

    @abstractmethod
    def build_prompt(self, context: AgentContext) -> str:
        """
        Build the prompt for Claude invocation.

        Args:
            context: Execution context

        Returns:
            Formatted prompt string
        """
        pass

    async def invoke_claude(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        output_format: str = "json",
        max_turns: int = 1,
    ) -> Dict[str, Any]:
        """
        Invoke Claude via CLI.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            output_format: Output format (json, text)
            max_turns: Maximum conversation turns

        Returns:
            Parsed response from Claude
        """
        start_time = time.time()
        self._status = AgentStatus.BUSY

        try:
            # Build command
            cmd = [self.claude_cli_path, "-p", prompt]

            if system_prompt:
                cmd.extend(["--system-prompt", system_prompt])

            cmd.extend(["--output-format", output_format])
            cmd.extend(["--max-turns", str(max_turns)])

            # Add working directory context
            cmd.extend(["--cwd", str(self.working_dir)])

            # Execute command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout,
            )

            # Parse response
            if process.returncode == 0:
                response_text = stdout.decode("utf-8")
                if output_format == "json":
                    try:
                        response = json.loads(response_text)
                    except json.JSONDecodeError:
                        response = {"text": response_text, "raw": True}
                else:
                    response = {"text": response_text}

                # Update metrics
                latency = (time.time() - start_time) * 1000
                self._metrics.total_invocations += 1
                self._metrics.successful_invocations += 1
                self._metrics.total_latency_ms += latency
                self._metrics.last_invocation_at = datetime.now(timezone.utc)

                # Estimate tokens (rough estimation)
                self._metrics.total_tokens_input += len(prompt.split()) * 2
                self._metrics.total_tokens_output += len(response_text.split()) * 2

                return response
            else:
                error_text = stderr.decode("utf-8")
                self._metrics.total_invocations += 1
                self._metrics.failed_invocations += 1
                raise RuntimeError(f"Claude CLI error: {error_text}")

        except asyncio.TimeoutError:
            self._metrics.total_invocations += 1
            self._metrics.failed_invocations += 1
            raise TimeoutError(f"Claude invocation timed out after {self.timeout}s")

        finally:
            self._status = AgentStatus.IDLE

    async def invoke_with_retry(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Invoke Claude with automatic retry on failure.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt

        Returns:
            Parsed response from Claude
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                return await self.invoke_claude(prompt, system_prompt)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)

        raise last_error

    def get_system_prompt(self) -> str:
        """
        Get the system prompt for this agent.

        Combines agent description with skills content.
        """
        prompt_parts = [
            f"You are {self.agent_name}, {self.agent_description}.",
            "",
            "Your capabilities include:",
        ]

        for cap in self.capabilities:
            prompt_parts.append(f"- {cap.value.replace('_', ' ').title()}")

        if self._skills_content:
            prompt_parts.extend(
                [
                    "",
                    "Your detailed skills and expertise:",
                    self._skills_content,
                ]
            )

        prompt_parts.extend(
            [
                "",
                "Always respond with valid JSON containing your analysis and output.",
                "Be thorough, accurate, and follow best practices.",
            ]
        )

        return "\n".join(prompt_parts)

    async def validate_input(self, context: AgentContext) -> Tuple[bool, List[str]]:
        """
        Validate input context before execution.

        Args:
            context: Execution context

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        if not context.project_id:
            errors.append("project_id is required")

        if not context.task_description:
            errors.append("task_description is required")

        return len(errors) == 0, errors

    async def run(self, context: AgentContext) -> AgentResult:
        """
        Run the agent with full lifecycle management.

        Handles validation, execution, and error handling.

        Args:
            context: Execution context

        Returns:
            AgentResult with output and metrics
        """
        # Validate input
        is_valid, errors = await self.validate_input(context)
        if not is_valid:
            return AgentResult(
                success=False,
                output={},
                error_message=f"Validation failed: {'; '.join(errors)}",
            )

        # Execute with error handling
        start_time = time.time()

        try:
            result = await self.execute(context)
            result.latency_ms = (time.time() - start_time) * 1000
            return result

        except TimeoutError as e:
            return AgentResult(
                success=False,
                output={},
                error_message=f"Timeout: {str(e)}",
                latency_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            return AgentResult(
                success=False,
                output={},
                error_message=f"{type(e).__name__}: {str(e)}",
                latency_ms=(time.time() - start_time) * 1000,
            )

    def reset_metrics(self) -> None:
        """Reset agent metrics."""
        self._metrics = AgentMetrics()

    def to_dict(self) -> Dict[str, Any]:
        """Convert agent info to dictionary."""
        return {
            "name": self.agent_name,
            "description": self.agent_description,
            "capabilities": [c.value for c in self.capabilities],
            "phase": self.phase,
            "status": self._status.value,
            "metrics": self._metrics.to_dict(),
        }
