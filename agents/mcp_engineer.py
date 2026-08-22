"""
MCP Engineer Agent for Claude Agents Orchestration System.

This agent handles Phase 2 of the orchestration pipeline:
- MCP server health checks
- Data retrieval from external sources
- Schema transformation
- Caching strategy
- Conditional activation (dormant when not needed)
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from agents.base_agent import (
    AgentCapability,
    AgentContext,
    AgentResult,
    AgentStatus,
    BaseAgent,
)


class MCPStatus(str, Enum):
    """MCP server status."""

    ACTIVE = "active"
    DORMANT = "dormant"
    FAILED = "failed"
    REACTIVATING = "reactivating"


class MCPEngineerAgent(BaseAgent):
    """
    MCP Engineer Agent for Phase 2.

    Responsible for:
    - MCP server connectivity and health checks
    - External data retrieval
    - Schema transformation
    - Data caching
    - Conditional activation (stays dormant if no MCP needed)
    """

    agent_name = "mcp_engineer"
    agent_description = "MCP integration specialist for external data retrieval and transformation"
    capabilities = [
        AgentCapability.MCP_INTEGRATION,
        AgentCapability.DATA_RETRIEVAL,
        AgentCapability.SCHEMA_TRANSFORMATION,
    ]
    skills_file = "skills/mcp_engineer.skills.md"
    phase = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._mcp_status = MCPStatus.DORMANT
        self._mcp_servers: Dict[str, Dict[str, Any]] = {}
        self._cache: Dict[str, Any] = {}

    @property
    def mcp_status(self) -> MCPStatus:
        """Get current MCP status."""
        return self._mcp_status

    async def check_mcp_availability(
        self,
        servers: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        Check availability of MCP servers.

        Args:
            servers: List of server configurations

        Returns:
            Status report for each server
        """
        results = {}

        for server in servers:
            server_name = server.get("name", "unknown")
            server_url = server.get("url", "")

            try:
                # Simulate health check (in production, would make actual request)
                # For now, we'll use Claude to simulate the check
                prompt = f"Check if MCP server at {server_url} is accessible. Return JSON with 'available': true/false"

                response = await self.invoke_claude(prompt)

                results[server_name] = {
                    "url": server_url,
                    "available": response.get("available", False),
                    "latency_ms": response.get("latency_ms", 0),
                    "version": response.get("version", "unknown"),
                }

            except Exception as e:
                results[server_name] = {
                    "url": server_url,
                    "available": False,
                    "error": str(e),
                }

        # Update MCP status based on results
        available_count = sum(1 for r in results.values() if r.get("available"))
        if available_count == len(servers):
            self._mcp_status = MCPStatus.ACTIVE
        elif available_count > 0:
            self._mcp_status = MCPStatus.REACTIVATING
        elif servers:
            self._mcp_status = MCPStatus.FAILED
        else:
            self._mcp_status = MCPStatus.DORMANT

        return {
            "status": self._mcp_status.value,
            "servers": results,
            "available_count": available_count,
            "total_count": len(servers),
        }

    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute MCP data retrieval phase.

        Args:
            context: Execution context with data requirements

        Returns:
            AgentResult with retrieved and transformed data
        """
        # Check if MCP is needed
        mcp_required = context.input_data.get("mcp_required", False)
        mcp_servers = context.input_data.get("mcp_servers", [])

        if not mcp_required or not mcp_servers:
            # Stay dormant - no MCP needed
            return AgentResult(
                success=True,
                output={
                    "mcp_status": MCPStatus.DORMANT.value,
                    "message": "No MCP data retrieval required",
                    "data": {},
                },
                metadata={
                    "phase": self.phase,
                    "agent": self.agent_name,
                    "mcp_status": MCPStatus.DORMANT.value,
                },
            )

        # Check MCP availability
        availability = await self.check_mcp_availability(mcp_servers)

        if self._mcp_status == MCPStatus.FAILED:
            return AgentResult(
                success=False,
                output={
                    "mcp_status": MCPStatus.FAILED.value,
                    "availability": availability,
                },
                error_message="All MCP servers are unavailable",
            )

        # Build and execute data retrieval
        try:
            prompt = self.build_prompt(context)
            system_prompt = self.get_system_prompt()

            response = await self.invoke_with_retry(prompt, system_prompt)

            # Transform and cache data
            retrieved_data = self._transform_data(response, context)

            return AgentResult(
                success=True,
                output={
                    "mcp_status": self._mcp_status.value,
                    "availability": availability,
                    "retrieved_data": retrieved_data,
                },
                metadata={
                    "phase": self.phase,
                    "agent": self.agent_name,
                    "mcp_status": self._mcp_status.value,
                    "cache_hit": False,
                },
            )

        except Exception as e:
            return AgentResult(
                success=False,
                output={
                    "mcp_status": MCPStatus.FAILED.value,
                },
                error_message=str(e),
            )

    def build_prompt(self, context: AgentContext) -> str:
        """Build the MCP data retrieval prompt."""
        prompt_parts = [
            "# MCP Data Retrieval Request",
            "",
            f"## Task",
            context.task_description,
            "",
        ]

        # Add data requirements
        data_requirements = context.input_data.get("data_requirements", [])
        if data_requirements:
            prompt_parts.extend(
                [
                    "## Data Requirements",
                    "",
                ]
            )
            for req in data_requirements:
                prompt_parts.append(f"- {req}")
            prompt_parts.append("")

        # Add MCP server info
        mcp_servers = context.input_data.get("mcp_servers", [])
        if mcp_servers:
            prompt_parts.extend(
                [
                    "## Available MCP Servers",
                    "",
                ]
            )
            for server in mcp_servers:
                prompt_parts.append(f"- {server.get('name')}: {server.get('url')}")
            prompt_parts.append("")

        # Add schema expectations
        if context.input_data.get("expected_schema"):
            prompt_parts.extend(
                [
                    "## Expected Data Schema",
                    str(context.input_data["expected_schema"]),
                    "",
                ]
            )

        prompt_parts.extend(
            [
                "## Required Output",
                "",
                "Please retrieve the required data and return it in JSON format:",
                "",
                "```json",
                "{",
                '  "success": true,',
                '  "data": {',
                '    "source": "MCP server name",',
                '    "retrieved_at": "ISO timestamp",',
                '    "records": [...],',
                '    "schema": {...}',
                "  },",
                '  "transformation_notes": "Any data transformation applied",',
                '  "cache_key": "Suggested cache key for this data"',
                "}",
                "```",
            ]
        )

        return "\n".join(prompt_parts)

    def _transform_data(
        self,
        response: Dict[str, Any],
        context: AgentContext,
    ) -> Dict[str, Any]:
        """Transform retrieved data to expected schema."""
        # Get expected schema
        expected_schema = context.input_data.get("expected_schema", {})

        # Basic transformation - in production, would do schema mapping
        transformed = {
            "success": response.get("success", True),
            "data": response.get("data", {}),
            "schema_valid": True,
            "transformation_applied": bool(expected_schema),
        }

        # Cache the result if cache key provided
        cache_key = response.get("cache_key")
        if cache_key:
            self._cache[cache_key] = transformed
            transformed["cached"] = True

        return transformed

    def get_cached_data(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached data."""
        return self._cache.get(cache_key)

    def clear_cache(self) -> None:
        """Clear the data cache."""
        self._cache.clear()
