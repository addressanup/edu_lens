"""
MCP Client for Claude Agents Orchestration System.

This module provides a generic MCP (Model Context Protocol) client interface
for connecting to and interacting with MCP servers.
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import httpx


class MCPServerStatus(str, Enum):
    """MCP server status."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    UNKNOWN = "unknown"


class AuthType(str, Enum):
    """Authentication types for MCP servers."""

    NONE = "none"
    API_KEY = "api_key"
    BEARER = "bearer"
    OAUTH = "oauth"
    BASIC = "basic"


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""

    name: str
    url: str
    auth_type: AuthType = AuthType.NONE
    credentials: Dict[str, str] = field(default_factory=dict)
    timeout: int = 60
    retry_attempts: int = 3
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class MCPTool:
    """Represents an MCP tool/capability."""

    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]] = None


@dataclass
class MCPResponse:
    """Response from an MCP operation."""

    success: bool
    data: Any = None
    error: Optional[str] = None
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "latency_ms": self.latency_ms,
            "metadata": self.metadata,
        }


@dataclass
class HealthStatus:
    """Health status of an MCP server."""

    status: MCPServerStatus
    latency_ms: float
    last_check: datetime
    version: Optional[str] = None
    capabilities: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "latency_ms": self.latency_ms,
            "last_check": self.last_check.isoformat(),
            "version": self.version,
            "capabilities": self.capabilities,
            "error": self.error,
        }


