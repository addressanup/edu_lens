"""
Context Compressor for Claude Agents Orchestration System.

This module provides progressive summarization and context compression
to maintain information density while reducing token count.
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class CompressionResult:
    """Result of context compression."""

    original_text: str
    compressed_text: str
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    info_density_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_tokens": self.original_tokens,
            "compressed_tokens": self.compressed_tokens,
            "compression_ratio": self.compression_ratio,
            "info_density_score": self.info_density_score,
            "tokens_saved": self.original_tokens - self.compressed_tokens,
        }


class ContextCompressor:
    """
    Context compression utility for managing token budgets.

    Uses progressive summarization to maintain information density
    while reducing context size between phases.

    Example:
        compressor = ContextCompressor()

        # Compress text
        result = compressor.compress(long_text, target_ratio=0.5)

        # Summarize for phase transition
        summary = compressor.summarize_for_phase_transition(
            context=phase_context,
            from_phase=1,
            to_phase=2
        )
    """

    # Patterns for low-value content removal
    LOW_VALUE_PATTERNS = [
        (r"\n{3,}", "\n\n"),  # Multiple blank lines
        (r" {2,}", " "),  # Multiple spaces
        (r"\t+", " "),  # Tabs to single space
        (r"#{4,}[^\n]*\n", ""),  # Deep headers (h4+)
        (r"[-=]{5,}", ""),  # Separator lines
        (r"<!--[\s\S]*?-->", ""),  # HTML comments
        (r"```\s*```", ""),  # Empty code blocks
    ]

    # High-value keywords to preserve
    HIGH_VALUE_KEYWORDS = [
        "error",
        "exception",
        "failed",
        "critical",
        "api",
        "endpoint",
        "database",
        "schema",
        "config",
        "configuration",
        "setting",
        "security",
        "auth",
        "permission",
        "function",
        "class",
        "method",
        "interface",
        "requirement",
        "constraint",
        "dependency",
    ]

    def __init__(self, token_estimator: Optional[callable] = None):
        """
        Initialize the context compressor.

        Args:
            token_estimator: Function to estimate tokens (default: simple word-based)
        """
        self._estimate_tokens = token_estimator or self._default_token_estimate

    def _default_token_estimate(self, text: str) -> int:
        """Default token estimation (word-based)."""
        if not text:
            return 0
        return int(len(text.split()) * 1.3)

    def compress(
        self,
        text: str,
        target_ratio: float = 0.5,
        preserve_code: bool = True,
    ) -> CompressionResult:
        """
        Compress text while preserving important information.

        Args:
            text: Text to compress
            target_ratio: Target size as ratio of original (0-1)
            preserve_code: Whether to preserve code blocks

        Returns:
            CompressionResult with compressed text and metrics
        """
        if not text:
            return CompressionResult(
                original_text="",
                compressed_text="",
                original_tokens=0,
                compressed_tokens=0,
                compression_ratio=1.0,
                info_density_score=0.0,
            )

        original_tokens = self._estimate_tokens(text)
        target_tokens = int(original_tokens * target_ratio)

        # Step 1: Extract and preserve code blocks
        code_blocks = []
        if preserve_code:
            text, code_blocks = self._extract_code_blocks(text)

        # Step 2: Remove low-value patterns
        compressed = self._remove_low_value_patterns(text)

        # Step 3: Compress paragraphs by value
        current_tokens = self._estimate_tokens(compressed)
        if current_tokens > target_tokens:
            compressed = self._compress_by_value(compressed, target_tokens)

        # Step 4: Restore code blocks (truncated if needed)
        if code_blocks:
            compressed = self._restore_code_blocks(compressed, code_blocks, target_tokens)

        compressed_tokens = self._estimate_tokens(compressed)
        compression_ratio = compressed_tokens / original_tokens if original_tokens > 0 else 1.0
        info_density = self._calculate_info_density(compressed)

        return CompressionResult(
            original_text=text,
            compressed_text=compressed.strip(),
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=compression_ratio,
            info_density_score=info_density,
        )

    def _extract_code_blocks(self, text: str) -> Tuple[str, List[str]]:
        """Extract code blocks from text."""
        code_blocks = []
        pattern = r"```[\s\S]*?```"

        def replace_block(match):
            code_blocks.append(match.group(0))
            return f"[CODE_BLOCK_{len(code_blocks) - 1}]"

        text_without_code = re.sub(pattern, replace_block, text)
        return text_without_code, code_blocks

    def _restore_code_blocks(
        self,
        text: str,
        code_blocks: List[str],
        target_tokens: int,
    ) -> str:
        """Restore code blocks, truncating if needed."""
        for i, block in enumerate(code_blocks):
            placeholder = f"[CODE_BLOCK_{i}]"
            if placeholder in text:
                # Truncate block if too long
                block_tokens = self._estimate_tokens(block)
                if block_tokens > target_tokens * 0.3:
                    # Keep first and last parts
                    lines = block.split("\n")
                    if len(lines) > 10:
                        truncated = "\n".join(lines[:5] + ["...truncated..."] + lines[-3:])
                        block = truncated

                text = text.replace(placeholder, block)

        return text

    def _remove_low_value_patterns(self, text: str) -> str:
        """Remove low-value patterns from text."""
        result = text
        for pattern, replacement in self.LOW_VALUE_PATTERNS:
            result = re.sub(pattern, replacement, result)
        return result

    def _compress_by_value(self, text: str, target_tokens: int) -> str:
        """Compress text by keeping high-value paragraphs."""
        paragraphs = text.split("\n\n")

        # Score each paragraph
        scored = []
        for para in paragraphs:
            score = self._calculate_info_density(para)
            tokens = self._estimate_tokens(para)
            scored.append((para, score, tokens))

        # Sort by score (descending)
        scored.sort(key=lambda x: x[1], reverse=True)

        # Keep high-value paragraphs until target reached
        kept = []
        current_tokens = 0

        for para, score, tokens in scored:
            if current_tokens + tokens <= target_tokens:
                kept.append(para)
                current_tokens += tokens

        # Restore original order
        original_order = {para: i for i, para in enumerate(paragraphs)}
        kept.sort(key=lambda p: original_order.get(p, 999))

        return "\n\n".join(kept)

    def _calculate_info_density(self, text: str) -> float:
        """
        Calculate information density score (0-1).

        Higher scores indicate more valuable content.
        """
        if not text:
            return 0.0

        text_lower = text.lower()

        # Count high-value keywords
        keyword_count = sum(1 for kw in self.HIGH_VALUE_KEYWORDS if kw in text_lower)

        # Count structural elements
        code_blocks = len(re.findall(r"```", text))
        bullet_points = len(re.findall(r"^\s*[-*]\s", text, re.MULTILINE))
        headers = len(re.findall(r"^#+\s", text, re.MULTILINE))

        # Calculate whitespace ratio
        whitespace = len(re.findall(r"\s", text))
        ws_ratio = whitespace / len(text) if text else 0

        # Calculate score
        score = 0.5  # Base score

        # Add for keywords
        score += min(0.2, keyword_count * 0.02)

        # Add for structure
        score += min(0.15, code_blocks * 0.03)
        score += min(0.1, bullet_points * 0.01)
        score += min(0.05, headers * 0.02)

        # Subtract for excessive whitespace
        score -= max(0, (ws_ratio - 0.2) * 0.3)

        return max(0.0, min(1.0, score))

    def summarize_for_phase_transition(
        self,
        context: Dict[str, Any],
        from_phase: int,
        to_phase: int,
        target_ratio: float = 0.6,
    ) -> Dict[str, Any]:
        """
        Summarize context for phase transition.

        Preserves key information while reducing context size.

        Args:
            context: Context dictionary from completed phase
            from_phase: Source phase number
            to_phase: Target phase number
            target_ratio: Target compression ratio

        Returns:
            Summarized context dictionary
        """
        summarized = {}

        for key, value in context.items():
            if isinstance(value, str):
                # Compress string values
                result = self.compress(value, target_ratio)
                summarized[key] = result.compressed_text
            elif isinstance(value, dict):
                # Recursively summarize nested dicts
                summarized[key] = self.summarize_for_phase_transition(
                    value, from_phase, to_phase, target_ratio
                )
            elif isinstance(value, list):
                # Keep lists but limit length
                if len(value) > 10:
                    summarized[key] = value[:10]
                    summarized[f"_{key}_truncated"] = True
                    summarized[f"_{key}_original_count"] = len(value)
                else:
                    summarized[key] = value
            else:
                # Keep other types as-is
                summarized[key] = value

        # Add metadata
        summarized["_phase_transition"] = {
            "from_phase": from_phase,
            "to_phase": to_phase,
            "summarized": True,
        }

        return summarized

    def extract_key_points(
        self,
        text: str,
        max_points: int = 5,
    ) -> List[str]:
        """
        Extract key points from text.

        Args:
            text: Text to extract from
            max_points: Maximum number of points

        Returns:
            List of key point strings
        """
        # Split into sentences
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        # Score sentences
        scored = []
        for sentence in sentences:
            score = self._calculate_info_density(sentence)
            scored.append((sentence, score))

        # Get top sentences
        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:max_points]

        # Return in original order
        original_order = {s: i for i, s in enumerate(sentences)}
        top.sort(key=lambda x: original_order.get(x[0], 999))

        return [s[0] for s in top]
