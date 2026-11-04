"""Session persistence — save, load, and resume conversations."""

import os
import json
import uuid
from datetime import datetime, timezone


SESSIONS_DIR = ".lantern_sessions"


class Session:
    def __init__(self, desk_path: str, policies: list[dict], session_id: str = None):
        self.id = session_id or str(uuid.uuid4())[:8]
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.created_at
        self.desk_path = desk_path
        self.messages: list[dict] = []
        self.pending_action: dict | None = None
        self.policies = policies

    def add_message(self, role: str, content: str) -> None:
        """Add a text message to the conversation."""
        self.messages.append({"role": role, "content": content})

    def add_raw_assistant_message(self, content_blocks: list[dict]) -> None:
        """Add a raw assistant message with content blocks (text + tool_use)."""
        self.messages.append({"role": "assistant", "content": content_blocks})

    def add_tool_results(self, tool_results: list[dict]) -> None:
        """Add tool results as a user message (Anthropic API format)."""
        self.messages.append({"role": "user", "content": tool_results})

    def save(self) -> None:
        """Save session to disk."""
        self.updated_at = datetime.now(timezone.utc).isoformat()
        sessions_dir = os.path.join(self.desk_path, SESSIONS_DIR)
        os.makedirs(sessions_dir, exist_ok=True)

        filepath = os.path.join(sessions_dir, f"{self.id}.json")
        data = {
            "id": self.id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "desk_path": self.desk_path,
            "messages": self.messages,
            "pending_action": self.pending_action,
            "policies": self.policies,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def to_dict(self) -> dict:
        """Serialize session to dict."""
        return {
            "id": self.id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "desk_path": self.desk_path,
            "messages": self.messages,
            "pending_action": self.pending_action,
            "policies": self.policies,
        }


def load_session(filepath: str) -> Session:
    """Load a session from a JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    session = Session(
        desk_path=data["desk_path"],
        policies=data.get("policies", []),
        session_id=data["id"],
    )
    session.created_at = data["created_at"]
    session.updated_at = data["updated_at"]
    session.messages = data.get("messages", [])
    session.pending_action = data.get("pending_action")
    return session


def load_latest_session(desk_path: str) -> Session | None:
    """Find and load the most recent session for this desk."""
    sessions_dir = os.path.join(desk_path, SESSIONS_DIR)
    if not os.path.isdir(sessions_dir):
        return None

    session_files = [
        f for f in os.listdir(sessions_dir) if f.endswith(".json")
    ]
    if not session_files:
        return None

    # Find most recently updated
    latest = None
    latest_time = ""
    for filename in session_files:
        filepath = os.path.join(sessions_dir, filename)
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            if data.get("updated_at", "") > latest_time:
                latest_time = data["updated_at"]
                latest = filepath
        except (json.JSONDecodeError, KeyError):
            continue

    if latest:
        return load_session(latest)
    return None


def load_session_by_id(session_id: str, desk_path: str) -> Session | None:
    """Load a specific session by ID."""
    sessions_dir = os.path.join(desk_path, SESSIONS_DIR)
    filepath = os.path.join(sessions_dir, f"{session_id}.json")
    if os.path.isfile(filepath):
        return load_session(filepath)
    return None


def list_sessions(desk_path: str) -> list[dict]:
    """List all available sessions with basic info."""
    sessions_dir = os.path.join(desk_path, SESSIONS_DIR)
    if not os.path.isdir(sessions_dir):
        return []

    sessions = []
    for filename in sorted(os.listdir(sessions_dir)):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(sessions_dir, filename)
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            sessions.append({
                "id": data["id"],
                "created_at": data["created_at"],
                "updated_at": data["updated_at"],
                "message_count": len(data.get("messages", [])),
                "has_pending": data.get("pending_action") is not None,
            })
        except (json.JSONDecodeError, KeyError):
            continue

    return sorted(sessions, key=lambda s: s["updated_at"], reverse=True)