class MCPClient:
    """
    Generic MCP client for external data integration.

    Provides a unified interface for connecting to any MCP-compatible server,
    discovering tools, and executing queries.

    Example:
        client = MCPClient()

        # Configure server
        config = MCPServerConfig(
            name="my-server",
            url="http://localhost:8000",
            auth_type=AuthType.API_KEY,
            credentials={"api_key": "xxx"}
        )

        # Connect
        await client.connect(config)

        # Discover tools
        tools = await client.discover_tools()

        # Execute query
        result = await client.query("search", {"query": "test"})

        # Disconnect
        await client.disconnect()
    """

    def __init__(
        self,
        default_timeout: int = 60,
        retry_attempts: int = 3,
    ):
        """
        Initialize the MCP client.

        Args:
            default_timeout: Default request timeout in seconds
            retry_attempts: Number of retry attempts for failed requests
        """
        self._default_timeout = default_timeout
        self._retry_attempts = retry_attempts
        self._servers: Dict[str, MCPServerConfig] = {}
        self._connections: Dict[str, httpx.AsyncClient] = {}
        self._tools: Dict[str, List[MCPTool]] = {}
        self._cache: Dict[str, Any] = {}
        self._cache_ttl: int = 300  # 5 minutes

    async def connect(self, config: MCPServerConfig) -> bool:
        """
        Connect to an MCP server.

        Args:
            config: Server configuration

        Returns:
            True if connection successful
        """
        try:
            # Build headers
            headers = config.headers.copy()

            if config.auth_type == AuthType.API_KEY:
                headers["X-API-Key"] = config.credentials.get("api_key", "")
            elif config.auth_type == AuthType.BEARER:
                headers["Authorization"] = f"Bearer {config.credentials.get('token', '')}"
            elif config.auth_type == AuthType.BASIC:
                import base64
                credentials = f"{config.credentials.get('username', '')}:{config.credentials.get('password', '')}"
                encoded = base64.b64encode(credentials.encode()).decode()
                headers["Authorization"] = f"Basic {encoded}"

            # Create client
            client = httpx.AsyncClient(
                base_url=config.url,
                headers=headers,
                timeout=config.timeout,
            )

            # Test connection with health check
            health = await self._health_check(client)

            if health.status == MCPServerStatus.CONNECTED:
                self._servers[config.name] = config
                self._connections[config.name] = client
                return True
            else:
                await client.aclose()
                return False

        except Exception as e:
            return False

    async def disconnect(self, server_name: Optional[str] = None) -> None:
        """
        Disconnect from server(s).

        Args:
            server_name: Specific server to disconnect (None = all)
        """
        if server_name:
            if server_name in self._connections:
                await self._connections[server_name].aclose()
                del self._connections[server_name]
                del self._servers[server_name]
                if server_name in self._tools:
                    del self._tools[server_name]
        else:
            for client in self._connections.values():
                await client.aclose()
            self._connections.clear()
            self._servers.clear()
            self._tools.clear()

    async def _health_check(
        self,
        client: httpx.AsyncClient,
    ) -> HealthStatus:
        """Perform health check on server."""
        import time
        start = time.time()

        try:
            response = await client.get("/health")
            latency = (time.time() - start) * 1000

            if response.status_code == 200:
                data = response.json() if response.text else {}
                return HealthStatus(
                    status=MCPServerStatus.CONNECTED,
                    latency_ms=latency,
                    last_check=datetime.now(timezone.utc),
                    version=data.get("version"),
                    capabilities=data.get("capabilities", []),
                )
            else:
                return HealthStatus(
                    status=MCPServerStatus.ERROR,
                    latency_ms=latency,
                    last_check=datetime.now(timezone.utc),
                    error=f"HTTP {response.status_code}",
                )

        except Exception as e:
            return HealthStatus(
                status=MCPServerStatus.ERROR,
                latency_ms=(time.time() - start) * 1000,
                last_check=datetime.now(timezone.utc),
                error=str(e),
            )

    async def health_check(
        self,
        server_name: Optional[str] = None,
    ) -> Dict[str, HealthStatus]:
        """
        Check health of connected server(s).

        Args:
            server_name: Specific server to check (None = all)

        Returns:
            Health status per server
        """
        results = {}

        if server_name:
            if server_name in self._connections:
                results[server_name] = await self._health_check(
                    self._connections[server_name]
                )
        else:
            for name, client in self._connections.items():
                results[name] = await self._health_check(client)

        return results

    async def discover_tools(
        self,
        server_name: str,
    ) -> List[MCPTool]:
        """
        Discover available tools on a server.

        Args:
            server_name: Server to query

        Returns:
            List of available tools
        """
        if server_name not in self._connections:
            raise ConnectionError(f"Not connected to server: {server_name}")

        client = self._connections[server_name]

        try:
            response = await client.get("/tools")
            if response.status_code == 200:
                data = response.json()
                tools = [
                    MCPTool(
                        name=t.get("name", ""),
                        description=t.get("description", ""),
                        input_schema=t.get("input_schema", {}),
                        output_schema=t.get("output_schema"),
                    )
                    for t in data.get("tools", [])
                ]
                self._tools[server_name] = tools
                return tools

            return []

        except Exception:
            return []

    async def query(
        self,
        server_name: str,
        tool_name: str,
        params: Dict[str, Any],
        use_cache: bool = True,
    ) -> MCPResponse:
        """
        Execute a query/tool on a server.

        Args:
            server_name: Server to query
            tool_name: Tool to execute
            params: Tool parameters
            use_cache: Whether to use cached results

        Returns:
            MCPResponse with results
        """
        if server_name not in self._connections:
            return MCPResponse(
                success=False,
                error=f"Not connected to server: {server_name}",
            )

        # Check cache
        cache_key = f"{server_name}:{tool_name}:{json.dumps(params, sort_keys=True)}"
        if use_cache and cache_key in self._cache:
            cached = self._cache[cache_key]
            if (datetime.now(timezone.utc) - cached["timestamp"]).seconds < self._cache_ttl:
                return MCPResponse(
                    success=True,
                    data=cached["data"],
                    metadata={"cache_hit": True},
                )

        # Execute query
        client = self._connections[server_name]
        import time
        start = time.time()

        for attempt in range(self._retry_attempts):
            try:
                response = await client.post(
                    f"/tools/{tool_name}",
                    json=params,
                )
                latency = (time.time() - start) * 1000

                if response.status_code == 200:
                    data = response.json()

                    # Cache result
                    self._cache[cache_key] = {
                        "data": data,
                        "timestamp": datetime.now(timezone.utc),
                    }

                    return MCPResponse(
                        success=True,
                        data=data,
                        latency_ms=latency,
                        metadata={"attempt": attempt + 1},
                    )
                else:
                    if attempt == self._retry_attempts - 1:
                        return MCPResponse(
                            success=False,
                            error=f"HTTP {response.status_code}: {response.text}",
                            latency_ms=latency,
                        )

            except Exception as e:
                if attempt == self._retry_attempts - 1:
                    return MCPResponse(
                        success=False,
                        error=str(e),
                        latency_ms=(time.time() - start) * 1000,
                    )

            # Exponential backoff
            await asyncio.sleep(2 ** attempt)

        return MCPResponse(success=False, error="Max retries exceeded")

    def clear_cache(self, server_name: Optional[str] = None) -> None:
        """Clear the query cache."""
        if server_name:
            keys_to_remove = [k for k in self._cache if k.startswith(f"{server_name}:")]
            for key in keys_to_remove:
                del self._cache[key]
        else:
            self._cache.clear()

    def get_connected_servers(self) -> List[str]:
        """Get list of connected server names."""
        return list(self._connections.keys())

    def is_connected(self, server_name: str) -> bool:
        """Check if connected to a specific server."""
        return server_name in self._connections

    async def batch_query(
        self,
        server_name: str,
        queries: List[Dict[str, Any]],
    ) -> List[MCPResponse]:
        """
        Execute multiple queries in parallel.

        Args:
            server_name: Server to query
            queries: List of {"tool": str, "params": dict}

        Returns:
            List of responses
        """
        tasks = [
            self.query(server_name, q["tool"], q.get("params", {}))
            for q in queries
        ]
        return await asyncio.gather(*tasks)
