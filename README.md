# Claude Agents Orchestration System

A multi-agent AI orchestration platform for end-to-end software project delivery. This system coordinates specialized AI agents to handle the complete software development lifecycle - from concept design through deployment.

## Overview

The Claude Agents Orchestration System uses a phased approach where specialized agents collaborate through a central orchestrator:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CLAUDE AGENTS ORCHESTRATOR                       │
├─────────────────────────────────────────────────────────────────────┤
│  Phase 1    Phase 2    Phase 3    Phase 4    Phase 5    Phase 6    │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐      │
│  │Concept│→│ MCP  │→│Infra │→│ Code │→│  QA  │→│Deploy│      │
│  │Design │  │ Data │  │Setup │  │ Gen  │  │ Test │  │ Ship │      │
│  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘      │
│      ↓         ↓         ↓         ↓         ↓         ↓          │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐      │
│  │Gate 1│  │Gate 2│  │Gate 3│  │Gate 4│  │Gate 5│  │Output│      │
│  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘      │
└─────────────────────────────────────────────────────────────────────┘
```

## Quick Start

> **For detailed step-by-step instructions, see [WORKFLOW.md](./WORKFLOW.md)**

### 1. Clone and Setup

```bash
git clone https://github.com/your-org/claude-agents-orchestration.git
cd claude-agents-orchestration
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Start Infrastructure

```bash
docker-compose up -d
```

### 4. Initialize Database

```bash
alembic upgrade head
```

### 5. Run the Orchestrator

```bash
# Interactive mode
python cli.py run --project "My New Project"

# With specific configuration
python cli.py run --project "My New Project" --config ./my-config.yaml
```

## Project Structure

```
claude-agents-orchestration/
├── orchestrator/           # Core orchestration engine
│   ├── orchestrator.py     # Main orchestrator class (520+ lines)
│   ├── config.py           # Configuration management
│   ├── logger.py           # 5-level logging system
│   └── state_manager.py    # State persistence with SQLAlchemy
├── core/                   # Core systems
│   ├── message_broker.py   # Priority-based message queuing
│   ├── communication_protocol.py  # Inter-agent messaging
│   ├── validation_gates.py # 5 validation gates with scoring
│   ├── error_recovery.py   # 3-level error recovery
│   └── context_budget.py   # Token budget management
├── agents/                 # Specialized AI agents
│   ├── base_agent.py       # Abstract base class
│   ├── concept_designer.py # Requirements & architecture
│   ├── mcp_engineer.py     # MCP data integration
│   ├── integration_engineer.py  # Infrastructure setup
│   ├── backend_engineer.py # Server-side code
│   ├── frontend_engineer.py # UI components
│   ├── security_engineer.py # Security scanning
│   ├── qa_engineer.py      # Testing & validation
│   └── devops_engineer.py  # Deployment & CI/CD
├── skills/                 # Agent capability templates
├── database/               # Data persistence layer
│   ├── models.py           # SQLAlchemy models
│   ├── schema.sql          # PostgreSQL schema
│   └── migrations/         # Alembic migrations
├── utils/                  # Utility modules
├── templates/              # Project templates
└── tests/                  # Test suite
```

## Key Features

### Multi-Agent Architecture
- **8 Specialized Agents**: Each agent has deep expertise in their domain
- **Skills Templates**: Markdown-based capability definitions (v1.0.0)
- **CLI Invocation**: Uses Claude Code CLI for agent execution

### Validation Gates
- **5-Stage Validation**: Each phase has quality gates
- **Confidence Scoring**: Automatic pass (>70%), review (50-70%), halt (<50%)
- **Issue Tracking**: Detailed remediation suggestions

### Error Recovery
- **Level 1**: Agent retry (3 attempts, 10 min timeout)
- **Level 2**: Phase rollback (2 attempts, 30 min timeout)
- **Level 3**: Full rollback with human intervention

### Context Budget Management
- **200k Token Allocation**: Distributed across processing phases
- **Progressive Summarization**: Maintains context efficiency
- **Real-time Tracking**: Monitor token usage per agent

### Logging & Compliance
- **5-Level Logging**: Event, Decision, Trace, Error, Audit
- **7-Year Retention**: Compliance-ready audit logs
- **Structured Output**: JSON-formatted for analysis

## Technology Stack

| Component | Technology |
|-----------|------------|
| Runtime | Python 3.11+ |
| AI Engine | Claude Code CLI |
| Database | PostgreSQL 15+ |
| Cache/Queue | Redis 7+ |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| CLI | Click |
| Async | asyncio, aiohttp |
| Logging | Loguru |
| Testing | pytest, pytest-asyncio |

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Runtime environment | `local` |
| `LOG_LEVEL` | Logging verbosity | `DEBUG` |
| `CONTEXT_BUDGET` | Total token budget | `200000` |
| `MAX_RETRIES` | Agent retry attempts | `3` |
| `VALIDATION_STRICTNESS` | Gate strictness | `LOW` |
| `STATE_STORE` | Database connection | `sqlite:///:memory:` |
| `REDIS_URL` | Redis connection | `redis://localhost:6379` |
| `MCP_TIMEOUT` | MCP operation timeout | `60` |

### Validation Strictness Levels

- **LOW**: 50% threshold for pass
- **MEDIUM**: 60% threshold for pass
- **HIGH**: 70% threshold for pass
- **STRICT**: 80% threshold for pass

## Agent Capabilities

| Agent | Primary Responsibility |
|-------|----------------------|
| Concept Designer | Requirements analysis, architecture decisions |
| MCP Engineer | External data integration via MCP servers |
| Integration Engineer | Infrastructure provisioning (Terraform, CI/CD) |
| Backend Engineer | API design, database integration |
| Frontend Engineer | UI components, state management |
| Security Engineer | SAST scanning, OWASP validation |
| QA Engineer | Test generation, coverage analysis |
| DevOps Engineer | Deployment, monitoring, disaster recovery |

## Contributing

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Code formatting
black .
isort .

# Linting
flake8 .
```

### Code Style

- Follow PEP 8 guidelines
- Use type hints throughout
- Write comprehensive docstrings (Google style)
- Maintain >80% test coverage

### Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit PR with clear description

## License

MIT License - See LICENSE file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/your-org/claude-agents-orchestration/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/claude-agents-orchestration/discussions)
- **Documentation**: [Wiki](https://github.com/your-org/claude-agents-orchestration/wiki)
