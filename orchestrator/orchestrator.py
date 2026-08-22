"""
Claude Agents Orchestration Engine.

This is the central orchestration engine that coordinates all agents,
manages phases, handles validation gates, and produces deployment-ready output.
"""

import asyncio
import json
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from agents import BaseAgent, get_agent_registry
from core.communication_protocol import (
    MessageType,
    create_message,
    sign_message,
    validate_message,
)
from core.context_budget import BudgetAllocation, ContextBudgetManager
from core.error_recovery import ErrorRecoveryManager, ErrorSeverity, RecoveryLevel
from core.message_broker import Message, MessageBroker, MessagePriority
from core.validation_gates import (
    GateType,
    ValidationGateManager,
)
from core.validation_gates import ValidationResult as GateValidationResult
from orchestrator.config import ConfigManager, get_config
from orchestrator.logger import LoggerManager, get_logger
from orchestrator.state_manager import AgentExecutionRecord, Checkpoint, StateStore
from utils.context_compressor import ContextCompressor
from utils.cost_tracker import CostTracker, ModelTier
from utils.health_checks import HealthChecker, HealthStatus
from utils.helpers import ensure_dir, format_timestamp, generate_uuid
from utils.mcp_client import AuthType, MCPClient, MCPServerConfig
from utils.token_counter import TokenCounter
from utils.validators import InputValidator, SecretDetector


class OrchestratorPhase(str, Enum):
    """Orchestrator execution phases."""

    INITIALIZATION = "initialization"
    PHASE_1_CONCEPT = "phase_1_concept"
    PHASE_2_ARCHITECTURE = "phase_2_architecture"
    PHASE_3_IMPLEMENTATION = "phase_3_implementation"
    PHASE_4_TESTING = "phase_4_testing"
    PHASE_5_SECURITY = "phase_5_security"
    PHASE_6_DEPLOYMENT = "phase_6_deployment"
    COMPLETED = "completed"
    FAILED = "failed"


