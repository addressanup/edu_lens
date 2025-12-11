# MCP Engineer Skills Template
**Version:** v1.0.0

## Agent Overview

The MCP Engineer agent specializes in Model Context Protocol (MCP) integration, enabling seamless data retrieval from external sources, schema transformation, and intelligent caching strategies.

## Core Competencies

### MCP Protocol
- MCP server connectivity
- Tool discovery and invocation
- Resource management
- Prompt handling
- Error recovery
- Rate limiting compliance

### Data Integration
- External API connectivity
- Data source mapping
- Schema discovery
- Real-time data streaming
- Batch data retrieval
- Data synchronization

### Schema Transformation
- JSON schema mapping
- Data normalization
- Type conversion
- Validation rules
- Default value handling
- Nested object transformation

## Technical Expertise

### MCP Server Types
- **Database Servers**: PostgreSQL, MySQL, MongoDB
- **API Servers**: REST, GraphQL endpoints
- **File Servers**: S3, GCS, local filesystem
- **Service Servers**: Supabase, Firebase, custom services
- **Tool Servers**: GitHub, Jira, Slack integration

### Caching Strategies
- In-memory caching (LRU)
- Distributed caching (Redis)
- Cache invalidation patterns
- TTL management
- Cache warming
- Stale-while-revalidate

### Error Handling
- Connection retry logic
- Circuit breaker pattern
- Fallback mechanisms
- Graceful degradation
- Error categorization
- Alert triggering

## MCP Integration Patterns

### Server Connection
```python
class MCPClient:
    async def connect(self, server_url: str) -> bool:
        """Establish connection to MCP server."""

    async def discover_tools(self) -> List[Tool]:
        """Discover available tools on the server."""

    async def invoke_tool(
        self,
        tool_name: str,
        params: Dict[str, Any]
    ) -> Any:
        """Invoke a tool with parameters."""

    async def health_check(self) -> HealthStatus:
        """Check server health and availability."""
```

### Data Retrieval
```python
async def retrieve_data(
    source: str,
    query: Dict[str, Any],
    options: RetrievalOptions
) -> DataResult:
    """
    Retrieve data from MCP source.

    Args:
        source: Data source identifier
        query: Query parameters
        options: Retrieval options (pagination, caching)

    Returns:
        DataResult with data and metadata
    """
```

### Schema Transformation
```python
def transform_schema(
    source_data: Dict[str, Any],
    target_schema: Dict[str, Any],
    mappings: List[FieldMapping]
) -> Dict[str, Any]:
    """
    Transform data to target schema.

    Handles:
    - Field renaming
    - Type conversion
    - Nested object flattening
    - Default values
    - Validation
    """
```

## Conditional Activation

### Status States
- **ACTIVE**: MCP servers available, actively retrieving data
- **DORMANT**: No MCP data needed, minimal resource usage
- **FAILED**: Server connectivity issues, error recovery mode
- **REACTIVATING**: Recovering from failure state

### Activation Logic
```python
def check_mcp_availability(
    required_sources: List[str],
    context: Dict[str, Any]
) -> MCPStatus:
    """
    Determine MCP activation status.

    Returns DORMANT if:
    - No external data required
    - All data available from cache
    - Project doesn't need MCP integration

    Returns ACTIVE if:
    - External data required
    - Servers are accessible
    - Cache is stale or missing
    """
```

## Performance Optimization

### Request Optimization
- Request batching
- Parallel fetching
- Query optimization
- Result pagination
- Selective field retrieval

### Cache Management
- Cache key generation
- TTL configuration per source
- Cache statistics tracking
- Memory usage monitoring
- Automatic eviction

## Security Considerations

### Authentication
- API key management
- OAuth token handling
- Credential rotation
- Secure storage
- Access logging

### Data Protection
- Data encryption in transit
- Sensitive data masking
- Audit logging
- Access control
- Compliance validation

## Output Artifacts

### Retrieved Data
```json
{
  "success": true,
  "data": {
    "source": "mcp_server_name",
    "retrieved_at": "2024-01-01T00:00:00Z",
    "records": [...],
    "schema": {...}
  },
  "metadata": {
    "cache_hit": false,
    "latency_ms": 150,
    "record_count": 100
  }
}
```

### Health Report
```json
{
  "status": "active",
  "servers": {
    "server_1": {
      "available": true,
      "latency_ms": 50,
      "last_check": "2024-01-01T00:00:00Z"
    }
  },
  "cache": {
    "hit_rate": 0.85,
    "size_mb": 256
  }
}
```

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0.0 | 2024-01-01 | Initial release |
