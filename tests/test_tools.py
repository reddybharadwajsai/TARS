"""Tests for tool execution logic."""

import os
import pytest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools import (
    execute_tool,
    has_path_arg,
    validate_tool_paths,
    MUTATING_TOOLS,
    READ_ONLY_TOOLS,
)
from sandbox import SandboxViolation


@pytest.fixture
def desk(tmp_path):
    """Create a desk with sample files."""
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "coral.md").write_text("# Coral Reefs\n\nCoral reefs are diverse ecosystems.")
    (tmp_path / "notes" / "tides.txt").write_text("Tidal patterns affect coastal life significantly.")
    (tmp_path / "output").mkdir()
    (tmp_path / "drafts").mkdir()
    (tmp_path / "drafts" / "chapter1.md").write_text("# Chapter 1\n\nIntroduction to coastal ecology.")
    return str(tmp_path)


class TestHasPathArg:
    def test_list_files(self):
        assert has_path_arg("list_files", {"path": "notes"}) == ["path"]

    def test_move_file_both_paths(self):
        result = has_path_arg("move_file", {"source": "a.txt", "destination": "b.txt"})
        assert "source" in result
        assert "destination" in result

    def test_empty_path_excluded(self):
        assert has_path_arg("search_files", {"query": "coral", "path": ""}) == []

    def test_missing_path_field(self):
        assert has_path_arg("search_files", {"query": "coral"}) == []


class TestValidateToolPaths:
    def test_valid_path_passes(self, desk):
        validate_tool_paths("read_file", {"path": "notes/coral.md"}, desk)

    def test_traversal_raises(self, desk):
        with pytest.raises(SandboxViolation):
            validate_tool_paths("read_file", {"path": "../secret.txt"}, desk)

    def test_absolute_outside_raises(self, desk):
        with pytest.raises(SandboxViolation):
            validate_tool_paths("write_file", {
                "path": "/etc/passwd",
                "content": "hack",
                "confidence_level": "NONE",
                "confidence_reasoning": "test"
            }, desk)

    def test_move_validates_both_paths(self, desk):
        with pytest.raises(SandboxViolation):
            validate_tool_paths("move_file", {
                "source": "notes/coral.md",
                "destination": "/tmp/stolen.md",
                "confidence_level": "NONE",
                "confidence_reasoning": "test"
            }, desk)


class TestListFiles:
    def test_lists_root(self, desk):
        result = execute_tool("list_files", {"path": "."}, desk)
        assert "notes" in result
        assert "output" in result
        assert "drafts" in result

    def test_lists_subdirectory(self, desk):
        result = execute_tool("list_files", {"path": "notes"}, desk)
        assert "coral.md" in result
        assert "tides.txt" in result

    def test_nonexistent_directory(self, desk):
        result = execute_tool("list_files", {"path": "nonexistent"}, desk)
        assert "Error" in result

    def test_sandbox_violation(self, desk):
        result = execute_tool("list_files", {"path": "/etc"}, desk)
        assert "Error" in result


class TestReadFile:
    def test_reads_markdown(self, desk):
        result = execute_tool("read_file", {"path": "notes/coral.md"}, desk)
        assert "Coral Reefs" in result
        assert "diverse ecosystems" in result

    def test_reads_txt(self, desk):
        result = execute_tool("read_file", {"path": "notes/tides.txt"}, desk)
        assert "Tidal patterns" in result

    def test_file_not_found(self, desk):
        result = execute_tool("read_file", {"path": "nonexistent.txt"}, desk)
        assert "Error" in result
        assert "not found" in result

    def test_sandbox_violation(self, desk):
        result = execute_tool("read_file", {"path": "/etc/passwd"}, desk)
        assert "Error" in result


class TestSearchFiles:
    def test_finds_matching_files(self, desk):
        result = execute_tool("search_files", {"query": "coral"}, desk)
        assert "coral.md" in result

    def test_case_insensitive(self, desk):
        result = execute_tool("search_files", {"query": "CORAL"}, desk)
        assert "coral.md" in result

    def test_no_matches(self, desk):
        result = execute_tool("search_files", {"query": "xyznonexistent"}, desk)
        assert "No files found" in result

    def test_search_subdirectory(self, desk):
        result = execute_tool("search_files", {"query": "tidal", "path": "notes"}, desk)
        assert "tides.txt" in result

    def test_search_wrong_subdirectory(self, desk):
        result = execute_tool("search_files", {"query": "coral", "path": "drafts"}, desk)
        assert "No files found" in result or "coral" not in result.lower().split("found")[0]


