"""
Concept Designer Agent for Claude Agents Orchestration System.

This agent handles Phase 1 of the orchestration pipeline:
- Requirements analysis
- Architecture design
- Technology stack selection
- Deliverables definition
"""

from typing import Any, Dict, List, Optional

from agents.base_agent import (
    AgentCapability,
    AgentContext,
    AgentResult,
    BaseAgent,
)


class ConceptDesignerAgent(BaseAgent):
    """
    Concept Designer Agent for Phase 1.

    Responsible for:
    - Analyzing project requirements
    - Designing system architecture
    - Selecting technology stack
    - Defining deliverables and milestones
    - Identifying risks and constraints
    """

    agent_name = "concept_designer"
    agent_description = "Expert architect specializing in requirements analysis and system design"
    capabilities = [
        AgentCapability.REQUIREMENTS_ANALYSIS,
        AgentCapability.ARCHITECTURE_DESIGN,
        AgentCapability.TECH_STACK_SELECTION,
    ]
    skills_file = "skills/concept_designer.skills.md"
    phase = 1

    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute concept design phase.

        Args:
            context: Execution context with project requirements

        Returns:
            AgentResult with project specification
        """
        # Build the prompt
        prompt = self.build_prompt(context)
        system_prompt = self.get_system_prompt()

        # Invoke Claude
        try:
            response = await self.invoke_with_retry(prompt, system_prompt)

            # Extract project specification from response
            project_spec = self._extract_project_spec(response)

            return AgentResult(
                success=True,
                output=project_spec,
                artifacts=[],
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
        """Build the concept design prompt."""
        prompt_parts = [
            "# Project Concept Design Request",
            "",
            f"## Task Description",
            context.task_description,
            "",
        ]

        # Add any existing requirements
        if context.input_data.get("requirements"):
            prompt_parts.extend(
                [
                    "## Initial Requirements",
                    str(context.input_data["requirements"]),
                    "",
                ]
            )

        # Add constraints
        if context.constraints:
            prompt_parts.extend(
                [
                    "## Constraints",
                    str(context.constraints),
                    "",
                ]
            )

        # Add the request
        prompt_parts.extend(
            [
                "## Required Output",
                "",
                "Please provide a comprehensive project specification in JSON format with the following structure:",
                "",
                "```json",
                "{",
                '  "project_overview": {',
                '    "name": "Project name",',
                '    "description": "Brief description",',
                '    "objectives": ["objective1", "objective2"],',
                '    "scope": "Project scope definition"',
                "  },",
                '  "requirements": [',
                "    {",
                '      "id": "REQ-001",',
                '      "type": "functional|non-functional",',
                '      "priority": "high|medium|low",',
                '      "description": "Requirement description",',
                '      "acceptance_criteria": ["criterion1", "criterion2"]',
                "    }",
                "  ],",
                '  "architecture": {',
                '    "pattern": "microservices|monolith|serverless",',
                '    "components": [',
                "      {",
                '        "name": "Component name",',
                '        "responsibility": "What it does",',
                '        "interfaces": ["interface1"]',
                "      }",
                "    ],",
                '    "data_flow": "Description of data flow",',
                '    "integrations": ["external systems"]',
                "  },",
                '  "technology_stack": {',
                '    "backend": {',
                '      "language": "Python/Node.js/etc",',
                '      "framework": "Framework name",',
                '      "rationale": "Why this choice"',
                "    },",
                '    "frontend": {',
                '      "framework": "React/Vue/etc",',
                '      "rationale": "Why this choice"',
                "    },",
                '    "database": {',
                '      "type": "PostgreSQL/MongoDB/etc",',
                '      "rationale": "Why this choice"',
                "    },",
                '    "infrastructure": {',
                '      "cloud": "AWS/GCP/Azure",',
                '      "services": ["service1", "service2"]',
                "    }",
                "  },",
                '  "deliverables": [',
                "    {",
                '      "name": "Deliverable name",',
                '      "description": "What it includes",',
                '      "dependencies": ["dep1"]',
                "    }",
                "  ],",
                '  "risks": [',
                "    {",
                '      "id": "RISK-001",',
                '      "description": "Risk description",',
                '      "probability": "high|medium|low",',
                '      "impact": "high|medium|low",',
                '      "mitigation": "How to mitigate"',
                "    }",
                "  ],",
                '  "acceptance_criteria": [',
                '    "Criterion 1",',
                '    "Criterion 2"',
                "  ]",
                "}",
                "```",
                "",
                "Ensure your response is valid JSON and covers all aspects thoroughly.",
            ]
        )

        return "\n".join(prompt_parts)

    def _extract_project_spec(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and validate project specification from response."""
        # If response is already structured
        if isinstance(response, dict):
            # Check for expected keys
            expected_keys = [
                "project_overview",
                "requirements",
                "architecture",
                "technology_stack",
                "deliverables",
            ]

            # If it has the expected structure, return it
            if any(key in response for key in expected_keys):
                return response

            # If it has a text/content field, try to parse it
            if "text" in response:
                import json

                try:
                    # Try to extract JSON from the text
                    text = response["text"]
                    # Find JSON block
                    start = text.find("{")
                    end = text.rfind("}") + 1
                    if start != -1 and end > start:
                        return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass

        # Return as-is with wrapper
        return {
            "raw_response": response,
            "project_overview": {
                "name": "Unnamed Project",
                "description": str(response),
            },
            "requirements": [],
            "architecture": {},
            "technology_stack": {},
            "deliverables": [],
        }

    async def validate_input(self, context: AgentContext) -> tuple[bool, List[str]]:
        """Validate concept designer input."""
        is_valid, errors = await super().validate_input(context)

        # Concept designer needs a task description at minimum
        if not context.task_description or len(context.task_description) < 10:
            errors.append("task_description must be at least 10 characters")
            is_valid = False

        return is_valid, errors
