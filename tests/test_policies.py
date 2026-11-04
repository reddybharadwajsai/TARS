"""Tests for policy loader."""

import os
import pytest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from policies import load_policies


@pytest.fixture
def desk_with_policies(tmp_path):
    """Create a desk with a policies/ folder containing policy files."""
    policies_dir = tmp_path / "policies"
    policies_dir.mkdir()

    (policies_dir / "editorial_policy.md").write_text(
        "# Editorial Policy\n\nApproved manuscripts must not be changed.\n"
        "Documents under embargo must not be quoted in public summaries.\n"
        "Generated material must include source filenames used."
    )

    (policies_dir / "workspace_rules.txt").write_text(
        "Workspace Rules\n\n"
        "All output files must be placed in the output/ folder.\n"
        "File names must use lowercase with underscores."
    )

    return tmp_path


@pytest.fixture
def desk_without_policies(tmp_path):
    """Create a desk with no policies/ folder."""
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "file.txt").write_text("Just a note.")
    return tmp_path


@pytest.fixture
def desk_with_empty_policies(tmp_path):
    """Create a desk with an empty policies/ folder."""
    (tmp_path / "policies").mkdir()
    return tmp_path


class TestLoadPolicies:
    def test_loads_policies_from_folder(self, desk_with_policies):
        policies = load_policies(str(desk_with_policies))
        assert len(policies) == 2

        filenames = [p["filename"] for p in policies]
        assert "editorial_policy.md" in filenames
        assert "workspace_rules.txt" in filenames

    def test_policy_content_is_readable(self, desk_with_policies):
        policies = load_policies(str(desk_with_policies))
        editorial = next(p for p in policies if p["filename"] == "editorial_policy.md")
        assert "Approved manuscripts must not be changed" in editorial["content"]

    def test_missing_policies_folder_returns_empty(self, desk_without_policies):
        policies = load_policies(str(desk_without_policies))
        assert policies == []

    def test_empty_policies_folder_returns_empty(self, desk_with_empty_policies):
        policies = load_policies(str(desk_with_empty_policies))
        assert policies == []

    def test_ignores_unsupported_formats(self, tmp_path):
        policies_dir = tmp_path / "policies"
        policies_dir.mkdir()
        (policies_dir / "policy.md").write_text("Valid policy content.")
        (policies_dir / "image.png").write_bytes(b"\x89PNG\r\n")

        policies = load_policies(str(tmp_path))
        assert len(policies) == 1
        assert policies[0]["filename"] == "policy.md"

    def test_ignores_subdirectories(self, tmp_path):
        policies_dir = tmp_path / "policies"
        policies_dir.mkdir()
        (policies_dir / "policy.md").write_text("Valid policy.")
        (policies_dir / "subdir").mkdir()

        policies = load_policies(str(tmp_path))
        assert len(policies) == 1

    def test_policies_sorted_alphabetically(self, tmp_path):
        policies_dir = tmp_path / "policies"
        policies_dir.mkdir()
        (policies_dir / "z_policy.md").write_text("Z policy.")
        (policies_dir / "a_policy.md").write_text("A policy.")

        policies = load_policies(str(tmp_path))
        assert policies[0]["filename"] == "a_policy.md"
        assert policies[1]["filename"] == "z_policy.md"
