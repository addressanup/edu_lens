"""
Integration Engineer Agent for Claude Agents Orchestration System.

This agent handles Phase 3 of the orchestration pipeline:
- Infrastructure provisioning
- Database setup
- Repository configuration
- CI/CD pipeline setup
"""

from typing import Any, Dict, List, Optional

from agents.base_agent import (
    BaseAgent,
    AgentCapability,
    AgentContext,
    AgentResult,
)


class IntegrationEngineerAgent(BaseAgent):
    """
    Integration Engineer Agent for Phase 3.

    Responsible for:
    - Cloud infrastructure provisioning (Terraform)
    - Database setup (Supabase, PostgreSQL)
    - Repository configuration (GitHub, GitLab)
    - CI/CD pipeline setup
    - Environment configuration
    """

    agent_name = "integration_engineer"
    agent_description = "Infrastructure and integration specialist for cloud provisioning and DevOps setup"
    capabilities = [
        AgentCapability.CLOUD_PROVISIONING,
        AgentCapability.DATABASE_SETUP,
        AgentCapability.CICD_CONFIGURATION,
    ]
    skills_file = "skills/integration_engineer.skills.md"
    phase = 3

    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute infrastructure setup phase.

        Args:
            context: Execution context with infrastructure requirements

        Returns:
            AgentResult with infrastructure configuration
        """
        try:
            prompt = self.build_prompt(context)
            system_prompt = self.get_system_prompt()

            response = await self.invoke_with_retry(prompt, system_prompt)

            # Extract infrastructure configuration
            infra_config = self._extract_infrastructure_config(response)

            return AgentResult(
                success=True,
                output=infra_config,
                artifacts=self._generate_artifacts(infra_config),
                metadata={
                    "phase": self.phase,
                    "agent": self.agent_name,
                },
            )

        except Exception as e:
            return AgentResult(
                success=False,
                output={},
                error_message=str(e),
            )

    def build_prompt(self, context: AgentContext) -> str:
        """Build the infrastructure setup prompt."""
        prompt_parts = [
            "# Infrastructure Setup Request",
            "",
            f"## Project Description",
            context.task_description,
            "",
        ]

        # Add technology stack requirements
        tech_stack = context.input_data.get("technology_stack", {})
        if tech_stack:
            prompt_parts.extend([
                "## Technology Stack",
                f"Backend: {tech_stack.get('backend', {})}",
                f"Frontend: {tech_stack.get('frontend', {})}",
                f"Database: {tech_stack.get('database', {})}",
                f"Infrastructure: {tech_stack.get('infrastructure', {})}",
                "",
            ])

        # Add architecture requirements
        architecture = context.input_data.get("architecture", {})
        if architecture:
            prompt_parts.extend([
                "## Architecture",
                f"Pattern: {architecture.get('pattern', 'Not specified')}",
                f"Components: {architecture.get('components', [])}",
                "",
            ])

        # Add constraints
        if context.constraints:
            prompt_parts.extend([
                "## Constraints",
                str(context.constraints),
                "",
            ])

        prompt_parts.extend([
            "## Required Output",
            "",
            "Please provide infrastructure configuration in JSON format:",
            "",
            "```json",
            "{",
            '  "database": {',
            '    "provisioned": true,',
            '    "type": "PostgreSQL",',
            '    "provider": "Supabase|AWS RDS|etc",',
            '    "connection_string_var": "DATABASE_URL",',
            '    "setup_commands": ["command1", "command2"],',
            '    "migrations": ["migration file paths"]',
            "  },",
            '  "repository": {',
            '    "created": true,',
            '    "provider": "GitHub|GitLab",',
            '    "name": "repo-name",',
            '    "branch_protection": true,',
            '    "setup_commands": ["git commands"]',
            "  },",
            '  "cicd": {',
            '    "configured": true,',
            '    "provider": "GitHub Actions|GitLab CI",',
            '    "pipeline_file": ".github/workflows/ci.yml",',
            '    "stages": ["lint", "test", "build", "deploy"],',
            '    "pipeline_content": "YAML content"',
            "  },",
            '  "infrastructure": {',
            '    "provider": "AWS|GCP|Azure",',
            '    "terraform_files": {',
            '      "main.tf": "terraform content",',
            '      "variables.tf": "variables content"',
            "    },",
            '    "resources": ["list of resources to provision"]',
            "  },",
            '  "environment_variables": {',
            '    "DATABASE_URL": "placeholder",',
            '    "API_KEY": "placeholder",',
            '    "SECRET_KEY": "placeholder"',
            "  },",
            '  "security": {',
            '    "ssl_enabled": true,',
            '    "firewall_configured": true,',
            '    "secrets_management": "AWS Secrets Manager|Vault"',
            "  }",
            "}",
            "```",
        ])

        return "\n".join(prompt_parts)

    def _extract_infrastructure_config(
        self,
        response: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract infrastructure configuration from response."""
        if isinstance(response, dict):
            # Check for expected structure
            expected_keys = ["database", "repository", "cicd", "infrastructure"]
            if any(key in response for key in expected_keys):
                return response

            # Try to extract from text
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

        # Return minimal structure
        return {
            "database": {"provisioned": False},
            "repository": {"created": False},
            "cicd": {"configured": False},
            "infrastructure": {"configured": False},
            "environment_variables": {},
            "security": {},
            "raw_response": response,
        }

    def _generate_artifacts(
        self,
        config: Dict[str, Any],
    ) -> List[str]:
        """Generate list of artifact paths."""
        artifacts = []

        # Terraform files
        tf_files = config.get("infrastructure", {}).get("terraform_files", {})
        for filename in tf_files.keys():
            artifacts.append(f"infrastructure/{filename}")

        # CI/CD pipeline
        if config.get("cicd", {}).get("pipeline_file"):
            artifacts.append(config["cicd"]["pipeline_file"])

        return artifacts
