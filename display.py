"""Terminal output formatting for the Lantern assistant."""

import os
import sys

# Enable ANSI escape sequences on Windows 10+
if sys.platform == "win32":
    os.system("")  # Triggers VT100 mode in Windows Terminal / CMD

# ANSI color codes
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
BLUE = "\033[34m"

CONFIDENCE_COLORS = {
    "NONE": GREEN,
    "LOW": GREEN,
    "MEDIUM": YELLOW,
    "HIGH": RED,
}

CONFIDENCE_ICONS = {
    "NONE": "✓",
    "LOW": "ℹ",
    "MEDIUM": "?",
    "HIGH": "⚠",
}


def display_text(text: str) -> None:
    """Display the model's conversational text output."""
    print(f"\n{CYAN}Lantern:{RESET} {text}\n")


def display_confidence(level: str, reasoning: str) -> None:
    """Display confidence level with appropriate formatting."""
    color = CONFIDENCE_COLORS.get(level.upper(), YELLOW)
    icon = CONFIDENCE_ICONS.get(level.upper(), "?")
    print(f"{color}{BOLD}[CONFIDENCE: {level.upper()}]{RESET} {icon} {reasoning}")


def display_tool_call(name: str, args: dict) -> None:
    """Show what tool is being executed."""
    # Filter out confidence fields for cleaner display
    display_args = {k: v for k, v in args.items()
                    if k not in ("confidence_level", "confidence_reasoning")}
    args_str = ", ".join(f"{k}={repr(v)[:50]}" for k, v in display_args.items())
    print(f"{DIM}  → {name}({args_str}){RESET}")


def display_plan(plan: str, steps: list[str]) -> None:
    """Display an announced plan."""
    print(f"\n{BLUE}{BOLD}📋 Plan:{RESET} {plan}")
    for i, step in enumerate(steps, 1):
        print(f"  {i}. {step}")
    print()


def display_error(message: str) -> None:
    """Display an error message."""
    print(f"{RED}Error:{RESET} {message}")


def prompt_yes_no(message: str) -> str:
    """Prompt for explicit yes/no approval (HIGH confidence)."""
    print(f"\n{RED}{BOLD}⚠ Approval required:{RESET}")
    print(f"  {message}")
    while True:
        try:
            response = input(f"\n{BOLD}Proceed? [yes/no]: {RESET}").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return "no"
        if response in ("yes", "y"):
            return "yes"
        if response in ("no", "n"):
            return "no"
        print("  Please answer 'yes' or 'no'.")


def prompt_choice(reasoning: str) -> str:
    """
    Present options for MEDIUM confidence.
    Parses numbered options from reasoning text.
    Returns the user's choice text or "cancel".
    """
    print(f"\n{YELLOW}{BOLD}? Choice needed:{RESET}")
    print(f"  {reasoning}")

    # Parse numbered options from reasoning
    lines = reasoning.strip().split("\n")
    options = []
    for line in lines:
        line = line.strip()
        # Match lines starting with number + dot or number + )
        if line and (line[0].isdigit() and (". " in line[:4] or ") " in line[:4])):
            options.append(line)

    if not options:
        # No parseable options — just ask for free text
        print(f"\n  (Type 'cancel' to abort)")
        try:
            response = input(f"{BOLD}Your choice: {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            return "cancel"
        return response if response else "cancel"

    # Show cancel option
    print(f"\n  Type a number to choose, or 'cancel' to abort.")
    while True:
        try:
            response = input(f"{BOLD}Choice [1-{len(options)}/cancel]: {RESET}").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return "cancel"

        if response == "cancel" or response == "c":
            return "cancel"

        try:
            idx = int(response) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except ValueError:
            pass

        print(f"  Please enter a number 1-{len(options)} or 'cancel'.")