class TestWriteFile:
    def test_creates_new_file(self, desk):
        result = execute_tool("write_file", {
            "path": "output/summary.md",
            "content": "# Summary\n\nThis is a test.",
            "confidence_level": "NONE",
            "confidence_reasoning": "New file, no conflict."
        }, desk)
        assert "Created" in result
        assert os.path.isfile(os.path.join(desk, "output", "summary.md"))

    def test_overwrites_existing(self, desk):
        result = execute_tool("write_file", {
            "path": "drafts/chapter1.md",
            "content": "New content.",
            "confidence_level": "NONE",
            "confidence_reasoning": "test"
        }, desk)
        assert "Overwrote" in result

    def test_unsupported_write_format(self, desk):
        result = execute_tool("write_file", {
            "path": "output/doc.docx",
            "content": "test",
            "confidence_level": "NONE",
            "confidence_reasoning": "test"
        }, desk)
        assert "Error" in result
        assert "Cannot write" in result

    def test_creates_parent_directories(self, desk):
        result = execute_tool("write_file", {
            "path": "output/sub/deep/file.md",
            "content": "deep file",
            "confidence_level": "NONE",
            "confidence_reasoning": "test"
        }, desk)
        assert "Created" in result
        assert os.path.isfile(os.path.join(desk, "output", "sub", "deep", "file.md"))

    def test_sandbox_violation(self, desk):
        result = execute_tool("write_file", {
            "path": "../outside.txt",
            "content": "escape attempt",
            "confidence_level": "NONE",
            "confidence_reasoning": "test"
        }, desk)
        assert "Error" in result


class TestMoveFile:
    def test_moves_file(self, desk):
        result = execute_tool("move_file", {
            "source": "notes/coral.md",
            "destination": "output/coral_moved.md",
            "confidence_level": "NONE",
            "confidence_reasoning": "test"
        }, desk)
        assert "Moved" in result
        assert not os.path.exists(os.path.join(desk, "notes", "coral.md"))
        assert os.path.exists(os.path.join(desk, "output", "coral_moved.md"))

    def test_source_not_found(self, desk):
        result = execute_tool("move_file", {
            "source": "nonexistent.txt",
            "destination": "output/x.txt",
            "confidence_level": "NONE",
            "confidence_reasoning": "test"
        }, desk)
        assert "Error" in result

    def test_sandbox_violation_destination(self, desk):
        result = execute_tool("move_file", {
            "source": "notes/tides.txt",
            "destination": "/tmp/stolen.txt",
            "confidence_level": "NONE",
            "confidence_reasoning": "test"
        }, desk)
        assert "Error" in result


class TestDeleteFile:
    def test_deletes_file(self, desk):
        result = execute_tool("delete_file", {
            "path": "notes/tides.txt",
            "confidence_level": "NONE",
            "confidence_reasoning": "test"
        }, desk)
        assert "Deleted" in result
        assert not os.path.exists(os.path.join(desk, "notes", "tides.txt"))

    def test_file_not_found(self, desk):
        result = execute_tool("delete_file", {
            "path": "nonexistent.txt",
            "confidence_level": "NONE",
            "confidence_reasoning": "test"
        }, desk)
        assert "Error" in result

    def test_cannot_delete_directory(self, desk):
        result = execute_tool("delete_file", {
            "path": "notes",
            "confidence_level": "NONE",
            "confidence_reasoning": "test"
        }, desk)
        assert "Error" in result
        assert "directory" in result.lower()


class TestCreateDirectory:
    def test_creates_directory(self, desk):
        result = execute_tool("create_directory", {
            "path": "new_folder",
            "confidence_level": "NONE",
            "confidence_reasoning": "test"
        }, desk)
        assert "Created" in result
        assert os.path.isdir(os.path.join(desk, "new_folder"))

    def test_already_exists(self, desk):
        result = execute_tool("create_directory", {
            "path": "notes",
            "confidence_level": "NONE",
            "confidence_reasoning": "test"
        }, desk)
        assert "already exists" in result


class TestAnnouncePlan:
    def test_returns_plan_text(self, desk):
        result = execute_tool("announce_plan", {
            "plan": "Search and summarize",
            "steps": ["Search for coral", "Read files", "Write summary"]
        }, desk)
        assert "Search and summarize" in result
        assert "Search for coral" in result


class TestUnknownTool:
    def test_unknown_tool(self, desk):
        result = execute_tool("nonexistent_tool", {}, desk)
        assert "Error" in result
        assert "Unknown tool" in result
