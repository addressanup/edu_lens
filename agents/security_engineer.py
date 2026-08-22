"""
Security Engineer Agent for Claude Agents Orchestration System.

This agent handles Phase 5 security validation:
- SAST scanning integration
- Dependency vulnerability checks
- OWASP Top 10 validation
- Secret detection
- Compliance checking
"""

from typing import Any, Dict, List, Optional

from agents.base_agent import (
    AgentCapability,
    AgentContext,
    AgentResult,
    BaseAgent,
)


class SecurityEngineerAgent(BaseAgent):
    """
    Security Engineer Agent for Phase 5.

    Responsible for:
    - Static Application Security Testing (SAST)
    - Dependency vulnerability scanning
    - OWASP Top 10 compliance
    - Secret detection in code
    - Security configuration review
    - Compliance framework validation
    """

    agent_name = "security_engineer"
    agent_description = "Security specialist for vulnerability assessment and compliance validation"
    capabilities = [
        AgentCapability.SECURITY_SCANNING,
        AgentCapability.CODE_REVIEW,
    ]
    skills_file = "skills/security_engineer.skills.md"
    phase = 5

    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute security validation phase.

        Args:
            context: Execution context with code to analyze

        Returns:
            AgentResult with security findings
        """
        try:
            prompt = self.build_prompt(context)
            system_prompt = self.get_system_prompt()

            response = await self.invoke_with_retry(prompt, system_prompt)

            # Extract security findings
            security_report = self._extract_security_report(response)

            # Determine overall pass/fail
            critical_count = len(
                [f for f in security_report.get("findings", []) if f.get("severity") == "critical"]
            )

            return AgentResult(
                success=critical_count == 0,
                output=security_report,
                metadata={
                    "phase": self.phase,
                    "agent": self.agent_name,
                    "critical_findings": critical_count,
                    "total_findings": len(security_report.get("findings", [])),
                },
            )

        except Exception as e:
            return AgentResult(
                success=False,
                output={},
                error_message=str(e),
            )

    def build_prompt(self, context: AgentContext) -> str:
        """Build the security analysis prompt."""
        prompt_parts = [
            "# Security Analysis Request",
            "",
            f"## Task Description",
            context.task_description,
            "",
        ]

        # Add code to analyze
        code_files = context.input_data.get("code_files", {})
        if code_files:
            prompt_parts.extend(
                [
                    "## Code to Analyze",
                    "",
                ]
            )
            for filepath, content in list(code_files.items())[:10]:  # Limit files
                prompt_parts.extend(
                    [
                        f"### {filepath}",
                        "```",
                        content[:2000] if isinstance(content, str) else str(content)[:2000],
                        "```",
                        "",
                    ]
                )

        # Add dependency files
        dependencies = context.input_data.get("dependencies", {})
        if dependencies:
            prompt_parts.extend(
                [
                    "## Dependencies",
                ]
            )
            for dep_file, content in dependencies.items():
                prompt_parts.extend(
                    [
                        f"### {dep_file}",
                        "```",
                        str(content)[:1000],
                        "```",
                        "",
                    ]
                )

        # Add configuration files
        configs = context.input_data.get("configuration", {})
        if configs:
            prompt_parts.extend(
                [
                    "## Configuration Files",
                ]
            )
            for config_file, content in configs.items():
                prompt_parts.extend(
                    [
                        f"### {config_file}",
                        "```",
                        str(content)[:1000],
                        "```",
                        "",
                    ]
                )

        prompt_parts.extend(
            [
                "## Security Checks Required",
                "",
                "1. **OWASP Top 10** - Check for common vulnerabilities",
                "2. **Secret Detection** - Find hardcoded secrets, API keys, passwords",
                "3. **Dependency Vulnerabilities** - Check for known CVEs",
                "4. **Input Validation** - Verify proper sanitization",
                "5. **Authentication/Authorization** - Check security implementations",
                "6. **Cryptography** - Verify secure algorithms and key management",
                "7. **Error Handling** - Check for information leakage",
                "",
                "## Required Output",
                "",
                "```json",
                "{",
                '  "summary": {',
                '    "overall_risk": "low|medium|high|critical",',
                '    "critical_count": 0,',
                '    "high_count": 0,',
                '    "medium_count": 0,',
                '    "low_count": 0',
                "  },",
                '  "findings": [',
                "    {",
                '      "id": "SEC-001",',
                '      "severity": "critical|high|medium|low",',
                '      "category": "OWASP category or other",',
                '      "title": "Finding title",',
                '      "description": "Detailed description",',
                '      "location": "file:line",',
                '      "recommendation": "How to fix",',
                '      "cwe_id": "CWE-XXX",',
                '      "owasp_category": "A01:2021"',
                "    }",
                "  ],",
                '  "secrets_detected": [',
                "    {",
                '      "type": "api_key|password|token",',
                '      "location": "file:line",',
                '      "masked_value": "***"',
                "    }",
                "  ],",
                '  "vulnerable_dependencies": [',
                "    {",
                '      "package": "package-name",',
                '      "version": "1.0.0",',
                '      "vulnerability": "CVE-XXXX-XXXXX",',
                '      "severity": "critical",',
                '      "fixed_version": "1.0.1"',
                "    }",
                "  ],",
                '  "compliance": {',
                '    "owasp_top_10": {',
                '      "A01_broken_access_control": "pass|fail",',
                '      "A02_cryptographic_failures": "pass|fail",',
                '      "A03_injection": "pass|fail"',
                "    }",
                "  },",
                '  "recommendations": [',
                '    "Priority recommendation 1",',
                '    "Priority recommendation 2"',
                "  ]",
                "}",
                "```",
            ]
        )

        return "\n".join(prompt_parts)

    def _extract_security_report(
        self,
        response: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract security report from response."""
        if isinstance(response, dict):
            if "findings" in response or "summary" in response:
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
            "summary": {
                "overall_risk": "unknown",
                "critical_count": 0,
                "high_count": 0,
                "medium_count": 0,
                "low_count": 0,
            },
            "findings": [],
            "secrets_detected": [],
            "vulnerable_dependencies": [],
            "compliance": {},
            "recommendations": [],
            "raw_response": response,
        }
