# Claude Agents Orchestration - Workflow Guide

This guide explains how to use the orchestration system to generate a complete software project.

---

## Prerequisites

- Python 3.10+
- Docker and Docker Compose
- Claude CLI installed and authenticated (`claude` command available)

---

## Step 1: Setup the Orchestration System

```bash
# Navigate to the orchestration system
cd /path/to/claude-agents-orchestration

# Install the package
pip install -e .

# Start supporting services (PostgreSQL + Redis)
docker-compose up -d

# Copy and configure environment
cp .env.example .env
# Edit .env with your settings if needed
```

---

## Step 2: Create Your Project Specification

```bash
# Create a new directory for your greenfield project
mkdir ~/my-new-app
cd ~/my-new-app

# Create a project specification file
cat > project_spec.json << 'EOF'
{
  "name": "my-new-app",
  "description": "A web application that does XYZ",
  "features": [
    {
      "name": "User Authentication",
      "description": "Login, registration, password reset",
      "priority": "high"
    },
    {
      "name": "Dashboard",
      "description": "Main user dashboard with analytics",
      "priority": "high"
    },
    {
      "name": "API Integration",
      "description": "REST API for mobile clients",
      "priority": "medium"
    }
  ],
  "type": "web_application",
  "technical": {
    "frontend": {"framework": "react"},
    "backend": {"language": "python", "framework": "fastapi"},
    "database": "postgresql"
  }
}
EOF
```

For a more detailed specification template, see `templates/project_spec_template.md`.

---

## Step 3: Run the Orchestration

### Option A: Use the CLI

```bash
cao run --spec project_spec.json --name my-new-app --output ./output
```

### Option B: Use Python directly

```python
import asyncio
from orchestrator.orchestrator import ClaudeAgentsOrchestrator
import json

async def main():
    orch = ClaudeAgentsOrchestrator(output_dir='./output')
    await orch.initialize()

    with open('project_spec.json') as f:
        spec = json.load(f)

    result = await orch.run_project(
        project_name='my-new-app',
        specification=spec,
        budget_usd=50.0  # Optional cost limit
    )
    print(json.dumps(result, indent=2))

asyncio.run(main())
```

### Option C: With MCP Integration (External Data Sources)

```bash
cao run --spec project_spec.json --name my-new-app --enable-mcp --mcp-config mcp_servers.json
```

---

## Step 4: What Happens Automatically

The orchestrator runs **6 phases** sequentially:

```
Phase 1: CONCEPT DESIGN
   └── ConceptDesigner agent creates project vision, user stories, feature breakdown
   └── Validation Gate: Checks completeness (>70% confidence to proceed)

Phase 2: ARCHITECTURE
   └── MCPEngineer designs data integrations
   └── IntegrationEngineer designs system architecture
   └── Validation Gate: Architecture review

Phase 3: IMPLEMENTATION
   └── BackendEngineer generates API, models, services
   └── FrontendEngineer generates UI components, pages
   └── Validation Gate: Code quality check

Phase 4: TESTING
   └── QAEngineer generates test suites (unit, integration, e2e)
   └── Validation Gate: Test coverage check

Phase 5: SECURITY
   └── SecurityEngineer audits code, generates security configs
   └── Validation Gate: Security compliance

Phase 6: DEPLOYMENT
   └── DevOpsEngineer generates Docker, K8s, CI/CD configs
   └── Final package generation
```

### Validation Gate Thresholds

| Confidence Score | Action |
|------------------|--------|
| > 70% | Proceed to next phase |
| 50-70% | Human review required |
| < 50% | Halt and request clarification |

### Error Recovery Levels

| Level | Trigger | Action |
|-------|---------|--------|
| Level 1 | Transient errors | Retry (up to 3 times) |
| Level 2 | Phase failure | Rollback to previous phase |
| Level 3 | Critical failure | Full rollback to start |

---

## Step 5: Review Output

```bash
# Check generated output
ls -la ./output/my-new-app/

# Structure will be:
# output/my-new-app/
# ├── phase_1_concept/
# │   └── concept_designer_output.json
# ├── phase_2_architecture/
# │   ├── mcp_engineer_output.json
# │   └── integration_engineer_output.json
# ├── phase_3_implementation/
# │   ├── backend_engineer_output.json
# │   └── frontend_engineer_output.json
# ├── phase_4_testing/
# │   └── qa_engineer_output.json
# ├── phase_5_security/
# │   └── security_engineer_output.json
# ├── phase_6_deployment/
# │   └── devops_engineer_output.json
# └── summary.json
```

---

## Step 6: Monitor Progress (While Running)

