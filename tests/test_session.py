"""Tests for session persistence."""

import os
import json
import pytest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from session import Session, load_session, load_latest_session, load_session_by_id, list_sessions


@pytest.fixture
def desk(tmp_path):
    return str(tmp_path)


class TestSessionCreation:
    def test_creates_with_defaults(self, desk):
        session = Session(desk_path=desk, policies=[])
        assert session.id is not None
        assert len(session.id) == 8
        assert session.desk_path == desk
        assert session.messages == []
        assert session.pending_action is None
        assert session.policies == []

    def test_creates_with_policies(self, desk):
        policies = [{"filename": "policy.md", "content": "No editing."}]
        session = Session(desk_path=desk, policies=policies)
        assert session.policies == policies

    def test_creates_with_custom_id(self, desk):
        session = Session(desk_path=desk, policies=[], session_id="test-id")
        assert session.id == "test-id"


class TestMessageManagement:
    def test_add_message(self, desk):
        session = Session(desk_path=desk, policies=[])
        session.add_message("user", "Hello")
        assert len(session.messages) == 1
        assert session.messages[0] == {"role": "user", "content": "Hello"}

    def test_add_raw_assistant_message(self, desk):
        session = Session(desk_path=desk, policies=[])
        blocks = [{"type": "text", "text": "Hi there"}]
        session.add_raw_assistant_message(blocks)
        assert session.messages[0] == {"role": "assistant", "content": blocks}

    def test_add_tool_results(self, desk):
        session = Session(desk_path=desk, policies=[])
        results = [{"type": "tool_result", "tool_use_id": "123", "content": "done"}]
        session.add_tool_results(results)
        assert session.messages[0] == {"role": "user", "content": results}


class TestSaveAndLoad:
    def test_save_creates_file(self, desk):
        session = Session(desk_path=desk, policies=[])
        session.save()
        filepath = os.path.join(desk, ".lantern_sessions", f"{session.id}.json")
        assert os.path.isfile(filepath)

    def test_save_load_roundtrip(self, desk):
        session = Session(desk_path=desk, policies=[{"filename": "p.md", "content": "rule"}])
        session.add_message("user", "Hello")
        session.add_message("user", "World")
        session.pending_action = {"tool_id": "t1", "tool_name": "write_file", "level": "HIGH"}
        session.save()

        filepath = os.path.join(desk, ".lantern_sessions", f"{session.id}.json")
        loaded = load_session(filepath)

        assert loaded.id == session.id
        assert loaded.desk_path == session.desk_path
        assert loaded.messages == session.messages
        assert loaded.pending_action == session.pending_action
        assert loaded.policies == session.policies

    def test_updated_at_changes_on_save(self, desk):
        session = Session(desk_path=desk, policies=[])
        first_save_time = session.updated_at
        session.add_message("user", "test")
        session.save()
        assert session.updated_at >= first_save_time


class TestLoadLatest:
    def test_finds_latest(self, desk):
        s1 = Session(desk_path=desk, policies=[], session_id="old")
        s1.add_message("user", "first")
        s1.save()

        s2 = Session(desk_path=desk, policies=[], session_id="new")
        s2.add_message("user", "second")
        s2.save()

        latest = load_latest_session(desk)
        assert latest is not None
        assert latest.id == "new"

    def test_returns_none_when_no_sessions(self, desk):
        result = load_latest_session(desk)
        assert result is None

    def test_returns_none_when_no_dir(self, tmp_path):
        result = load_latest_session(str(tmp_path / "nonexistent"))
        assert result is None


class TestLoadById:
    def test_loads_by_id(self, desk):
        session = Session(desk_path=desk, policies=[], session_id="myid")
        session.add_message("user", "hello")
        session.save()

        loaded = load_session_by_id("myid", desk)
        assert loaded is not None
        assert loaded.id == "myid"
        assert loaded.messages[0]["content"] == "hello"

    def test_returns_none_for_missing_id(self, desk):
        result = load_session_by_id("nonexistent", desk)
        assert result is None


class TestListSessions:
    def test_lists_sessions(self, desk):
        s1 = Session(desk_path=desk, policies=[], session_id="aaa")
        s1.save()
        s2 = Session(desk_path=desk, policies=[], session_id="bbb")
        s2.pending_action = {"tool_id": "t1"}
        s2.save()

        sessions = list_sessions(desk)
        assert len(sessions) == 2
        ids = [s["id"] for s in sessions]
        assert "aaa" in ids
        assert "bbb" in ids

        bbb = next(s for s in sessions if s["id"] == "bbb")
        assert bbb["has_pending"] is True

    def test_empty_when_no_sessions(self, desk):
        assert list_sessions(desk) == []


class TestPendingAction:
    def test_pending_preserved_on_save(self, desk):
        session = Session(desk_path=desk, policies=[])
        session.pending_action = {
            "tool_id": "tool_123",
            "tool_name": "delete_file",
            "tool_args": {"path": "drafts/old.md"},
            "level": "HIGH",
            "reasoning": "This will permanently delete the file.",
        }
        session.save()

        loaded = load_latest_session(desk)
        assert loaded.pending_action is not None
        assert loaded.pending_action["tool_name"] == "delete_file"
        assert loaded.pending_action["level"] == "HIGH"

    def test_pending_cleared_after_decision(self, desk):
        session = Session(desk_path=desk, policies=[])
        session.pending_action = {"tool_id": "t1", "level": "HIGH"}
        session.save()

        # Simulate clearing after user decision
        session.pending_action = None
        session.save()

        loaded = load_latest_session(desk)
        assert loaded.pending_action is None
