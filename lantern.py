"""Lantern — a cautious document assistant for the editorial desk."""

import argparse
import os
import signal
import sys

from session import Session, load_latest_session, load_session_by_id, list_sessions
from policies import load_policies
from agent import run_agent_loop
from display import display_text, display_error, display_confidence, BOLD, RESET, CYAN
from confidence import prompt_for_decision
from transcript import TranscriptLogger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lantern — a cautious document assistant for the editorial desk."
    )
    parser.add_argument(
        "workspace",
        nargs="?",
        default=".",
        help="Path to the workspace directory (default: current directory).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume the most recent session.",
    )
    parser.add_argument(
        "--session",
        type=str,
        default=None,
        help="Resume a specific session by ID.",
    )
    parser.add_argument(
        "--transcript",
        type=str,
        default=None,
        help="Path to write a structured transcript log.",
    )
    return parser.parse_args()


def print_banner(desk_path: str, session_id: str, resumed: bool) -> None:
    status = "Resumed session" if resumed else "New session"
    print(f"\n{CYAN}{BOLD}🔦 Lantern — Editorial Desk Assistant{RESET}")
    print(f"   Desk: {desk_path}")
    print(f"   {status}: {session_id}")
    print(f"   Type '/quit' to save and exit, '/help' for commands.\n")


def handle_special_command(command: str, session: Session, transcript_logger=None) -> bool:
    """Handle special /commands. Returns True if handled."""
    cmd = command.strip().lower()

    if cmd in ("/quit", "/exit", "/q"):
        session.save()
        if transcript_logger:
            transcript_logger.finalize()
        print(f"\n{CYAN}Session saved ({session.id}). Goodbye.{RESET}\n")
        sys.exit(0)

    if cmd == "/save":
        session.save()
        print(f"{CYAN}Session saved ({session.id}).{RESET}")
        return True

    if cmd == "/sessions":
        sessions = list_sessions(session.desk_path)
        if not sessions:
            print("No saved sessions found.")
        else:
            print(f"\n{'ID':<10} {'Updated':<28} {'Messages':<10} {'Pending'}")
            print("-" * 60)
            for s in sessions:
                pending = "⚠ yes" if s["has_pending"] else "no"
                print(f"{s['id']:<10} {s['updated_at']:<28} {s['message_count']:<10} {pending}")
        print()
        return True

    if cmd == "/help":
        print(f"""
{BOLD}Commands:{RESET}
  /quit     Save session and exit
  /save     Save session without exiting
  /sessions List all saved sessions
  /help     Show this help
""")
        return True

    return False


def resume_pending_action(session: Session, transcript_logger=None) -> None:
    """If the session has a pending action, re-prompt the user."""
    if not session.pending_action:
        return

    pending = session.pending_action
    level = pending["level"]
    reasoning = pending["reasoning"]
    tool_name = pending["tool_name"]

    print(f"\n{BOLD}⏸ Resuming — you had a pending decision:{RESET}")
    display_confidence(level, reasoning)

    user_response = prompt_for_decision(level, reasoning, tool_name, pending.get("tool_args", {}))

    if transcript_logger:
        transcript_logger.log_user_decision(level, user_response)

    # Inject the response and clear pending
    if level.upper() == "HIGH":
        if user_response == "yes":
            result_msg = "User approved the action on resume."
        else:
            result_msg = "Action cancelled by user on resume."
    else:
        if user_response == "cancel":
            result_msg = "Action cancelled by user on resume."
        else:
            result_msg = f"Action paused. User chose: {user_response}. Please re-issue the appropriate tool call based on the user's selection."

    # Add as a tool result for the pending tool call
    session.messages.append({
        "role": "user",
        "content": [{"type": "tool_result", "tool_use_id": pending["tool_id"], "content": result_msg}]
    })
    session.pending_action = None
    session.save()


def main() -> None:
    args = parse_args()

    # Resolve desk path
    desk_path = os.path.realpath(args.workspace)
    if not os.path.isdir(desk_path):
        display_error(f"Workspace not found: {args.workspace}")
        sys.exit(1)

    # Load policies
    policies = load_policies(desk_path)

    # Set up transcript logger
    transcript_logger = None
    if args.transcript:
        transcript_logger = TranscriptLogger(args.transcript, desk_path)

    # Create or resume session
    resumed = False
    if args.session:
        session = load_session_by_id(args.session, desk_path)
        if not session:
            display_error(f"Session '{args.session}' not found.")
            sys.exit(1)
        resumed = True
    elif args.resume:
        session = load_latest_session(desk_path)
        if not session:
            print("No previous session found. Starting a new session.")
            session = Session(desk_path=desk_path, policies=policies)
        else:
            resumed = True
    else:
        session = Session(desk_path=desk_path, policies=policies)

    # Print banner
    print_banner(desk_path, session.id, resumed)

    # Handle pending action from resumed session
    if resumed:
        resume_pending_action(session, transcript_logger)

    # Set up Ctrl+C handler
    def signal_handler(sig, frame):
        print(f"\n\n{CYAN}Interrupted. Saving session...{RESET}")
        session.save()
        if transcript_logger:
            transcript_logger.finalize()
        print(f"{CYAN}Session saved ({session.id}). Goodbye.{RESET}\n")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # REPL loop
    while True:
        try:
            user_input = input(f"{BOLD}You: {RESET}").strip()
        except EOFError:
            session.save()
            if transcript_logger:
                transcript_logger.finalize()
            print(f"\n{CYAN}Session saved ({session.id}). Goodbye.{RESET}\n")
            break

        if not user_input:
            continue

        # Check for special commands
        if user_input.startswith("/"):
            if handle_special_command(user_input, session, transcript_logger):
                continue

        # Log user input to transcript
        if transcript_logger:
            transcript_logger.log_user_input(user_input)

        # Run agent loop
        run_agent_loop(user_input, session, transcript_logger)

        # Auto-save after each turn
        session.save()

        # Save partial transcript
        if transcript_logger:
            transcript_logger.save_partial()


if __name__ == "__main__":
    main()
