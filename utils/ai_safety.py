# Flick Forge - Flick Store Backend
# Copyright (C) 2025 Flick Project
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
AI Safety Checker for Flick Forge.

This module provides multi-level AI safety checking for app requests.
Currently implemented as stubs that can be integrated with Claude Code
or other AI safety systems.

The safety check process:
1. Basic keyword filtering (local, fast)
2. Pattern matching for known dangerous prompts (local)
3. AI-based semantic analysis (external API, when configured)
4. Human review flagging for edge cases
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SafetyLevel(Enum):
    """Safety check result levels."""

    SAFE = "safe"
    NEEDS_REVIEW = "needs_review"
    UNSAFE = "unsafe"


@dataclass
class SafetyResult:
    """Result of a safety check."""

    level: SafetyLevel
    score: float  # 0.0 = unsafe, 1.0 = safe
    reasons: list[str]
    needs_human_review: bool = False

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "level": self.level.value,
            "score": self.score,
            "reasons": self.reasons,
            "needs_human_review": self.needs_human_review,
        }


class SafetyChecker:
    """
    Multi-level AI safety checker for app request prompts.

    Levels:
    1. Keyword filter - Fast local check for obviously dangerous content
    2. Pattern matching - Regex-based detection of known attack patterns
    3. AI analysis - External API call to Claude/GPT for semantic analysis
    4. Human review - Flag edge cases for manual review

    Usage:
        checker = SafetyChecker(config)
        result = checker.check_prompt(prompt_text)
        if result.level == SafetyLevel.SAFE:
            # Proceed with request
        elif result.needs_human_review:
            # Queue for manual review
        else:
            # Reject request
    """

    # Dangerous keywords that should trigger immediate rejection
    DANGEROUS_KEYWORDS = [
        "malware",
        "ransomware",
        "keylogger",
        "virus",
        "trojan",
        "rootkit",
        "botnet",
        "ddos",
        "denial of service",
        "exploit",
        "vulnerability scanner",
        "password cracker",
        "credential harvester",
        "phishing",
        "spyware",
        "backdoor",
        "remote access trojan",
        "rat",
        "cryptominer",
        "crypto miner",
    ]

    # Patterns that need human review (not necessarily bad, but suspicious)
    REVIEW_PATTERNS = [
        r"access.*system\s+files?",
        r"modify.*registry",
        r"delete.*files?",
        r"encrypt.*files?",
        r"send.*data.*server",
        r"record.*keystrokes?",
        r"capture.*screen",
        r"access.*camera",
        r"access.*microphone",
        r"hidden.*process",
        r"run.*background.*undetected",
        r"bypass.*security",
        r"disable.*antivirus",
        r"elevate.*privileges?",
        r"admin.*access",
        r"root.*access",
    ]

    def __init__(self, config=None):
        """
        Initialize the safety checker.

        Args:
            config: Optional configuration dictionary with:
                - ai_safety_endpoint: URL for external AI safety API
                - ai_safety_enabled: Whether to use external AI checking
                - ai_safety_api_key: API key for external service
        """
        self.config = config or {}
        self.ai_enabled = self.config.get("AI_SAFETY_ENABLED", False)
        self.ai_endpoint = self.config.get("AI_SAFETY_ENDPOINT")

    def check_prompt(self, prompt: str) -> SafetyResult:
        """
        Perform multi-level safety check on a prompt.

        Args:
            prompt: The app request prompt to check

        Returns:
            SafetyResult with level, score, and reasons
        """
        prompt_lower = prompt.lower()
        reasons = []

        # Level 1: Keyword filtering
        for keyword in self.DANGEROUS_KEYWORDS:
            if keyword in prompt_lower:
                return SafetyResult(
                    level=SafetyLevel.UNSAFE,
                    score=0.0,
                    reasons=[f"Contains dangerous keyword: {keyword}"],
                    needs_human_review=False,
                )

        # Level 2: Pattern matching
        for pattern in self.REVIEW_PATTERNS:
            if re.search(pattern, prompt_lower):
                reasons.append(f"Matches suspicious pattern: {pattern}")

        if reasons:
            # Some patterns matched - flag for review
            return SafetyResult(
                level=SafetyLevel.NEEDS_REVIEW,
                score=0.5,
                reasons=reasons,
                needs_human_review=True,
            )

        # Level 3: AI analysis (if enabled)
        if self.ai_enabled and self.ai_endpoint:
            ai_result = self._check_with_ai(prompt)
            if ai_result:
                return ai_result

        # Passed all checks
        return SafetyResult(
            level=SafetyLevel.SAFE,
            score=1.0,
            reasons=["Passed all safety checks"],
            needs_human_review=False,
        )

    def _check_with_ai(self, prompt: str) -> Optional[SafetyResult]:
        """
        Check prompt with external AI safety service.

        STUB: This method is a placeholder for integration with Claude Code
        or another AI safety service.

        Args:
            prompt: The prompt to check

        Returns:
            SafetyResult or None if AI check fails/unavailable
        """
        # STUB: In production, this would:
        # 1. Send the prompt to an AI safety endpoint
        # 2. The AI would analyze for:
        #    - Intent to create harmful software
        #    - Attempts to circumvent safety measures
        #    - Hidden malicious instructions
        #    - Social engineering attempts
        # 3. Return structured safety assessment

        # Example implementation (when Claude API is available):
        #
        # try:
        #     response = requests.post(
        #         self.ai_endpoint,
        #         headers={"Authorization": f"Bearer {self.config['ai_safety_api_key']}"},
        #         json={
        #             "prompt": prompt,
        #             "system": "Analyze this app request for safety concerns...",
        #         },
        #         timeout=30,
        #     )
        #     result = response.json()
        #     return SafetyResult(
        #         level=SafetyLevel(result["level"]),
        #         score=result["score"],
        #         reasons=result["reasons"],
        #         needs_human_review=result.get("needs_review", False),
        #     )
        # except Exception as e:
        #     # Log error, return None to skip AI check
        #     return None

        return None

    def check_app_code(self, code: str, language: str = "python") -> SafetyResult:
        """
        Check generated app code for safety issues.

        STUB: This method would analyze generated code for:
        - Dangerous system calls
        - Network activity
        - File system access patterns
        - Known vulnerability patterns

        Args:
            code: The generated code to check
            language: Programming language of the code

        Returns:
            SafetyResult
        """
        # STUB: In production, this would perform static analysis
        # on the generated code before packaging

        # Basic checks that can be done locally
        dangerous_imports = [
            "subprocess",
            "os.system",
            "eval",
            "exec",
            "__import__",
            "ctypes",
            "win32api",
        ]

        code_lower = code.lower()
        for imp in dangerous_imports:
            if imp in code_lower:
                return SafetyResult(
                    level=SafetyLevel.NEEDS_REVIEW,
                    score=0.5,
                    reasons=[f"Code uses potentially dangerous import: {imp}"],
                    needs_human_review=True,
                )

        return SafetyResult(
            level=SafetyLevel.SAFE,
            score=1.0,
            reasons=["Code passed basic safety checks"],
            needs_human_review=False,
        )


def check_prompt_safety(prompt: str, config: dict = None) -> dict:
    """
    Convenience function to check prompt safety.

    Args:
        prompt: The prompt to check
        config: Optional configuration

    Returns:
        Dictionary with safety check results
    """
    checker = SafetyChecker(config)
    result = checker.check_prompt(prompt)
    return result.to_dict()
