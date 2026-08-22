"""
Frontend Engineer Agent for Claude Agents Orchestration System.

This agent handles Phase 4 code generation for:
- UI component design and implementation
- State management
- Responsive design
- Accessibility compliance
"""

from typing import Any, Dict, List, Optional

from agents.base_agent import (
    AgentCapability,
    AgentContext,
    AgentResult,
    BaseAgent,
)


class FrontendEngineerAgent(BaseAgent):
    """
    Frontend Engineer Agent for Phase 4.

    Responsible for:
    - UI component generation (React, Vue, Svelte)
    - State management (Redux, Vuex, Svelte stores)
    - Responsive design implementation
    - Accessibility (WCAG 2.1) compliance
    - Performance optimization
    """

    agent_name = "frontend_engineer"
    agent_description = (
        "Frontend development specialist for UI components, state management, and user experience"
    )
    capabilities = [
        AgentCapability.FRONTEND_CODE,
        AgentCapability.UI_COMPONENTS,
    ]
    skills_file = "skills/frontend_engineer.skills.md"
    phase = 4

    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute frontend code generation phase.

        Args:
            context: Execution context with frontend requirements

        Returns:
            AgentResult with generated frontend code
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
                    "components_generated": len(code_output.get("components", {})),
                },
            )

        except Exception as e:
            return AgentResult(
                success=False,
                output={},
                error_message=str(e),
            )

    def build_prompt(self, context: AgentContext) -> str:
        """Build the frontend code generation prompt."""
        prompt_parts = [
            "# Frontend Code Generation Request",
            "",
            f"## Task Description",
            context.task_description,
            "",
        ]

        # Add UI requirements
        ui_spec = context.input_data.get("ui_specification", {})
        if ui_spec:
            prompt_parts.extend(
                [
                    "## UI Specification",
                    f"Design System: {ui_spec.get('design_system', 'Custom')}",
                    f"Theme: {ui_spec.get('theme', 'Light/Dark')}",
                    "",
                    "### Pages/Views",
                ]
            )
            for page in ui_spec.get("pages", []):
                prompt_parts.append(f"- {page.get('name', 'Page')}: {page.get('description', '')}")
            prompt_parts.append("")

        # Add technology stack
        tech_stack = context.input_data.get("technology_stack", {})
        if tech_stack.get("frontend"):
            prompt_parts.extend(
                [
                    "## Technology Stack",
                    f"Framework: {tech_stack['frontend'].get('framework', 'React')}",
                    f"State Management: {tech_stack['frontend'].get('state_management', 'Redux')}",
                    f"Styling: {tech_stack['frontend'].get('styling', 'Tailwind CSS')}",
                    "",
                ]
            )

        # Add API integration points
        api_endpoints = context.input_data.get("api_endpoints", [])
        if api_endpoints:
            prompt_parts.extend(
                [
                    "## API Integration",
                    "### Endpoints to Integrate",
                ]
            )
            for endpoint in api_endpoints:
                prompt_parts.append(f"- {endpoint}")
            prompt_parts.append("")

        # Add accessibility requirements
        prompt_parts.extend(
            [
                "## Accessibility Requirements",
                "- WCAG 2.1 Level AA compliance",
                "- Keyboard navigation support",
                "- Screen reader compatibility",
                "- Proper ARIA labels",
                "",
            ]
        )

        prompt_parts.extend(
            [
                "## Required Output",
                "",
                "Generate complete frontend code in JSON format:",
                "",
                "```json",
                "{",
                '  "components": {',
                '    "src/components/Header.tsx": "// Header component\\n...",',
                '    "src/components/Footer.tsx": "// Footer component\\n...",',
                '    "src/components/Button.tsx": "// Button component\\n..."',
                "  },",
                '  "pages": {',
                '    "src/pages/Home.tsx": "// Home page\\n...",',
                '    "src/pages/Dashboard.tsx": "// Dashboard page\\n..."',
                "  },",
                '  "state": {',
                '    "src/store/index.ts": "// Redux store setup\\n...",',
                '    "src/store/slices/userSlice.ts": "// User slice\\n..."',
                "  },",
                '  "hooks": {',
                '    "src/hooks/useApi.ts": "// API hook\\n...",',
                '    "src/hooks/useAuth.ts": "// Auth hook\\n..."',
                "  },",
                '  "styles": {',
                '    "src/styles/globals.css": "/* Global styles */\\n...",',
                '    "tailwind.config.js": "module.exports = {...}"',
                "  },",
                '  "configuration": {',
                '    "package.json": "{...}",',
                '    "tsconfig.json": "{...}",',
                '    "next.config.js": "// Next.js config\\n..."',
                "  },",
                '  "tests": {',
                '    "src/__tests__/components/Button.test.tsx": "// Button tests\\n..."',
                "  }",
                "}",
                "```",
                "",
                "Ensure all code is:",
                "- Fully typed with TypeScript",
                "- Accessible (ARIA labels, semantic HTML)",
                "- Responsive (mobile-first)",
                "- Following React/Vue/Svelte best practices",
                "- Properly styled with consistent design",
            ]
        )

        return "\n".join(prompt_parts)

    def _extract_code_output(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract code files from response."""
        if isinstance(response, dict):
            if "components" in response or "pages" in response:
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
            "components": {},
            "pages": {},
            "state": {},
            "hooks": {},
            "styles": {},
            "raw_response": response,
        }

    def _get_artifacts(self, output: Dict[str, Any]) -> List[str]:
        """Get list of generated artifact paths."""
        artifacts = []

        for category in [
            "components",
            "pages",
            "state",
            "hooks",
            "styles",
            "configuration",
            "tests",
        ]:
            if category in output:
                artifacts.extend(output[category].keys())

        return artifacts
