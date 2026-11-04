"""Transcript logger — writes structured markdown logs during a session."""

import os
from datetime import datetime, timezone


class TranscriptLogger:
    def __init__(self, filepath: str, desk_path: str):
        self.filepath = filepath
        self.desk_path = desk_path
        self._lines: list[str] = []
        self._start_time = datetime.now(timezone.utc).isoformat()
        self._write_header()

    def _write_header(self) -> None:
        self._lines.append(f"# Lantern Test Run Transcript")
        self._lines.append(f"")
        self._lines.append(f"**Date**: {self._start_time}")
        self._lines.append(f"**Workspace**: `{self.desk_path}`")
        self._lines.append(f"")
        self._lines.append(f"## Starting Workspace State")
        self._lines.append(f"")
        self._log_workspace_state()
        self._lines.append(f"")
        self._lines.append(f"---")
        self._lines.append(f"")
        self._lines.append(f"## Conversation")
        self._lines.append(f"")

    def _log_workspace_state(self) -> None:
        """Log the current file tree of the workspace."""
        self._lines.append("```")
        for root, dirs, files in os.walk(self.desk_path):
            dirs[:] = [d for d in sorted(dirs) if not d.startswith(".")]
            level = root.replace(self.desk_path, "").count(os.sep)
            indent = "  " * level
            folder_name = os.path.basename(root) or os.path.basename(self.desk_path)
            self._lines.append(f"{indent}{folder_name}/")
            for filename in sorted(files):
                if not filename.startswith("."):
                    self._lines.append(f"{indent}  {filename}")
        self._lines.append("```")

    def log_user_input(self, text: str) -> None:
        self._lines.append(f"### User")
        self._lines.append(f"")
        self._lines.append(f"> {text}")
        self._lines.append(f"")

    def log_assistant_text(self, text: str) -> None:
        self._lines.append(f"### Lantern")
        self._lines.append(f"")
        self._lines.append(text)
        self._lines.append(f"")

    def log_tool_call(self, tool_name: str, args: dict) -> None:
        confidence = args.get("confidence_level", "")
        display_args = {k: v for k, v in args.items()
                        if k not in ("confidence_level", "confidence_reasoning", "content")}
        if "content" in args:
            display_args["content"] = f"[{len(args['content'].split())} words]"

        confidence_str = f" `[CONFIDENCE: {confidence}]`" if confidence else ""
        self._lines.append(f"**Tool call**: `{tool_name}`{confidence_str}")
        self._lines.append(f"```json")
        import json
        self._lines.append(json.dumps(display_args, indent=2))
        self._lines.append(f"```")
        if args.get("confidence_reasoning"):
            self._lines.append(f"*Reasoning*: {args['confidence_reasoning']}")
        self._lines.append(f"")

    def log_tool_result(self, tool_name: str, result: str) -> None:
        # Truncate long results
        display_result = result if len(result) < 500 else result[:500] + "..."
        self._lines.append(f"**Result** (`{tool_name}`):")
        self._lines.append(f"```")
        self._lines.append(display_result)
        self._lines.append(f"```")
        self._lines.append(f"")

    def log_user_decision(self, level: str, decision: str) -> None:
        self._lines.append(f"**User decision** (confidence={level}): `{decision}`")
        self._lines.append(f"")

    def finalize(self) -> None:
        """Write the final workspace state and save to disk."""
        self._lines.append(f"---")
        self._lines.append(f"")
        self._lines.append(f"## Final Workspace State")
        self._lines.append(f"")
        self._log_workspace_state()
        self._lines.append(f"")
        self._lines.append(f"---")
        self._lines.append(f"*Transcript ended at {datetime.now(timezone.utc).isoformat()}*")

        with open(self.filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(self._lines))

    def save_partial(self) -> None:
        """Save current state without final workspace snapshot."""
        with open(self.filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(self._lines))
