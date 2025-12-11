"""
Helper Utilities for Claude Agents Orchestration System.

This module provides common utility functions used throughout the system.
"""

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, TypeVar, Union


T = TypeVar("T")


def generate_uuid() -> str:
    """Generate a UUID4 string."""
    return str(uuid.uuid4())


def generate_short_id(length: int = 8) -> str:
    """Generate a short random ID."""
    return uuid.uuid4().hex[:length]


def format_timestamp(
    dt: Optional[datetime] = None,
    format_str: str = "%Y-%m-%dT%H:%M:%S.%fZ",
) -> str:
    """
    Format a datetime as ISO timestamp.

    Args:
        dt: Datetime to format (uses now if None)
        format_str: Format string

    Returns:
        Formatted timestamp string
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.strftime(format_str)


def parse_timestamp(
    timestamp: str,
    format_str: str = "%Y-%m-%dT%H:%M:%S.%fZ",
) -> datetime:
    """
    Parse a timestamp string to datetime.

    Args:
        timestamp: Timestamp string
        format_str: Expected format

    Returns:
        Parsed datetime
    """
    try:
        return datetime.strptime(timestamp, format_str).replace(tzinfo=timezone.utc)
    except ValueError:
        # Try ISO format
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


def safe_json_loads(
    data: Union[str, bytes],
    default: Optional[T] = None,
) -> Union[Dict[str, Any], List, T]:
    """
    Safely parse JSON with default fallback.

    Args:
        data: JSON string or bytes
        default: Default value on error

    Returns:
        Parsed JSON or default
    """
    if default is None:
        default = {}

    try:
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        return json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return default


def safe_json_dumps(
    data: Any,
    default: str = "{}",
    indent: Optional[int] = None,
) -> str:
    """
    Safely serialize to JSON.

    Args:
        data: Data to serialize
        default: Default string on error
        indent: JSON indentation

    Returns:
        JSON string
    """
    try:
        return json.dumps(data, indent=indent, default=str)
    except (TypeError, ValueError):
        return default


def truncate_string(
    text: str,
    max_length: int = 100,
    suffix: str = "...",
) -> str:
    """
    Truncate string to max length with suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length (including suffix)
        suffix: Suffix to add when truncated

    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text

    truncate_at = max_length - len(suffix)
    return text[:truncate_at] + suffix


def slugify(text: str) -> str:
    """
    Convert text to URL-safe slug.

    Args:
        text: Text to convert

    Returns:
        URL-safe slug
    """
    # Convert to lowercase
    text = text.lower()

    # Replace spaces with hyphens
    text = re.sub(r"\s+", "-", text)

    # Remove non-alphanumeric characters (except hyphens)
    text = re.sub(r"[^a-z0-9-]", "", text)

    # Remove consecutive hyphens
    text = re.sub(r"-+", "-", text)

    # Remove leading/trailing hyphens
    text = text.strip("-")

    return text


def deep_merge(
    base: Dict[str, Any],
    override: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Deep merge two dictionaries.

    Args:
        base: Base dictionary
        override: Dictionary to merge (takes precedence)

    Returns:
        Merged dictionary
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def get_nested(
    data: Dict[str, Any],
    path: str,
    default: Optional[T] = None,
    separator: str = ".",
) -> Union[Any, T]:
    """
    Get a nested value from a dictionary.

    Args:
        data: Dictionary to search
        path: Dot-separated path (e.g., "config.database.url")
        default: Default value if not found
        separator: Path separator

    Returns:
        Value at path or default
    """
    keys = path.split(separator)
    current = data

    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default

    return current


def set_nested(
    data: Dict[str, Any],
    path: str,
    value: Any,
    separator: str = ".",
) -> Dict[str, Any]:
    """
    Set a nested value in a dictionary.

    Args:
        data: Dictionary to modify
        path: Dot-separated path
        value: Value to set
        separator: Path separator

    Returns:
        Modified dictionary
    """
    keys = path.split(separator)
    current = data

    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]

    current[keys[-1]] = value
    return data


