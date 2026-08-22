"""
Configuration Management for Claude Agents Orchestration System.

This module handles loading, validation, and access to configuration
from environment variables and configuration files.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings


class AgentConfig(BaseModel):
    """Configuration for individual agents."""

    name: str
    enabled: bool = True
    timeout: int = 300
    max_retries: int = 3
    skills_file: Optional[str] = None


class MCPServerConfig(BaseModel):
    """Configuration for MCP servers."""

    name: str
    url: str
    enabled: bool = True
    timeout: int = 60
    auth_type: str = "none"  # none, api_key, oauth
    credentials: Optional[Dict[str, str]] = None


class ValidationGateConfig(BaseModel):
    """Configuration for validation gates."""

    pass_threshold: int = 70
    review_threshold: int = 50
    halt_threshold: int = 50
    strictness: str = "LOW"  # LOW, MEDIUM, HIGH, STRICT


class ErrorRecoveryConfig(BaseModel):
    """Configuration for error recovery."""

    level1_retry_attempts: int = 3
    level1_timeout_minutes: int = 10
    level2_retry_attempts: int = 2
    level2_timeout_minutes: int = 30
    level3_require_human: bool = True


class ContextBudgetConfig(BaseModel):
    """Configuration for context budget management."""

    total_budget: int = 200000
    system_percent: int = 15
    historical_percent: int = 20
    task_percent: int = 15
    processing_percent: int = 40
    reserved_percent: int = 10

    @property
    def system_budget(self) -> int:
        return int(self.total_budget * self.system_percent / 100)

    @property
    def historical_budget(self) -> int:
        return int(self.total_budget * self.historical_percent / 100)

    @property
    def task_budget(self) -> int:
        return int(self.total_budget * self.task_percent / 100)

    @property
    def processing_budget(self) -> int:
        return int(self.total_budget * self.processing_percent / 100)

    @property
    def reserved_budget(self) -> int:
        return int(self.total_budget * self.reserved_percent / 100)


class LoggingConfig(BaseModel):
    """Configuration for logging."""

    level: str = "DEBUG"
    format: str = "json"
    directory: str = "./logs"
    rotation: str = "10 MB"
    retention: str = "30 days"
    audit_retention: str = "7 years"


class Settings(BaseSettings):
    """Main settings loaded from environment."""

    # Environment
    environment: str = Field(default="local", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")

    # Database
    database_url: str = Field(default="sqlite:///./state.db", env="DATABASE_URL")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")

    # Claude CLI
    claude_cli_path: str = Field(default="claude", env="CLAUDE_CLI_PATH")
    claude_output_format: str = Field(default="json", env="CLAUDE_OUTPUT_FORMAT")
    claude_max_turns: int = Field(default=5, env="CLAUDE_MAX_TURNS")

    # Context Budget
    context_budget: int = Field(default=200000, env="CONTEXT_BUDGET")

    # Agent Settings
    max_retries: int = Field(default=3, env="MAX_RETRIES")
    agent_timeout: int = Field(default=300, env="AGENT_TIMEOUT")
    mcp_timeout: int = Field(default=60, env="MCP_TIMEOUT")

    # Validation
    validation_strictness: str = Field(default="LOW", env="VALIDATION_STRICTNESS")
    gate_pass_threshold: int = Field(default=70, env="GATE_PASS_THRESHOLD")
    gate_review_threshold: int = Field(default=50, env="GATE_REVIEW_THRESHOLD")

    # Logging
    log_level: str = Field(default="DEBUG", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    log_dir: str = Field(default="./logs", env="LOG_DIR")

    # Security
    secret_key: str = Field(default="change-me", env="SECRET_KEY")
    enable_secret_detection: bool = Field(default=True, env="ENABLE_SECRET_DETECTION")

    # MCP
    mcp_enabled: bool = Field(default=True, env="MCP_ENABLED")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


class ConfigManager:
    """
    Configuration manager for the orchestration system.

    Handles loading configuration from:
    - Environment variables
    - .env files
    - YAML configuration files

    Example:
        config = ConfigManager()
        config.load_from_file("./config.yaml")
        db_url = config.get("DATABASE_URL")
    """

    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize the configuration manager.

        Args:
            env_file: Path to .env file. If None, uses default locations.
        """
        self._settings: Optional[Settings] = None
        self._file_config: Dict[str, Any] = {}
        self._overrides: Dict[str, Any] = {}

        # Load environment variables
        self._load_env(env_file)

        # Initialize settings
        self._settings = Settings()

        # Initialize sub-configs
        self._context_budget = ContextBudgetConfig(total_budget=self._settings.context_budget)
        self._validation = ValidationGateConfig(
            pass_threshold=self._settings.gate_pass_threshold,
            review_threshold=self._settings.gate_review_threshold,
            strictness=self._settings.validation_strictness,
        )
        self._logging = LoggingConfig(
            level=self._settings.log_level,
            format=self._settings.log_format,
            directory=self._settings.log_dir,
        )
        self._error_recovery = ErrorRecoveryConfig()

        # Agent registry
        self._agents: Dict[str, AgentConfig] = {}
        self._mcp_servers: Dict[str, MCPServerConfig] = {}

        # Initialize default agents
        self._init_default_agents()

    def _load_env(self, env_file: Optional[str] = None) -> None:
        """Load environment variables from .env files."""
        # Load base .env
        load_dotenv(".env.base", override=False)

        # Load environment-specific .env
        env = os.getenv("ENVIRONMENT", "local")
        env_specific = f".env.{env}"
        if Path(env_specific).exists():
            load_dotenv(env_specific, override=True)

        # Load specified env file
        if env_file and Path(env_file).exists():
            load_dotenv(env_file, override=True)

        # Load default .env last
        load_dotenv(".env", override=True)

    def _init_default_agents(self) -> None:
        """Initialize default agent configurations."""
        default_agents = [
            ("concept_designer", "skills/concept_designer.skills.md"),
            ("mcp_engineer", "skills/mcp_engineer.skills.md"),
            ("integration_engineer", "skills/integration_engineer.skills.md"),
            ("backend_engineer", "skills/backend_engineer.skills.md"),
            ("frontend_engineer", "skills/frontend_engineer.skills.md"),
            ("security_engineer", "skills/security_engineer.skills.md"),
            ("qa_engineer", "skills/qa_engineer.skills.md"),
            ("devops_engineer", "skills/devops_engineer.skills.md"),
        ]

        for name, skills_file in default_agents:
            self._agents[name] = AgentConfig(
                name=name,
                enabled=True,
                timeout=self._settings.agent_timeout,
                max_retries=self._settings.max_retries,
                skills_file=skills_file,
            )

    def load_from_file(self, file_path: str) -> None:
        """
        Load configuration from a YAML file.

        Args:
            file_path: Path to YAML configuration file.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        with open(path, "r") as f:
            self._file_config = yaml.safe_load(f) or {}

        # Process agents from file config
        if "agents" in self._file_config:
            for agent_cfg in self._file_config["agents"]:
                self._agents[agent_cfg["name"]] = AgentConfig(**agent_cfg)

        # Process MCP servers from file config
        if "mcp_servers" in self._file_config:
            for server_cfg in self._file_config["mcp_servers"]:
                self._mcp_servers[server_cfg["name"]] = MCPServerConfig(**server_cfg)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Lookup order:
        1. Overrides
        2. File config
        3. Environment/Settings
        4. Default

        Args:
            key: Configuration key (case-insensitive for env vars)
            default: Default value if not found

        Returns:
            Configuration value or default
        """
        # Check overrides first
        if key in self._overrides:
            return self._overrides[key]

        # Check file config
        if key in self._file_config:
            return self._file_config[key]

        # Check settings (convert to lowercase for attribute lookup)
        settings_key = key.lower()
        if hasattr(self._settings, settings_key):
            return getattr(self._settings, settings_key)

        # Check environment directly
        env_value = os.getenv(key) or os.getenv(key.upper())
        if env_value is not None:
            return env_value

        return default

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration override.

        Args:
            key: Configuration key
            value: Value to set
        """
        self._overrides[key] = value

    @property
    def settings(self) -> Settings:
        """Get the base settings object."""
        return self._settings

    @property
    def context_budget(self) -> ContextBudgetConfig:
        """Get context budget configuration."""
        return self._context_budget

    @property
    def validation(self) -> ValidationGateConfig:
        """Get validation gate configuration."""
        return self._validation

    @property
    def logging(self) -> LoggingConfig:
        """Get logging configuration."""
        return self._logging

    @property
    def error_recovery(self) -> ErrorRecoveryConfig:
        """Get error recovery configuration."""
        return self._error_recovery

    @property
    def agents(self) -> Dict[str, AgentConfig]:
        """Get agent configurations."""
        return self._agents

    @property
    def mcp_servers(self) -> Dict[str, MCPServerConfig]:
        """Get MCP server configurations."""
        return self._mcp_servers

    def get_agent(self, name: str) -> Optional[AgentConfig]:
        """Get configuration for a specific agent."""
        return self._agents.get(name)

    def get_mcp_server(self, name: str) -> Optional[MCPServerConfig]:
        """Get configuration for a specific MCP server."""
        return self._mcp_servers.get(name)

    def is_debug(self) -> bool:
        """Check if debug mode is enabled."""
        return self._settings.debug

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self._settings.environment == "production"

    def validate(self) -> List[str]:
        """
        Validate configuration completeness.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check required settings
        if not self._settings.database_url:
            errors.append("DATABASE_URL is required")

        if not self._settings.redis_url:
            errors.append("REDIS_URL is required")

        if self._settings.secret_key == "change-me" and self.is_production():
            errors.append("SECRET_KEY must be changed for production")

        # Validate context budget percentages
        total_percent = (
            self._context_budget.system_percent
            + self._context_budget.historical_percent
            + self._context_budget.task_percent
            + self._context_budget.processing_percent
            + self._context_budget.reserved_percent
        )
        if total_percent != 100:
            errors.append(f"Context budget percentages must sum to 100 (got {total_percent})")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary."""
        return {
            "environment": self._settings.environment,
            "debug": self._settings.debug,
            "database_url": self._settings.database_url,
            "redis_url": self._settings.redis_url,
            "context_budget": {
                "total": self._context_budget.total_budget,
                "system": self._context_budget.system_budget,
                "historical": self._context_budget.historical_budget,
                "task": self._context_budget.task_budget,
                "processing": self._context_budget.processing_budget,
                "reserved": self._context_budget.reserved_budget,
            },
            "validation": {
                "pass_threshold": self._validation.pass_threshold,
                "review_threshold": self._validation.review_threshold,
                "strictness": self._validation.strictness,
            },
            "agents": {name: cfg.model_dump() for name, cfg in self._agents.items()},
            "mcp_servers": {name: cfg.model_dump() for name, cfg in self._mcp_servers.items()},
        }
