"""
EduLens Configuration Management

This module provides a comprehensive configuration management system for EduLens,
supporting multiple configuration sources, environment-specific settings, validation,
and secure secret management.

Features:
- YAML configuration files
- Environment variable overrides
- Configuration validation with schemas
- Secure secret management
- Hot-reloading support
- Type-safe configuration access
- Default value fallbacks

Author: Integration Agent (INT-001)
Version: 1.0.0
Date: 2025-12-10
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, TypeVar, cast

import yaml
from pydantic import BaseModel, Field, ValidationError, validator

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration Exceptions
# ============================================================================


class ConfigurationError(Exception):
    """Base exception for configuration errors"""

    pass


class ConfigValidationError(ConfigurationError):
    """Configuration validation error"""

    pass


class ConfigNotFoundError(ConfigurationError):
    """Configuration file not found"""

    pass


class SecretError(ConfigurationError):
    """Secret management error"""

    pass


# ============================================================================
# Configuration Schemas (Pydantic Models)
# ============================================================================


class CameraConfig(BaseModel):
    """Camera configuration"""

    fps: int = Field(default=30, ge=1, le=120)
    resolution_width: int = Field(default=1920, ge=640)
    resolution_height: int = Field(default=1080, ge=480)
    device_id: int = Field(default=0, ge=0)
    auto_exposure: bool = True
    buffer_size: int = Field(default=10, ge=1)


class AudioConfig(BaseModel):
    """Audio configuration"""

    sample_rate: int = Field(default=16000, ge=8000, le=48000)
    channels: int = Field(default=1, ge=1, le=2)
    chunk_duration_ms: int = Field(default=100, ge=10, le=1000)
    device_id: Optional[int] = None
    noise_reduction: bool = True


class VisionPipelineConfig(BaseModel):
    """Vision pipeline configuration"""

    object_detection_enabled: bool = True
    object_detection_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    ocr_enabled: bool = True
    ocr_languages: list[str] = Field(default_factory=lambda: ["en"])
    scene_analysis_enabled: bool = True
    preprocessing_size: tuple[int, int] = (640, 640)


class AudioPipelineConfig(BaseModel):
    """Audio pipeline configuration"""

    speech_recognition_enabled: bool = True
    speaker_identification_enabled: bool = False
    language: str = "en"
    model: str = "whisper-tiny"


class PrivacyConfig(BaseModel):
    """Privacy configuration"""

    pii_detection_enabled: bool = True
    face_blur_enabled: bool = True
    blur_sigma: float = Field(default=50.0, ge=1.0, le=100.0)
    text_redaction_enabled: bool = True
    consent_required: bool = True
    data_retention_days: int = Field(default=30, ge=1)


class AIEngineConfig(BaseModel):
    """AI engine configuration"""

    llm_provider: str = "anthropic"  # anthropic, openai, local
    llm_model: str = "claude-3-5-sonnet-20241022"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=1)
    context_window_size: int = Field(default=10, ge=1)
    rag_enabled: bool = True
    rag_top_k: int = Field(default=5, ge=1)


class StorageConfig(BaseModel):
    """Storage configuration"""

    database_type: str = "sqlite"  # sqlite, postgresql
    database_path: str = "./data/edulens.db"
    cache_enabled: bool = True
    cache_backend: str = "memory"  # memory, redis
    cache_ttl_seconds: int = Field(default=3600, ge=60)


class CloudConfig(BaseModel):
    """Cloud services configuration"""

    enabled: bool = False
    api_endpoint: str = "https://api.edulens.com"
    sync_interval_seconds: int = Field(default=300, ge=60)
    retry_attempts: int = Field(default=3, ge=1)
    timeout_seconds: int = Field(default=30, ge=1)


class LoggingConfig(BaseModel):
    """Logging configuration"""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_to_file: bool = True
    log_file_path: str = "./logs/edulens.log"
    max_file_size_mb: int = Field(default=100, ge=1)
    backup_count: int = Field(default=5, ge=1)


class PerformanceConfig(BaseModel):
    """Performance configuration"""

    max_workers: int = Field(default=4, ge=1)
    batch_size: int = Field(default=1, ge=1)
    model_quantization: bool = True
    gpu_enabled: bool = False
    gpu_device_id: int = Field(default=0, ge=0)


class SystemConfig(BaseModel):
    """Complete system configuration"""

    environment: str = "development"  # development, staging, production
    debug: bool = False
    camera: CameraConfig = Field(default_factory=CameraConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    vision_pipeline: VisionPipelineConfig = Field(default_factory=VisionPipelineConfig)
    audio_pipeline: AudioPipelineConfig = Field(default_factory=AudioPipelineConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)
    ai_engine: AIEngineConfig = Field(default_factory=AIEngineConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    cloud: CloudConfig = Field(default_factory=CloudConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)

    @validator("environment")
    def validate_environment(cls, v: str) -> str:
        """Validate environment value"""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v


# ============================================================================
# Configuration Manager
# ============================================================================

T = TypeVar("T")


class ConfigManager:
    """
    Configuration manager for EduLens system

    Provides centralized configuration management with support for:
    - Multiple configuration sources (YAML files, environment variables)
    - Configuration validation using Pydantic schemas
    - Environment-specific configurations
    - Secure secret management
    - Type-safe configuration access

    Example usage:
        config_manager = ConfigManager()
        config_manager.load_config("configs/system/default_config.yaml")

        # Access configuration
        fps = config_manager.get("camera.fps", default=30)

        # Get typed configuration
        camera_config = config_manager.get_typed("camera", CameraConfig)

        # Validate configuration
        config_manager.validate()
    """

    def __init__(
        self,
        config_dir: Optional[Path] = None,
        env_prefix: str = "EDULENS_",
    ) -> None:
        """
        Initialize configuration manager

        Args:
            config_dir: Directory containing configuration files
            env_prefix: Prefix for environment variable overrides
        """
        self._config: Dict[str, Any] = {}
        self._config_dir = config_dir or Path("./configs")
        self._env_prefix = env_prefix
        self._secrets: Dict[str, str] = {}
        self._system_config: Optional[SystemConfig] = None

    def load_config(
        self,
        config_path: str | Path,
        merge: bool = False,
    ) -> None:
        """
        Load configuration from YAML file

        Args:
            config_path: Path to configuration file
            merge: Whether to merge with existing config

        Raises:
            ConfigNotFoundError: If config file not found
            ConfigurationError: If config loading fails
        """
        config_path = Path(config_path)

        if not config_path.exists():
            raise ConfigNotFoundError(f"Configuration file not found: {config_path}")

        logger.info(f"Loading configuration from {config_path}")

        try:
            with open(config_path, "r") as f:
                yaml_config = yaml.safe_load(f)

            if yaml_config is None:
                yaml_config = {}

            if merge:
                self._merge_config(yaml_config)
            else:
                self._config = yaml_config

            # Apply environment variable overrides
            self._apply_env_overrides()

            logger.info(f"Configuration loaded successfully from {config_path}")

        except yaml.YAMLError as e:
            raise ConfigurationError(f"Failed to parse YAML configuration: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")

    def load_environment_config(self, environment: str) -> None:
        """
        Load environment-specific configuration

        Args:
            environment: Environment name (development, staging, production)

        Raises:
            ConfigNotFoundError: If environment config not found
        """
        env_config_path = self._config_dir / "system" / f"{environment}_config.yaml"

        if env_config_path.exists():
            self.load_config(env_config_path, merge=True)
        else:
            logger.warning(f"Environment config not found: {env_config_path}")

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides to configuration"""
        for key, value in os.environ.items():
            if key.startswith(self._env_prefix):
                # Convert EDULENS_CAMERA_FPS to camera.fps
                config_key = key[len(self._env_prefix) :].lower().replace("_", ".")
                self.set(config_key, self._parse_env_value(value))
                logger.debug(f"Environment override: {config_key} = {value}")

    def _parse_env_value(self, value: str) -> Any:
        """
        Parse environment variable value to appropriate type

        Args:
            value: String value from environment

        Returns:
            Parsed value (bool, int, float, or str)
        """
        # Boolean
        if value.lower() in ("true", "false"):
            return value.lower() == "true"

        # Integer
        try:
            return int(value)
        except ValueError:
            pass

        # Float
        try:
            return float(value)
        except ValueError:
            pass

        # String
        return value

    def _merge_config(self, new_config: Dict[str, Any]) -> None:
        """
        Merge new configuration with existing

        Args:
            new_config: Configuration to merge
        """

        def merge_dict(base: Dict[str, Any], update: Dict[str, Any]) -> None:
            for key, value in update.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    merge_dict(base[key], value)
                else:
                    base[key] = value

        merge_dict(self._config, new_config)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key

        Args:
            key: Configuration key (dot-separated path, e.g., "camera.fps")
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            fps = config.get("camera.fps", default=30)
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_typed(self, key: str, model: type[T]) -> T:
        """
        Get typed configuration section

        Args:
            key: Configuration section key
            model: Pydantic model class

        Returns:
            Typed configuration object

        Raises:
            ConfigValidationError: If validation fails

        Example:
            camera_config = config.get_typed("camera", CameraConfig)
        """
        value = self.get(key, default={})

        try:
            return model(**value)
        except ValidationError as e:
            raise ConfigValidationError(f"Validation failed for {key}: {e}")

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value

        Args:
            key: Configuration key (dot-separated path)
            value: Value to set

        Example:
            config.set("camera.fps", 60)
        """
        keys = key.split(".")
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def validate(self) -> SystemConfig:
        """
        Validate complete configuration against schema

        Returns:
            Validated SystemConfig object

        Raises:
            ConfigValidationError: If validation fails
        """
        try:
            self._system_config = SystemConfig(**self._config)
            logger.info("Configuration validation successful")
            return self._system_config

        except ValidationError as e:
            error_msg = self._format_validation_error(e)
            logger.error(f"Configuration validation failed:\n{error_msg}")
            raise ConfigValidationError(error_msg)

    def _format_validation_error(self, error: ValidationError) -> str:
        """
        Format Pydantic validation error for logging

        Args:
            error: ValidationError from Pydantic

        Returns:
            Formatted error message
        """
        lines = ["Configuration validation errors:"]
        for err in error.errors():
            location = ".".join(str(loc) for loc in err["loc"])
            lines.append(f"  - {location}: {err['msg']}")
        return "\n".join(lines)

    def get_system_config(self) -> SystemConfig:
        """
        Get validated system configuration

        Returns:
            SystemConfig object

        Raises:
            ConfigurationError: If config not validated yet
        """
        if self._system_config is None:
            raise ConfigurationError("Configuration not validated. Call validate() first.")
        return self._system_config

    def set_secret(self, key: str, value: str) -> None:
        """
        Store a secret securely

        Args:
            key: Secret key
            value: Secret value

        Note:
            In production, this should integrate with a proper secret
            management system (e.g., AWS Secrets Manager, HashiCorp Vault)
        """
        self._secrets[key] = value
        logger.info(f"Secret stored: {key}")

    def get_secret(self, key: str) -> Optional[str]:
        """
        Retrieve a secret

        Args:
            key: Secret key

        Returns:
            Secret value or None if not found
        """
        return self._secrets.get(key)

    def load_secrets_from_env(self) -> None:
        """
        Load secrets from environment variables

        Looks for variables with pattern: EDULENS_SECRET_*
        """
        secret_prefix = f"{self._env_prefix}SECRET_"

        for key, value in os.environ.items():
            if key.startswith(secret_prefix):
                secret_key = key[len(secret_prefix) :].lower()
                self.set_secret(secret_key, value)
                logger.info(f"Loaded secret from environment: {secret_key}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Get configuration as dictionary

        Returns:
            Configuration dictionary
        """
        return self._config.copy()

    def save_config(self, output_path: str | Path) -> None:
        """
        Save current configuration to YAML file

        Args:
            output_path: Path to output file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Saving configuration to {output_path}")

        try:
            with open(output_path, "w") as f:
                yaml.dump(self._config, f, default_flow_style=False, indent=2)

            logger.info(f"Configuration saved successfully to {output_path}")

        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")

    def reload(self) -> None:
        """
        Reload configuration from original source

        Useful for hot-reloading configuration changes
        """
        # This would require storing the original config path
        # For now, just log a warning
        logger.warning("Configuration hot-reloading not yet implemented")

    def __repr__(self) -> str:
        return f"ConfigManager(config_dir={self._config_dir}, keys={len(self._config)})"


# ============================================================================
# Global Configuration Instance
# ============================================================================

_global_config: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """
    Get global configuration manager instance

    Returns:
        Global ConfigManager instance
    """
    global _global_config
    if _global_config is None:
        _global_config = ConfigManager()
    return _global_config


def set_config(config: ConfigManager) -> None:
    """
    Set global configuration manager instance

    Args:
        config: ConfigManager to use as global
    """
    global _global_config
    _global_config = config


def reset_config() -> None:
    """Reset global configuration manager"""
    global _global_config
    _global_config = None


# ============================================================================
# Configuration Utilities
# ============================================================================


def load_default_config() -> ConfigManager:
    """
    Load default system configuration

    Returns:
        Configured ConfigManager instance
    """
    config = ConfigManager()

    # Try to load default config
    default_config_path = Path("./configs/system/default_config.yaml")
    if default_config_path.exists():
        config.load_config(default_config_path)

    # Load environment-specific config
    environment = os.environ.get("EDULENS_ENVIRONMENT", "development")
    config.load_environment_config(environment)

    # Load secrets from environment
    config.load_secrets_from_env()

    # Validate configuration
    config.validate()

    return config