class OrchestratorStatus(str, Enum):
    """Orchestrator status."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PhaseResult:
    """Result of a phase execution."""

    phase: OrchestratorPhase
    success: bool
    outputs: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    token_usage: Dict[str, int] = field(default_factory=dict)
    validation_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase.value,
            "success": self.success,
            "outputs": self.outputs,
            "errors": self.errors,
            "duration_seconds": self.duration_seconds,
            "token_usage": self.token_usage,
            "validation_score": self.validation_score,
        }


@dataclass
class ProjectContext:
    """Project context maintained throughout orchestration."""

    project_id: str
    project_name: str
    specification: Dict[str, Any]
    phase_outputs: Dict[str, Any] = field(default_factory=dict)
    current_phase: OrchestratorPhase = OrchestratorPhase.INITIALIZATION
    mcp_enabled: bool = False
    mcp_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "specification": self.specification,
            "phase_outputs": self.phase_outputs,
            "current_phase": self.current_phase.value,
            "mcp_enabled": self.mcp_enabled,
            "mcp_data": self.mcp_data,
            "metadata": self.metadata,
        }


class ClaudeAgentsOrchestrator:
    """
    Central orchestration engine for Claude multi-agent system.

    Coordinates the execution of 8 specialized agents across 6 phases,
    managing communication, validation, error recovery, and context budget.

    Example:
        orchestrator = ClaudeAgentsOrchestrator()

        # Start new project
        result = await orchestrator.run_project(
            project_name="my-app",
            specification=spec_dict,
            enable_mcp=True
        )

        # Resume from checkpoint
        result = await orchestrator.resume_from_checkpoint(
            checkpoint_id="abc123"
        )

        # Get status
        status = orchestrator.get_status()
    """

    def __init__(
        self,
        config: Optional[ConfigManager] = None,
        output_dir: Optional[str] = None,
    ):
        """
        Initialize the orchestrator.

        Args:
            config: Configuration manager (uses default if not provided)
            output_dir: Output directory for generated files
        """
        self._config = config or get_config()
        self._logger = get_logger()
        self._output_dir = Path(output_dir or self._config.get("output_dir", "./output"))

        # Core components
        self._state_store = StateStore()
        self._message_broker = MessageBroker()
        self._validation_manager = ValidationGateManager()
        self._error_recovery = ErrorRecoveryManager()
        self._context_budget = ContextBudgetManager(
            total_budget=self._config.get("context_budget", 200000)
        )

        # Utilities
        self._token_counter = TokenCounter()
        self._context_compressor = ContextCompressor()
        self._cost_tracker = CostTracker(
            default_model=ModelTier(self._config.get("default_model", "sonnet"))
        )
        self._mcp_client = MCPClient()
        self._input_validator = InputValidator()
        self._secret_detector = SecretDetector()
        self._health_checker = HealthChecker()

        # Agent registry
        self._agent_registry = get_agent_registry()
        self._agents: Dict[str, BaseAgent] = {}

        # State
        self._status = OrchestratorStatus.IDLE
        self._current_context: Optional[ProjectContext] = None
        self._phase_results: List[PhaseResult] = []

        # Phase configuration
        self._phase_sequence = [
            OrchestratorPhase.PHASE_1_CONCEPT,
            OrchestratorPhase.PHASE_2_ARCHITECTURE,
            OrchestratorPhase.PHASE_3_IMPLEMENTATION,
            OrchestratorPhase.PHASE_4_TESTING,
            OrchestratorPhase.PHASE_5_SECURITY,
            OrchestratorPhase.PHASE_6_DEPLOYMENT,
        ]

        self._phase_agents = {
            OrchestratorPhase.PHASE_1_CONCEPT: ["concept_designer"],
            OrchestratorPhase.PHASE_2_ARCHITECTURE: ["mcp_engineer", "integration_engineer"],
            OrchestratorPhase.PHASE_3_IMPLEMENTATION: ["backend_engineer", "frontend_engineer"],
            OrchestratorPhase.PHASE_4_TESTING: ["qa_engineer"],
            OrchestratorPhase.PHASE_5_SECURITY: ["security_engineer"],
            OrchestratorPhase.PHASE_6_DEPLOYMENT: ["devops_engineer"],
        }

        self._phase_gates = {
            OrchestratorPhase.PHASE_1_CONCEPT: GateType.CONCEPT_VALIDATION,
            OrchestratorPhase.PHASE_2_ARCHITECTURE: GateType.ARCHITECTURE_VALIDATION,
            OrchestratorPhase.PHASE_3_IMPLEMENTATION: GateType.IMPLEMENTATION_VALIDATION,
            OrchestratorPhase.PHASE_4_TESTING: GateType.TESTING_VALIDATION,
            OrchestratorPhase.PHASE_5_SECURITY: GateType.SECURITY_VALIDATION,
        }

    async def initialize(self) -> bool:
        """
        Initialize all orchestrator components.

        Returns:
            True if initialization successful
        """
        self._logger.log_event("orchestrator_init", "Initializing orchestrator components")

        try:
            # Initialize state store
            await self._state_store.initialize()

            # Initialize message broker
            await self._message_broker.connect()

            # Initialize agents
            await self._initialize_agents()

            # Setup health checks
            self._setup_health_checks()

            self._logger.log_event("orchestrator_init", "Orchestrator initialized successfully")
            return True

        except Exception as e:
            self._logger.log_error(
                "init_failed",
                f"Orchestrator initialization failed: {str(e)}",
                {"error": str(e)},
            )
            return False

    async def _initialize_agents(self) -> None:
        """Initialize all registered agents."""
        for agent_name, agent_class in self._agent_registry.items():
            try:
                agent = agent_class(
                    agent_id=f"{agent_name}_{generate_uuid()[:8]}",
                    config=self._config.get(f"agents.{agent_name}", {}),
                )
                self._agents[agent_name] = agent
                self._logger.log_trace(
                    "agent_init",
                    f"Initialized agent: {agent_name}",
                    {"agent_id": agent.agent_id},
                )
            except Exception as e:
                self._logger.log_error(
                    "agent_init_failed",
                    f"Failed to initialize agent {agent_name}: {str(e)}",
                )

    def _setup_health_checks(self) -> None:
        """Setup health check functions for components."""
        # Add component health checks
        self._health_checker.add_check(
            "message_broker",
            lambda: self._message_broker.health_check(),
        )
        self._health_checker.add_check(
            "state_store",
            lambda: self._state_store.health_check(),
        )

    async def run_project(
        self,
        project_name: str,
        specification: Dict[str, Any],
        enable_mcp: bool = False,
        mcp_servers: Optional[List[MCPServerConfig]] = None,
        budget_usd: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Run a complete project through all phases.

        Args:
            project_name: Name of the project
            specification: Project specification dictionary
            enable_mcp: Whether to enable MCP integration
            mcp_servers: List of MCP server configurations
            budget_usd: Optional cost budget in USD

        Returns:
            Complete project results
        """
        project_id = generate_uuid()
        self._logger.log_event(
            "project_start",
            f"Starting project: {project_name}",
            {"project_id": project_id},
        )

        # Validate specification
        validation_result = self._validate_specification(specification)
        if not validation_result["valid"]:
            return {
                "success": False,
                "error": "Invalid specification",
                "validation_errors": validation_result["errors"],
            }

        # Check for secrets in specification
        if self._secret_detector.has_secrets(json.dumps(specification)):
            self._logger.log_error(
                "secrets_detected",
                "Secrets detected in project specification",
            )
            return {
                "success": False,
                "error": "Secrets detected in specification - please remove sensitive data",
            }

        # Initialize project context
        self._current_context = ProjectContext(
            project_id=project_id,
            project_name=project_name,
            specification=specification,
            mcp_enabled=enable_mcp,
            metadata={
                "started_at": format_timestamp(),
                "budget_usd": budget_usd,
            },
        )

        # Set budget if provided
        if budget_usd:
            self._cost_tracker.set_budget(budget_usd)

        # Setup MCP if enabled
        if enable_mcp and mcp_servers:
            await self._setup_mcp(mcp_servers)

        self._status = OrchestratorStatus.RUNNING

        try:
            # Execute phases
            for phase in self._phase_sequence:
                # Check budget before phase
                if budget_usd and self._cost_tracker.get_remaining_budget() <= 0:
                    self._logger.log_error("budget_exceeded", "Cost budget exceeded")
                    break

                # Execute phase
                phase_result = await self._execute_phase(phase)
                self._phase_results.append(phase_result)

                if not phase_result.success:
                    # Attempt recovery
                    recovered = await self._attempt_recovery(phase, phase_result)
                    if not recovered:
                        self._status = OrchestratorStatus.FAILED
                        break

                # Create checkpoint after successful phase
                await self._create_checkpoint(phase)

            # Generate final output
            if self._status != OrchestratorStatus.FAILED:
                self._status = OrchestratorStatus.COMPLETED
                await self._generate_deployment_package()

        except Exception as e:
            self._logger.log_error(
                "orchestration_failed",
                f"Orchestration failed: {str(e)}",
                {"error": str(e)},
            )
            self._status = OrchestratorStatus.FAILED

        finally:
            # Cleanup
            await self._cleanup()

        return self._generate_final_report()

    async def _execute_phase(self, phase: OrchestratorPhase) -> PhaseResult:
        """
        Execute a single phase.

        Args:
            phase: Phase to execute

        Returns:
            PhaseResult with outcomes
        """
        import time

        start_time = time.time()

        self._logger.log_event("phase_start", f"Starting phase: {phase.value}")
        self._current_context.current_phase = phase

        phase_outputs = {}
        phase_errors = []
        total_tokens = {"input": 0, "output": 0}

        try:
            # Get agents for this phase
            agent_names = self._phase_agents.get(phase, [])

            # Prepare context for agents
            agent_context = await self._prepare_phase_context(phase)

            # Execute agents
            for agent_name in agent_names:
                if agent_name not in self._agents:
                    phase_errors.append(f"Agent not found: {agent_name}")
                    continue

                agent = self._agents[agent_name]

                # Execute agent
                agent_result = await self._execute_agent(agent, agent_context, phase)

                if agent_result["success"]:
                    phase_outputs[agent_name] = agent_result["output"]
                    total_tokens["input"] += agent_result.get("input_tokens", 0)
                    total_tokens["output"] += agent_result.get("output_tokens", 0)

                    # Track cost
                    self._cost_tracker.track(
                        agent_name=agent_name,
                        phase=self._phase_sequence.index(phase) + 1,
                        input_tokens=agent_result.get("input_tokens", 0),
                        output_tokens=agent_result.get("output_tokens", 0),
                    )
                else:
                    phase_errors.append(
                        f"{agent_name}: {agent_result.get('error', 'Unknown error')}"
                    )

            # Run validation gate
            validation_score = 0.0
            if phase in self._phase_gates:
                gate_result = await self._run_validation_gate(phase, phase_outputs)
                validation_score = gate_result.confidence_score

                if not gate_result.passed:
                    phase_errors.append(f"Validation gate failed: {gate_result.message}")

            # Store phase outputs
            self._current_context.phase_outputs[phase.value] = phase_outputs

            duration = time.time() - start_time

            return PhaseResult(
                phase=phase,
                success=len(phase_errors) == 0,
                outputs=phase_outputs,
                errors=phase_errors,
                duration_seconds=duration,
                token_usage=total_tokens,
                validation_score=validation_score,
            )

        except Exception as e:
            return PhaseResult(
                phase=phase,
                success=False,
                errors=[str(e)],
                duration_seconds=time.time() - start_time,
            )

    async def _execute_agent(
        self,
        agent: BaseAgent,
        context: Dict[str, Any],
        phase: OrchestratorPhase,
    ) -> Dict[str, Any]:
        """
        Execute a single agent.

        Args:
            agent: Agent instance
            context: Execution context
            phase: Current phase

        Returns:
            Agent execution result
        """
        self._logger.log_trace(
            "agent_execute",
            f"Executing agent: {agent.name}",
            {"phase": phase.value},
        )

        try:
            # Build prompt from context
            prompt = self._build_agent_prompt(agent, context, phase)

            # Check context budget
            estimated_tokens = self._token_counter.estimate_tokens(prompt)
            budget_check = self._context_budget.check_budget(
                agent.name,
                estimated_tokens,
            )

            if not budget_check["allowed"]:
                # Compress context if over budget
                compressed = await self._context_compressor.compress(
                    context,
                    target_tokens=budget_check["available"],
                )
                prompt = self._build_agent_prompt(agent, compressed, phase)

            # Execute agent
            result = await agent.execute(prompt, context)

            # Record execution
            execution_record = AgentExecutionRecord(
                agent_id=agent.agent_id,
                agent_name=agent.name,
                phase=phase.value,
                input_tokens=result.get("input_tokens", 0),
                output_tokens=result.get("output_tokens", 0),
                success=result.get("success", False),
            )
            await self._state_store.record_execution(execution_record)

            # Update context budget
            self._context_budget.record_usage(
                agent.name,
                result.get("input_tokens", 0) + result.get("output_tokens", 0),
            )

            return result

        except Exception as e:
            self._logger.log_error(
                "agent_failed",
                f"Agent {agent.name} failed: {str(e)}",
            )
            return {"success": False, "error": str(e)}

    def _build_agent_prompt(
        self,
        agent: BaseAgent,
        context: Dict[str, Any],
        phase: OrchestratorPhase,
    ) -> str:
        """Build prompt for agent execution."""
        prompt_parts = [
            f"# Project: {self._current_context.project_name}",
            f"# Phase: {phase.value}",
            "",
            "## Project Specification",
            json.dumps(self._current_context.specification, indent=2),
            "",
        ]

        # Add previous phase outputs if available
        if self._current_context.phase_outputs:
            prompt_parts.append("## Previous Phase Outputs")
            prompt_parts.append(json.dumps(self._current_context.phase_outputs, indent=2))
            prompt_parts.append("")

        # Add MCP data if available
        if self._current_context.mcp_enabled and self._current_context.mcp_data:
            prompt_parts.append("## External Data (MCP)")
            prompt_parts.append(json.dumps(self._current_context.mcp_data, indent=2))
            prompt_parts.append("")

        # Add phase-specific context
        if context:
            prompt_parts.append("## Phase Context")
            prompt_parts.append(json.dumps(context, indent=2))
            prompt_parts.append("")

        # Add agent-specific instructions
        prompt_parts.append(f"## Your Role: {agent.name}")
        prompt_parts.append(f"Execute your responsibilities for this phase.")

        return "\n".join(prompt_parts)

    async def _prepare_phase_context(self, phase: OrchestratorPhase) -> Dict[str, Any]:
        """Prepare context for phase execution."""
        context = {
            "project_id": self._current_context.project_id,
            "project_name": self._current_context.project_name,
            "phase": phase.value,
            "specification": self._current_context.specification,
        }

        # Add compressed history from previous phases
        if self._current_context.phase_outputs:
            compressed_history = await self._context_compressor.summarize_for_phase_transition(
                self._current_context.phase_outputs,
                target_tokens=self._context_budget.get_allocation("historical").tokens,
            )
            context["previous_phases"] = compressed_history

        # Fetch MCP data if enabled
        if self._current_context.mcp_enabled:
            mcp_data = await self._fetch_mcp_data(phase)
            if mcp_data:
                context["mcp_data"] = mcp_data
                self._current_context.mcp_data.update(mcp_data)

        return context

    async def _run_validation_gate(
        self,
        phase: OrchestratorPhase,
        outputs: Dict[str, Any],
    ) -> GateValidationResult:
        """Run validation gate for phase."""
        gate_type = self._phase_gates.get(phase)
        if not gate_type:
            return GateValidationResult(passed=True, confidence_score=1.0)

        self._logger.log_decision(
            "validation_gate",
            f"Running {gate_type.value} gate",
            {"phase": phase.value},
        )

        result = await self._validation_manager.validate(
            gate_type=gate_type,
            data=outputs,
            context={
                "specification": self._current_context.specification,
                "phase": phase.value,
            },
        )

        self._logger.log_decision(
            "validation_result",
            f"Gate {gate_type.value}: {'PASSED' if result.passed else 'FAILED'}",
            {
                "score": result.confidence_score,
                "message": result.message,
            },
        )

        return result

    async def _attempt_recovery(
        self,
        phase: OrchestratorPhase,
        failed_result: PhaseResult,
    ) -> bool:
        """Attempt error recovery for failed phase."""
        self._logger.log_event(
            "recovery_attempt",
            f"Attempting recovery for phase: {phase.value}",
        )

        # Determine recovery level based on error severity
        severity = self._classify_error_severity(failed_result.errors)

        if severity == ErrorSeverity.LOW:
            # Level 1: Retry
            recovery_result = await self._error_recovery.recover(
                level=RecoveryLevel.RETRY,
                error_data={
                    "phase": phase.value,
                    "errors": failed_result.errors,
                },
                retry_func=lambda: self._execute_phase(phase),
            )
        elif severity == ErrorSeverity.MEDIUM:
            # Level 2: Phase rollback
            recovery_result = await self._error_recovery.recover(
                level=RecoveryLevel.PHASE_ROLLBACK,
                error_data={
                    "phase": phase.value,
                    "errors": failed_result.errors,
                },
                rollback_func=lambda: self._rollback_to_phase(phase),
            )
        else:
            # Level 3: Full rollback
            recovery_result = await self._error_recovery.recover(
                level=RecoveryLevel.FULL_ROLLBACK,
                error_data={
                    "phase": phase.value,
                    "errors": failed_result.errors,
                },
                rollback_func=lambda: self._full_rollback(),
            )

        return recovery_result.success

    def _classify_error_severity(self, errors: List[str]) -> ErrorSeverity:
        """Classify error severity based on error messages."""
        error_text = " ".join(errors).lower()

        if any(word in error_text for word in ["critical", "fatal", "security"]):
            return ErrorSeverity.CRITICAL
        elif any(word in error_text for word in ["validation", "failed", "timeout"]):
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW

    async def _rollback_to_phase(self, target_phase: OrchestratorPhase) -> bool:
        """Rollback to a specific phase."""
        phase_index = self._phase_sequence.index(target_phase)
        if phase_index > 0:
            previous_phase = self._phase_sequence[phase_index - 1]
            checkpoint = await self._state_store.get_latest_checkpoint(
                self._current_context.project_id,
                previous_phase.value,
            )
            if checkpoint:
                return await self.resume_from_checkpoint(checkpoint.checkpoint_id)
        return False

    async def _full_rollback(self) -> bool:
        """Perform full rollback to initial state."""
        self._current_context.phase_outputs.clear()
        self._phase_results.clear()
        return True

    async def _create_checkpoint(self, phase: OrchestratorPhase) -> str:
        """Create checkpoint after phase completion."""
        checkpoint = Checkpoint(
            checkpoint_id=generate_uuid(),
            project_id=self._current_context.project_id,
            phase=phase.value,
            state=self._current_context.to_dict(),
            phase_outputs=self._current_context.phase_outputs.copy(),
        )

        await self._state_store.save_checkpoint(checkpoint)

        self._logger.log_event(
            "checkpoint_created",
            f"Checkpoint created for phase: {phase.value}",
            {"checkpoint_id": checkpoint.checkpoint_id},
        )

        return checkpoint.checkpoint_id

    async def resume_from_checkpoint(self, checkpoint_id: str) -> Dict[str, Any]:
        """
        Resume project from a checkpoint.

        Args:
            checkpoint_id: ID of checkpoint to resume from

        Returns:
            Project results from resumed execution
        """
        self._logger.log_event(
            "checkpoint_resume",
            f"Resuming from checkpoint: {checkpoint_id}",
        )

        checkpoint = await self._state_store.get_checkpoint(checkpoint_id)
        if not checkpoint:
            return {
                "success": False,
                "error": f"Checkpoint not found: {checkpoint_id}",
            }

        # Restore context
        self._current_context = ProjectContext(
            project_id=checkpoint.state["project_id"],
            project_name=checkpoint.state["project_name"],
            specification=checkpoint.state["specification"],
            phase_outputs=checkpoint.phase_outputs,
            current_phase=OrchestratorPhase(checkpoint.phase),
            mcp_enabled=checkpoint.state.get("mcp_enabled", False),
            mcp_data=checkpoint.state.get("mcp_data", {}),
        )

        # Find starting phase
        current_index = self._phase_sequence.index(OrchestratorPhase(checkpoint.phase))
        remaining_phases = self._phase_sequence[current_index + 1 :]

        self._status = OrchestratorStatus.RUNNING

        try:
            for phase in remaining_phases:
                phase_result = await self._execute_phase(phase)
                self._phase_results.append(phase_result)

                if not phase_result.success:
                    recovered = await self._attempt_recovery(phase, phase_result)
                    if not recovered:
                        self._status = OrchestratorStatus.FAILED
                        break

                await self._create_checkpoint(phase)

            if self._status != OrchestratorStatus.FAILED:
                self._status = OrchestratorStatus.COMPLETED
                await self._generate_deployment_package()

        except Exception as e:
            self._logger.log_error("resume_failed", f"Resume failed: {str(e)}")
            self._status = OrchestratorStatus.FAILED

        return self._generate_final_report()

    async def _setup_mcp(self, servers: List[MCPServerConfig]) -> None:
        """Setup MCP server connections."""
        for server_config in servers:
            try:
                connected = await self._mcp_client.connect(server_config)
                if connected:
                    self._logger.log_event(
                        "mcp_connected",
                        f"Connected to MCP server: {server_config.name}",
                    )
            except Exception as e:
                self._logger.log_error(
                    "mcp_connect_failed",
                    f"Failed to connect to MCP server {server_config.name}: {str(e)}",
                )

    async def _fetch_mcp_data(self, phase: OrchestratorPhase) -> Dict[str, Any]:
        """Fetch relevant MCP data for phase."""
        mcp_data = {}

        connected_servers = self._mcp_client.get_connected_servers()
        if not connected_servers:
            return mcp_data

        # Determine what data to fetch based on phase
        queries = self._get_mcp_queries_for_phase(phase)

        for server_name in connected_servers:
            for query in queries:
                try:
                    result = await self._mcp_client.query(
                        server_name=server_name,
                        tool_name=query["tool"],
                        params=query["params"],
                    )
                    if result.success:
                        mcp_data[f"{server_name}_{query['tool']}"] = result.data
                except Exception as e:
                    self._logger.log_error(
                        "mcp_query_failed",
                        f"MCP query failed: {str(e)}",
                    )

        return mcp_data

    def _get_mcp_queries_for_phase(self, phase: OrchestratorPhase) -> List[Dict[str, Any]]:
        """Get MCP queries appropriate for each phase."""
        queries = {
            OrchestratorPhase.PHASE_1_CONCEPT: [
                {"tool": "search", "params": {"type": "market_research"}},
            ],
            OrchestratorPhase.PHASE_2_ARCHITECTURE: [
                {"tool": "search", "params": {"type": "tech_stack"}},
            ],
            OrchestratorPhase.PHASE_3_IMPLEMENTATION: [
                {"tool": "search", "params": {"type": "code_examples"}},
            ],
            OrchestratorPhase.PHASE_5_SECURITY: [
                {"tool": "search", "params": {"type": "security_advisories"}},
            ],
        }
        return queries.get(phase, [])

    async def _generate_deployment_package(self) -> None:
        """Generate final deployment package."""
        self._logger.log_event("deployment_package", "Generating deployment package")

        output_path = self._output_dir / self._current_context.project_name
        ensure_dir(output_path)

        # Write phase outputs
        for phase_name, outputs in self._current_context.phase_outputs.items():
            phase_dir = output_path / phase_name
            ensure_dir(phase_dir)

            for agent_name, output in outputs.items():
                output_file = phase_dir / f"{agent_name}_output.json"
                with open(output_file, "w") as f:
                    json.dump(output, f, indent=2)

        # Generate summary
        summary = {
            "project_id": self._current_context.project_id,
            "project_name": self._current_context.project_name,
            "completed_at": format_timestamp(),
            "phases_completed": len(self._phase_results),
            "total_cost": self._cost_tracker.get_summary(),
        }

        with open(output_path / "summary.json", "w") as f:
            json.dump(summary, f, indent=2)

        self._logger.log_event(
            "deployment_complete",
            f"Deployment package generated at: {output_path}",
        )

    def _generate_final_report(self) -> Dict[str, Any]:
        """Generate final project report."""
        return {
            "success": self._status == OrchestratorStatus.COMPLETED,
            "status": self._status.value,
            "project_id": self._current_context.project_id if self._current_context else None,
            "project_name": self._current_context.project_name if self._current_context else None,
            "phases": [r.to_dict() for r in self._phase_results],
            "cost_summary": self._cost_tracker.get_summary(),
            "context_summary": self._context_budget.get_summary(),
            "output_directory": (
                str(self._output_dir / self._current_context.project_name)
                if self._current_context
                else None
            ),
        }

    def _validate_specification(self, specification: Dict[str, Any]) -> Dict[str, Any]:
        """Validate project specification."""
        errors = []

        required_fields = ["name", "description", "features"]
        for field in required_fields:
            if field not in specification:
                errors.append(f"Missing required field: {field}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    async def _cleanup(self) -> None:
        """Cleanup resources."""
        await self._mcp_client.disconnect()
        await self._message_broker.disconnect()

    def get_status(self) -> Dict[str, Any]:
        """Get current orchestrator status."""
        return {
            "status": self._status.value,
            "current_phase": (
                self._current_context.current_phase.value if self._current_context else None
            ),
            "phases_completed": len(self._phase_results),
            "cost": self._cost_tracker.get_total_cost(),
            "budget_remaining": self._cost_tracker.get_remaining_budget(),
        }

    def get_phase_results(self) -> List[Dict[str, Any]]:
        """Get all phase results."""
        return [r.to_dict() for r in self._phase_results]

    async def health_check(self) -> Dict[str, Any]:
        """Run health check on all components."""
        health = await self._health_checker.check_all()
        return health.to_dict()
