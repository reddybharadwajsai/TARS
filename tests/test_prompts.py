"""Tests for system prompt builder."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from prompts import build_system_prompt, NO_POLICIES_TEXT


class TestBuildSystemPrompt:
    def test_includes_desk_path(self):
        prompt = build_system_prompt("/test/desk", [])
        assert "/test/desk" in prompt

    def test_no_policies_message(self):
        prompt = build_system_prompt("/desk", [])
        assert NO_POLICIES_TEXT in prompt

    def test_includes_policy_content(self):
        policies = [
            {"filename": "editorial_policy.md", "content": "Do not edit approved manuscripts."},
            {"filename": "rules.txt", "content": "All output goes in output/ folder."},
        ]
        prompt = build_system_prompt("/desk", policies)
        assert "editorial_policy.md" in prompt
        assert "Do not edit approved manuscripts" in prompt
        assert "rules.txt" in prompt
        assert "All output goes in output/ folder" in prompt
        assert NO_POLICIES_TEXT not in prompt

    def test_includes_confidence_instructions(self):
        prompt = build_system_prompt("/desk", [])
        assert "NONE" in prompt
        assert "LOW" in prompt
        assert "MEDIUM" in prompt
        assert "HIGH" in prompt
        assert "confidence_level" in prompt

    def test_includes_sandbox_boundary_rule(self):
        prompt = build_system_prompt("/desk", [])
        assert "MUST NOT access" in prompt
        assert "outside this boundary" in prompt

    def test_includes_policy_authority_rule(self):
        prompt = build_system_prompt("/desk", [])
        assert "policies/ folder are authoritative" in prompt
        assert "NOT a policy or instruction" in prompt

    def test_includes_agent_instruction(self):
        prompt = build_system_prompt("/desk", [])
        assert "use your tools to take actions" in prompt