def ensure_dir(path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists.

    Args:
        path: Directory path

    Returns:
        Path object
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_env(
    key: str,
    default: Optional[str] = None,
    required: bool = False,
) -> Optional[str]:
    """
    Get environment variable with validation.

    Args:
        key: Environment variable name
        default: Default value
        required: Whether the variable is required

    Returns:
        Environment variable value

    Raises:
        ValueError: If required and not set
    """
    value = os.environ.get(key, default)

    if required and value is None:
        raise ValueError(f"Required environment variable not set: {key}")

    return value


def get_env_bool(
    key: str,
    default: bool = False,
) -> bool:
    """
    Get boolean environment variable.

    Args:
        key: Environment variable name
        default: Default value

    Returns:
        Boolean value
    """
    value = os.environ.get(key, "").lower()

    if value in ("true", "1", "yes", "on"):
        return True
    elif value in ("false", "0", "no", "off"):
        return False

    return default


def get_env_int(
    key: str,
    default: int = 0,
) -> int:
    """
    Get integer environment variable.

    Args:
        key: Environment variable name
        default: Default value

    Returns:
        Integer value
    """
    value = os.environ.get(key)

    if value is not None:
        try:
            return int(value)
        except ValueError:
            pass

    return default


def chunk_list(lst: List[T], chunk_size: int) -> List[List[T]]:
    """
    Split a list into chunks.

    Args:
        lst: List to chunk
        chunk_size: Size of each chunk

    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def flatten_dict(
    data: Dict[str, Any],
    separator: str = ".",
    prefix: str = "",
) -> Dict[str, Any]:
    """
    Flatten a nested dictionary.

    Args:
        data: Dictionary to flatten
        separator: Key separator
        prefix: Key prefix

    Returns:
        Flattened dictionary
    """
    result = {}

    for key, value in data.items():
        new_key = f"{prefix}{separator}{key}" if prefix else key

        if isinstance(value, dict):
            result.update(flatten_dict(value, separator, new_key))
        else:
            result[new_key] = value

    return result


def unflatten_dict(
    data: Dict[str, Any],
    separator: str = ".",
) -> Dict[str, Any]:
    """
    Unflatten a flattened dictionary.

    Args:
        data: Flattened dictionary
        separator: Key separator

    Returns:
        Nested dictionary
    """
    result: Dict[str, Any] = {}

    for key, value in data.items():
        set_nested(result, key, value, separator)

    return result


def mask_sensitive(
    text: str,
    visible_start: int = 4,
    visible_end: int = 4,
    mask_char: str = "*",
) -> str:
    """
    Mask sensitive data, showing only start and end.

    Args:
        text: Text to mask
        visible_start: Characters to show at start
        visible_end: Characters to show at end
        mask_char: Character to use for masking

    Returns:
        Masked string
    """
    if len(text) <= visible_start + visible_end:
        return mask_char * len(text)

    masked_length = len(text) - visible_start - visible_end
    return text[:visible_start] + (mask_char * masked_length) + text[-visible_end:]


def bytes_to_human(
    size_bytes: int,
    decimal_places: int = 2,
) -> str:
    """
    Convert bytes to human-readable format.

    Args:
        size_bytes: Size in bytes
        decimal_places: Number of decimal places

    Returns:
        Human-readable string (e.g., "1.5 GB")
    """
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.{decimal_places}f} {unit}"
        size_bytes /= 1024.0

    return f"{size_bytes:.{decimal_places}f} EB"


def seconds_to_human(seconds: float) -> str:
    """
    Convert seconds to human-readable duration.

    Args:
        seconds: Duration in seconds

    Returns:
        Human-readable string (e.g., "2h 30m 15s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"

    minutes, secs = divmod(int(seconds), 60)
    hours, mins = divmod(minutes, 60)
    days, hrs = divmod(hours, 24)

    parts = []
    if days:
        parts.append(f"{days}d")
    if hrs:
        parts.append(f"{hrs}h")
    if mins:
        parts.append(f"{mins}m")
    if secs:
        parts.append(f"{secs}s")

    return " ".join(parts)