```bash
# In another terminal, check status
cao status

# View checkpoints (for resume if interrupted)
cao checkpoints --project my-new-app

# If interrupted, resume from last checkpoint
cao resume --checkpoint <checkpoint-id>

# Inspect a specific agent's last output
cao inspect --agent backend_engineer
```

---

## Step 7: Use the Generated Code

The agents output code snippets and file contents in their JSON outputs. Extract and organize them into your project structure:

```bash
# Navigate to your project
cd ~/my-new-app

# Example: Parse backend engineer output and create files
python << 'EOF'
import json
import os

with open('./output/my-new-app/phase_3_implementation/backend_engineer_output.json') as f:
    output = json.load(f)

# Create files from output
for filename, content in output.get('files', {}).items():
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w') as f:
        f.write(content)
    print(f"Created: {filename}")
EOF
```

---

## CLI Reference

| Command | Purpose |
|---------|---------|
| `cao run --spec spec.json` | Start new project |
| `cao run --spec spec.json --enable-mcp` | Start with MCP integration |
| `cao status` | Check current orchestration status |
| `cao checkpoints` | List all saved checkpoints |
| `cao checkpoints --project NAME` | List checkpoints for specific project |
| `cao resume --checkpoint ID` | Resume from a checkpoint |
| `cao agents` | List all available agents |
| `cao inspect --agent NAME` | View agent's last output |
| `cao validate --spec spec.json` | Validate specification before running |

---

## Example: Complete Session

```bash
# 1. Setup (one-time)
cd /path/to/claude-agents-orchestration
pip install -e .
docker-compose up -d

# 2. Create project directory
mkdir ~/my-saas-app && cd ~/my-saas-app

# 3. Copy and edit specification template
cp /path/to/claude-agents-orchestration/templates/project_spec_template.md ./
# Edit the template with your requirements
# Convert to JSON format (see template for JSON schema)

# 4. Validate specification
cao validate --spec project_spec.json

# 5. Run orchestration
cao run --spec project_spec.json --name my-saas-app

# 6. Monitor progress (in another terminal)
watch cao status

# 7. If interrupted, find checkpoint and resume
cao checkpoints --project my-saas-app
cao resume --checkpoint <checkpoint-id>

# 8. Review outputs
cat ./output/my-saas-app/summary.json | jq .

# 9. Extract generated code to your project
# (see Step 7 above)
```

---

## Configuration Options

### Environment Variables (.env)

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `CLAUDE_CLI_PATH` | Path to Claude CLI | `claude` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `CONTEXT_BUDGET` | Max tokens per session | `200000` |
| `DEFAULT_MODEL` | Claude model tier | `sonnet` |

### Budget Management

Set a cost budget to prevent runaway costs:

```bash
cao run --spec spec.json --budget 50.0  # $50 USD limit
```

The system will:
- Track token usage per agent/phase
- Alert at 75% budget utilization
- Stop at 90% budget utilization

---

## Troubleshooting

### Common Issues

**1. Claude CLI not found**
```bash
# Ensure Claude CLI is installed and in PATH
which claude
# If not found, install it or set CLAUDE_CLI_PATH in .env
```

**2. Docker services not running**
```bash
docker-compose ps
# If not running:
docker-compose up -d
```

**3. Database connection failed**
```bash
# Check PostgreSQL is accessible
docker-compose logs postgres
# Verify DATABASE_URL in .env
```

**4. Validation gate failures**
```bash
# Check the validation result in phase output
cat ./output/project/phase_N_*/validation_result.json
# Review confidence score and issues
```

**5. Resume not working**
```bash
# List available checkpoints
cao checkpoints
# Ensure checkpoint ID is correct
cao resume --checkpoint <full-checkpoint-id>
```

---

## Agent Capabilities Reference

| Agent | Capabilities | Phase |
|-------|--------------|-------|
| ConceptDesigner | Project vision, user stories, feature specs | 1 |
| MCPEngineer | External data integration design | 2 |
| IntegrationEngineer | System architecture, API design | 2 |
| BackendEngineer | API code, models, services, backend tests | 3 |
| FrontendEngineer | UI components, pages, state management | 3 |
| QAEngineer | Test suites, coverage analysis | 4 |
| SecurityEngineer | Security audit, vulnerability fixes | 5 |
| DevOpsEngineer | Docker, K8s, CI/CD, monitoring | 6 |

---

## Further Reading

- `templates/project_spec_template.md` - Detailed specification format
- `templates/architecture_template.md` - Architecture document template
- `templates/deployment_template.yaml` - Kubernetes deployment template
- `skills/*.skills.md` - Individual agent capability definitions
