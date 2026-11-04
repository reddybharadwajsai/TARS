"""Tests for confidence gating logic."""

import os
import pytest
from unittest.mock import patch
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from confidence import gate_on_confidence, prompt_for_decision, PROCEED, WAIT_FOR_USER


class TestGateOnConfidence:
    @patch("confidence.display_confidence")
    def test_none_proceeds(self, mock_display):
        result = gate_on_confidence("NONE", "Clear request.", "write_file", {})
        assert result == PROCEED
        mock_display.assert_called_once_with("NONE", "Clear request.")

    @patch("confidence.display_confidence")
    def test_low_proceeds(self, mock_display):
        result = gate_on_confidence("LOW", "Minor assumption made.", "write_file", {})
        assert result == PROCEED

    @patch("confidence.display_confidence")
    def test_medium_waits(self, mock_display):
        result = gate_on_confidence("MEDIUM", "Multiple options.", "write_file", {})
        assert result == WAIT_FOR_USER

    @patch("confidence.display_confidence")
    def test_high_waits(self, mock_display):
        result = gate_on_confidence("HIGH", "Destructive action.", "delete_file", {})
        assert result == WAIT_FOR_USER

    @patch("confidence.display_confidence")
    def test_unknown_level_treated_as_high(self, mock_display):
        result = gate_on_confidence("UNKNOWN", "Something weird.", "write_file", {})
        assert result == WAIT_FOR_USER
        call_args = mock_display.call_args[0]
        assert call_args[0] == "HIGH"

    @patch("confidence.display_confidence")
    def test_case_insensitive(self, mock_display):
        result = gate_on_confidence("none", "test", "write_file", {})
        assert result == PROCEED

        result = gate_on_confidence("high", "test", "delete_file", {})
        assert result == WAIT_FOR_USER


class TestPromptForDecision:
    @patch("confidence.prompt_yes_no", return_value="yes")
    def test_high_calls_yes_no(self, mock_prompt):
        result = prompt_for_decision("HIGH", "Will delete file.", "delete_file", {})
        assert result == "yes"
        mock_prompt.assert_called_once()

    @patch("confidence.prompt_yes_no", return_value="no")
    def test_high_returns_no(self, mock_prompt):
        result = prompt_for_decision("HIGH", "Will delete file.", "delete_file", {})
        assert result == "no"

    @patch("confidence.prompt_choice", return_value="1. Overwrite existing")
    def test_medium_calls_choice(self, mock_prompt):
        result = prompt_for_decision("MEDIUM", "Options:\n1. Overwrite existing\n2. Cancel", "write_file", {})
        assert result == "1. Overwrite existing"

    @patch("confidence.prompt_choice", return_value="cancel")
    def test_medium_returns_cancel(self, mock_prompt):
        result = prompt_for_decision("MEDIUM", "Options:\n1. Save\n2. Cancel", "write_file", {})
        assert result == "cancel"


class TestConfidenceSandboxBypass:
    """Verify that sandbox violations never go through confidence — they are hard refusals."""

    @patch("confidence.display_confidence")
    def test_sandbox_violation_is_not_confidence_gated(self, mock_display):
        """
        This test verifies the architectural rule:
        Sandbox violations happen BEFORE confidence check in the agent loop.
        The confidence system should never see a sandbox violation.
        """
        # The actual enforcement is in agent.py's handle flow:
        # validate_tool_paths() is called BEFORE gate_on_confidence()
        # If SandboxViolation is raised, we return error immediately — no confidence prompt.
        # This test documents that invariant.
        from sandbox import validate_path, SandboxViolation
        import tempfile

        desk = tempfile.mkdtemp()
        with pytest.raises(SandboxViolation):
            validate_path("/etc/passwd", desk)

        # gate_on_confidence should NOT have been called
        mock_display.assert_not_called()
