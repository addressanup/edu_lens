"""
QA Engineer Agent for Claude Agents Orchestration System.

This agent handles Phase 5 quality assurance:
- Test generation
- Integration testing
- Performance validation
- Error scenario testing
- Coverage analysis
"""

from typing import Any, Dict, List, Optional

from agents.base_agent import (
    BaseAgent,
    AgentCapability,
    AgentContext,
    AgentResult,
)


class QAEngineerAgent(BaseAgent):
    """
    QA Engineer Agent for Phase 5.

    Responsible for:
    - Test case generation (unit, integration, e2e)
    - Test execution and validation
    - Performance testing
    - Error handling validation
    - Code coverage analysis
    """

    agent_name = "qa_engineer"
    agent_description = "Quality assurance specialist for testing, validation, and coverage analysis"
    capabilities = [
        AgentCapability.TEST_GENERATION,
        AgentCapability.CODE_REVIEW,
    ]
    skills_file = "skills/qa_engineer.skills.md"
    phase = 5

    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute QA validation phase.

        Args:
            context: Execution context with code to test

        Returns:
            AgentResult with test results
        """
        try:
            prompt = self.build_prompt(context)
            system_prompt = self.get_system_prompt()

            response = await self.invoke_with_retry(prompt, system_prompt)

            # Extract test results
            qa_report = self._extract_qa_report(response)

            # Calculate pass rate
            test_results = qa_report.get("test_results", {})
            total = test_results.get("total", 0)
            passed = test_results.get("passed", 0)
            pass_rate = passed / total if total > 0 else 0

            return AgentResult(
                success=pass_rate >= 0.8,  # 80% pass rate required
                output=qa_report,
                artifacts=self._get_test_artifacts(qa_report),
                metadata={
                    "phase": self.phase,
                    "agent": self.agent_name,
                    "pass_rate": pass_rate,
                    "coverage": qa_report.get("coverage", {}).get("overall", 0),
                },
            )

        except Exception as e:
            return AgentResult(
                success=False,
                output={},
                error_message=str(e),
            )

    def build_prompt(self, context: AgentContext) -> str:
        """Build the QA testing prompt."""
        prompt_parts = [
            "# Quality Assurance Request",
            "",
            f"## Task Description",
            context.task_description,
            "",
        ]

        # Add code to test
        code_files = context.input_data.get("code_files", {})
        if code_files:
            prompt_parts.extend([
                "## Code to Test",
                "",
            ])
            for filepath, content in list(code_files.items())[:10]:
                prompt_parts.extend([
                    f"### {filepath}",
                    "```",
                    content[:2000] if isinstance(content, str) else str(content)[:2000],
                    "```",
                    "",
                ])

        # Add API specification
        api_spec = context.input_data.get("api_specification", {})
        if api_spec:
            prompt_parts.extend([
                "## API Specification",
                str(api_spec),
                "",
            ])

        # Add existing tests
        existing_tests = context.input_data.get("existing_tests", {})
        if existing_tests:
            prompt_parts.extend([
                "## Existing Tests",
            ])
            for test_file, content in existing_tests.items():
                prompt_parts.extend([
                    f"### {test_file}",
                    "```",
                    str(content)[:1000],
                    "```",
                    "",
                ])

        prompt_parts.extend([
            "## Testing Requirements",
            "",
            "1. **Unit Tests** - Test individual functions and methods",
            "2. **Integration Tests** - Test component interactions",
            "3. **API Tests** - Test endpoint behavior",
            "4. **Error Handling** - Test error scenarios",
            "5. **Edge Cases** - Test boundary conditions",
            "6. **Performance** - Basic performance validation",
            "",
            "## Required Output",
            "",
            "```json",
            "{",
            '  "test_results": {',
            '    "total": 0,',
            '    "passed": 0,',
            '    "failed": 0,',
            '    "skipped": 0',
            "  },",
            '  "generated_tests": {',
            '    "tests/test_api.py": "import pytest\\n...",',
            '    "tests/test_models.py": "import pytest\\n...",',
            '    "tests/test_services.py": "import pytest\\n..."',
            "  },",
            '  "test_cases": [',
            "    {",
            '      "id": "TC-001",',
            '      "name": "Test case name",',
            '      "type": "unit|integration|e2e",',
            '      "description": "What is being tested",',
            '      "status": "passed|failed|skipped",',
            '      "duration_ms": 100,',
            '      "error": null',
            "    }",
            "  ],",
            '  "coverage": {',
            '    "overall": 0.85,',
            '    "by_file": {',
            '      "src/main.py": 0.90,',
            '      "src/routes/api.py": 0.80',
            "    }",
            "  },",
            '  "performance": {',
            '    "avg_response_time_ms": 50,',
            '    "p95_response_time_ms": 100,',
            '    "passed": true',
            "  },",
            '  "error_handling": {',
            '    "scenarios_tested": 10,',
            '    "scenarios_passed": 10',
            "  },",
            '  "recommendations": [',
            '    "Add more edge case tests",',
            '    "Improve coverage for module X"',
            "  ]",
            "}",
            "```",
        ])

        return "\n".join(prompt_parts)

    def _extract_qa_report(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract QA report from response."""
        if isinstance(response, dict):
            if "test_results" in response or "generated_tests" in response:
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
            "test_results": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
            },
            "generated_tests": {},
            "test_cases": [],
            "coverage": {"overall": 0},
            "performance": {"passed": False},
            "error_handling": {},
            "recommendations": [],
            "raw_response": response,
        }

    def _get_test_artifacts(self, report: Dict[str, Any]) -> List[str]:
        """Get list of generated test file paths."""
        return list(report.get("generated_tests", {}).keys())
