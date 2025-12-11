"""
Backend Engineer Agent for Claude Agents Orchestration System.

This agent handles Phase 4 code generation for:
- API design and implementation
- Database integration
- Authentication/authorization
- Server-side business logic
"""

from typing import Any, Dict, List, Optional

from agents.base_agent import (
    BaseAgent,
    AgentCapability,
    AgentContext,
    AgentResult,
)


class BackendEngineerAgent(BaseAgent):
    """
    Backend Engineer Agent for Phase 4.

    Responsible for:
    - API design (REST, GraphQL)
    - Database integration and queries
    - Authentication and authorization
    - Business logic implementation
    - Error handling and validation
    """

    agent_name = "backend_engineer"
    agent_description = "Backend development specialist for APIs, databases, and server-side logic"
    capabilities = [
        AgentCapability.API_DEVELOPMENT,
        AgentCapability.BACKEND_CODE,
    ]
    skills_file = "skills/backend_engineer.skills.md"
    phase = 4

    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute backend code generation phase.

        Args:
            context: Execution context with backend requirements

        Returns:
            AgentResult with generated backend code
        """
        try:
            prompt = self.build_prompt(context)
            system_prompt = self.get_system_prompt()

            response = await self.invoke_with_retry(prompt, system_prompt)

            # Extract code output
            code_output = self._extract_code_output(response)

            return AgentResult(
                success=True,
                output=code_output,
                artifacts=self._get_artifacts(code_output),
                metadata={
                    "phase": self.phase,
                    "agent": self.agent_name,
                    "files_generated": len(code_output.get("files", {})),
                },
            )

        except Exception as e:
            return AgentResult(
                success=False,
                output={},
                error_message=str(e),
            )

    def build_prompt(self, context: AgentContext) -> str:
        """Build the backend code generation prompt."""
        prompt_parts = [
            "# Backend Code Generation Request",
            "",
            f"## Task Description",
            context.task_description,
            "",
        ]

        # Add API requirements
        api_spec = context.input_data.get("api_specification", {})
        if api_spec:
            prompt_parts.extend([
                "## API Specification",
                f"Style: {api_spec.get('style', 'REST')}",
                f"Base Path: {api_spec.get('base_path', '/api/v1')}",
                "",
                "### Endpoints",
            ])
            for endpoint in api_spec.get("endpoints", []):
                prompt_parts.append(f"- {endpoint.get('method', 'GET')} {endpoint.get('path', '/')}: {endpoint.get('description', '')}")
            prompt_parts.append("")

        # Add database schema
        db_schema = context.input_data.get("database_schema", {})
        if db_schema:
            prompt_parts.extend([
                "## Database Schema",
                str(db_schema),
                "",
            ])

        # Add technology stack
        tech_stack = context.input_data.get("technology_stack", {})
        if tech_stack.get("backend"):
            prompt_parts.extend([
                "## Technology Stack",
                f"Language: {tech_stack['backend'].get('language', 'Python')}",
                f"Framework: {tech_stack['backend'].get('framework', 'FastAPI')}",
                "",
            ])

        # Add authentication requirements
        auth_config = context.input_data.get("authentication", {})
        if auth_config:
            prompt_parts.extend([
                "## Authentication",
                f"Type: {auth_config.get('type', 'JWT')}",
                f"Provider: {auth_config.get('provider', 'Custom')}",
                "",
            ])

        prompt_parts.extend([
            "## Required Output",
            "",
            "Generate complete backend code in JSON format:",
            "",
            "```json",
            "{",
            '  "files": {',
            '    "src/main.py": "# Main application entry point\\n...",',
            '    "src/routes/api.py": "# API routes\\n...",',
            '    "src/models/models.py": "# Database models\\n...",',
            '    "src/services/service.py": "# Business logic\\n...",',
            '    "src/middleware/auth.py": "# Authentication middleware\\n..."',
            "  },",
            '  "dependencies": {',
            '    "requirements.txt": "fastapi\\nuvicorn\\n..."',
            "  },",
            '  "configuration": {',
            '    "config.py": "# Configuration settings\\n..."',
            "  },",
            '  "tests": {',
            '    "tests/test_api.py": "# API tests\\n..."',
            "  },",
            '  "documentation": {',
            '    "openapi.json": "{...}",',
            '    "README.md": "# Backend Documentation\\n..."',
            "  }",
            "}",
            "```",
            "",
            "Ensure all code is:",
            "- Production-ready with proper error handling",
            "- Well-documented with docstrings",
            "- Following best practices and design patterns",
            "- Type-hinted (for Python)",
            "- Secure (no hardcoded secrets, proper validation)",
        ])

        return "\n".join(prompt_parts)

    def _extract_code_output(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract code files from response."""
        if isinstance(response, dict):
            if "files" in response:
                return response

            if "text" in response:
                import json
                try:
                    text = response["text"]
                    start = text.find("{")
                    end = text.rfind("}") + 1
                    if start != -1 and end > start:
                        return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass

        return {
            "files": {},
            "dependencies": {},
            "tests": {},
            "raw_response": response,
        }

    def _get_artifacts(self, output: Dict[str, Any]) -> List[str]:
        """Get list of generated artifact paths."""
        artifacts = []

        for category in ["files", "dependencies", "configuration", "tests", "documentation"]:
            if category in output:
                artifacts.extend(output[category].keys())

        return artifacts
