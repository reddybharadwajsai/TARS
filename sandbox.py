"""Sandbox enforcement — validates all file paths stay within the desk boundary."""

import os


class SandboxViolation(Exception):
    """Raised when a path resolves outside the desk boundary."""
    pass


def validate_path(requested_path: str, desk_root: str) -> str:
    """
    Resolve the requested path and verify it's within desk_root.
    Returns the absolute resolved path or raises SandboxViolation.
    """
    desk_root = os.path.realpath(desk_root)

    if os.path.isabs(requested_path):
        resolved = os.path.realpath(requested_path)
    else:
        resolved = os.path.realpath(os.path.join(desk_root, requested_path))

    if resolved == desk_root:
        return resolved

    if not resolved.startswith(desk_root + os.sep):
        raise SandboxViolation(
            f"Access denied: '{requested_path}' resolves outside the working desk."
        )

    return resolved
