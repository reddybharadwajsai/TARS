"""Tests for sandbox boundary enforcement."""

import os
import tempfile
import pytest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sandbox import validate_path, SandboxViolation


@pytest.fixture
def desk(tmp_path):
    """Create a temporary desk directory with some structure."""
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "file.txt").write_text("hello")
    (tmp_path / "output").mkdir()
    return str(tmp_path)


class TestValidRelativePaths:
    def test_simple_relative(self, desk):
        result = validate_path("notes/file.txt", desk)
        assert result == os.path.join(desk, "notes", "file.txt")

    def test_relative_to_desk_root(self, desk):
        result = validate_path(".", desk)
        assert result == desk

    def test_subdirectory(self, desk):
        result = validate_path("notes", desk)
        assert result == os.path.join(desk, "notes")

    def test_new_file_in_output(self, desk):
        result = validate_path("output/new_file.md", desk)
        assert result == os.path.join(desk, "output", "new_file.md")


class TestBlockedTraversal:
    def test_parent_directory(self, desk):
        with pytest.raises(SandboxViolation):
            validate_path("..", desk)

    def test_parent_then_sibling(self, desk):
        with pytest.raises(SandboxViolation):
            validate_path("../other_folder", desk)

    def test_deep_traversal(self, desk):
        with pytest.raises(SandboxViolation):
            validate_path("notes/../../etc/passwd", desk)

    def test_double_parent(self, desk):
        with pytest.raises(SandboxViolation):
            validate_path("../../etc/passwd", desk)

    def test_traversal_with_trailing_content(self, desk):
        with pytest.raises(SandboxViolation):
            validate_path("../outside/secret.txt", desk)


class TestBlockedAbsolutePaths:
    def test_etc_passwd(self, desk):
        with pytest.raises(SandboxViolation):
            validate_path("/etc/passwd", desk)

    def test_tmp_directory(self, desk):
        with pytest.raises(SandboxViolation):
            validate_path("/tmp/temp_file.txt", desk)

    def test_home_directory(self, desk):
        with pytest.raises(SandboxViolation):
            validate_path(os.path.expanduser("~/secret.txt"), desk)

    def test_root(self, desk):
        with pytest.raises(SandboxViolation):
            validate_path("/", desk)


symlink_supported = pytest.mark.skipif(
    sys.platform == "win32" and not os.environ.get("CI"),
    reason="Symlinks require admin/Developer Mode on Windows"
)


@symlink_supported
class TestBlockedSymlinks:
    def test_symlink_pointing_outside(self, desk):
        link_path = os.path.join(desk, "sneaky_link")
        os.symlink("/etc", link_path)
        with pytest.raises(SandboxViolation):
            validate_path("sneaky_link/passwd", desk)

    def test_symlink_to_parent(self, desk):
        link_path = os.path.join(desk, "parent_link")
        os.symlink(os.path.dirname(desk), link_path)
        with pytest.raises(SandboxViolation):
            validate_path("parent_link/some_file.txt", desk)

    def test_symlink_within_desk_allowed(self, desk):
        target = os.path.join(desk, "notes", "file.txt")
        link_path = os.path.join(desk, "link_to_notes")
        os.symlink(target, link_path)
        result = validate_path("link_to_notes", desk)
        assert result == os.path.realpath(target)


class TestEdgeCases:
    def test_empty_path(self, desk):
        result = validate_path("", desk)
        assert result == desk

    def test_dot_path(self, desk):
        result = validate_path(".", desk)
        assert result == desk

    def test_absolute_path_inside_desk(self, desk):
        inside_path = os.path.join(desk, "notes", "file.txt")
        result = validate_path(inside_path, desk)
        assert result == inside_path

    def test_path_with_redundant_separators(self, desk):
        result = validate_path("notes//file.txt", desk)
        assert result == os.path.join(desk, "notes", "file.txt")

    def test_desk_root_prefix_but_different_dir(self, desk):
        """E.g., desk is /tmp/abc, path resolves to /tmp/abcdef — must be blocked."""
        fake_sibling = desk + "_sibling"
        os.makedirs(fake_sibling, exist_ok=True)
        try:
            with pytest.raises(SandboxViolation):
                validate_path(fake_sibling, desk)
        finally:
            os.rmdir(fake_sibling)
