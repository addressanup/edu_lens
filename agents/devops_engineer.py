"""
DevOps Engineer Agent for Claude Agents Orchestration System.

This agent handles Phase 6 deployment:
- Deployment scripts
- Kubernetes manifests
- Monitoring setup
- CI/CD pipelines
- Disaster recovery
"""

from typing import Any, Dict, List, Optional

from agents.base_agent import (
    BaseAgent,
    AgentCapability,
    AgentContext,
    AgentResult,
)


class DevOpsEngineerAgent(BaseAgent):
    """
    DevOps Engineer Agent for Phase 6.

    Responsible for:
    - Deployment script generation
    - Kubernetes manifest creation
    - Monitoring and alerting setup
    - CI/CD pipeline configuration
    - Disaster recovery planning
    - Infrastructure documentation
    """

    agent_name = "devops_engineer"
    agent_description = "DevOps specialist for deployment, monitoring, and infrastructure automation"
    capabilities = [
        AgentCapability.DEPLOYMENT,
        AgentCapability.MONITORING,
        AgentCapability.DISASTER_RECOVERY,
    ]
    skills_file = "skills/devops_engineer.skills.md"
    phase = 6

    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute deployment phase.

        Args:
            context: Execution context with deployment requirements

        Returns:
            AgentResult with deployment configuration
        """
        try:
            prompt = self.build_prompt(context)
            system_prompt = self.get_system_prompt()

            response = await self.invoke_with_retry(prompt, system_prompt)

            # Extract deployment configuration
            deployment_config = self._extract_deployment_config(response)

            return AgentResult(
                success=True,
                output=deployment_config,
                artifacts=self._get_deployment_artifacts(deployment_config),
                metadata={
                    "phase": self.phase,
                    "agent": self.agent_name,
                    "deployment_ready": deployment_config.get("deployment_ready", False),
                },
            )

        except Exception as e:
            return AgentResult(
                success=False,
                output={},
                error_message=str(e),
            )

    def build_prompt(self, context: AgentContext) -> str:
        """Build the deployment configuration prompt."""
        prompt_parts = [
            "# Deployment Configuration Request",
            "",
            f"## Task Description",
            context.task_description,
            "",
        ]

        # Add infrastructure requirements
        infra = context.input_data.get("infrastructure", {})
        if infra:
            prompt_parts.extend([
                "## Infrastructure",
                f"Cloud Provider: {infra.get('provider', 'Not specified')}",
                f"Region: {infra.get('region', 'Not specified')}",
                "",
            ])

        # Add technology stack
        tech_stack = context.input_data.get("technology_stack", {})
        if tech_stack:
            prompt_parts.extend([
                "## Technology Stack",
                str(tech_stack),
                "",
            ])

        # Add scaling requirements
        scaling = context.input_data.get("scaling", {})
        if scaling:
            prompt_parts.extend([
                "## Scaling Requirements",
                f"Min Replicas: {scaling.get('min_replicas', 1)}",
                f"Max Replicas: {scaling.get('max_replicas', 10)}",
                f"Target CPU: {scaling.get('target_cpu', '80%')}",
                "",
            ])

        # Add monitoring requirements
        monitoring = context.input_data.get("monitoring", {})
        if monitoring:
            prompt_parts.extend([
                "## Monitoring Requirements",
                str(monitoring),
                "",
            ])

        prompt_parts.extend([
            "## Required Output",
            "",
            "```json",
            "{",
            '  "deployment_ready": true,',
            '  "kubernetes": {',
            '    "deployment.yaml": "apiVersion: apps/v1\\nkind: Deployment\\n...",',
            '    "service.yaml": "apiVersion: v1\\nkind: Service\\n...",',
            '    "ingress.yaml": "apiVersion: networking.k8s.io/v1\\nkind: Ingress\\n...",',
            '    "configmap.yaml": "apiVersion: v1\\nkind: ConfigMap\\n...",',
            '    "secrets.yaml": "apiVersion: v1\\nkind: Secret\\n...",',
            '    "hpa.yaml": "apiVersion: autoscaling/v2\\nkind: HorizontalPodAutoscaler\\n..."',
            "  },",
            '  "docker": {',
            '    "Dockerfile": "FROM python:3.11-slim\\n...",',
            '    "docker-compose.yml": "version: 3.8\\nservices:\\n...",',
            '    ".dockerignore": "*.pyc\\n..."',
            "  },",
            '  "cicd": {',
            '    ".github/workflows/deploy.yml": "name: Deploy\\n...",',
            '    "scripts/deploy.sh": "#!/bin/bash\\n..."',
            "  },",
            '  "monitoring": {',
            '    "prometheus/alerts.yml": "groups:\\n...",',
            '    "grafana/dashboard.json": "{...}",',
            '    "logging/fluentd.conf": "..."',
            "  },",
            '  "disaster_recovery": {',
            '    "backup_strategy": "Description of backup approach",',
            '    "restore_procedure": "Step-by-step restore process",',
            '    "rpo_minutes": 15,',
            '    "rto_minutes": 60,',
            '    "scripts": {',
            '      "backup.sh": "#!/bin/bash\\n...",',
            '      "restore.sh": "#!/bin/bash\\n..."',
            "    }",
            "  },",
            '  "documentation": {',
            '    "DEPLOYMENT.md": "# Deployment Guide\\n...",',
            '    "RUNBOOK.md": "# Operations Runbook\\n..."',
            "  }",
            "}",
            "```",
            "",
            "Ensure all configurations are:",
            "- Production-ready with proper resource limits",
            "- Secure (no hardcoded secrets)",
            "- Highly available with proper replicas",
            "- Observable with logging and metrics",
            "- Documented for operations team",
        ])

        return "\n".join(prompt_parts)

    def _extract_deployment_config(
        self,
        response: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract deployment configuration from response."""
        if isinstance(response, dict):
            if "kubernetes" in response or "docker" in response:
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
            "deployment_ready": False,
            "kubernetes": {},
            "docker": {},
            "cicd": {},
            "monitoring": {},
            "disaster_recovery": {},
            "documentation": {},
            "raw_response": response,
        }

    def _get_deployment_artifacts(
        self,
        config: Dict[str, Any],
    ) -> List[str]:
        """Get list of deployment artifact paths."""
        artifacts = []

        for category in ["kubernetes", "docker", "cicd", "monitoring", "documentation"]:
            if category in config and isinstance(config[category], dict):
                artifacts.extend(config[category].keys())

        dr_scripts = config.get("disaster_recovery", {}).get("scripts", {})
        if dr_scripts:
            artifacts.extend(dr_scripts.keys())

        return artifacts
