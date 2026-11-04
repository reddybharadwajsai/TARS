"""Confidence gating — inspects confidence level on mutating tools and handles user prompts."""

from display import (
    display_confidence,
    prompt_yes_no,
    prompt_choice,
)


# Return values from gate_on_confidence
PROCEED = "PROCEED"
WAIT_FOR_USER = "WAIT_FOR_USER"
CANCELLED = "CANCELLED"


def gate_on_confidence(level: str, reasoning: str, tool_name: str, args: dict) -> str:
    """
    Evaluate confidence level and determine whether to proceed or wait.
    Returns PROCEED or WAIT_FOR_USER.
    """
    level = level.upper()

    if level == "NONE":
        display_confidence(level, reasoning)
        return PROCEED

    if level == "LOW":
        display_confidence(level, reasoning)
        return PROCEED

    if level in ("MEDIUM", "HIGH"):
        display_confidence(level, reasoning)
        return WAIT_FOR_USER

    # Unknown level — treat as HIGH for safety
    display_confidence("HIGH", f"Unknown confidence level '{level}'. Treating as HIGH. {reasoning}")
    return WAIT_FOR_USER


def prompt_for_decision(level: str, reasoning: str, tool_name: str, args: dict) -> str | None:
    """
    Prompt the user based on confidence level.
    Returns:
      - For HIGH: "yes" or "no"
      - For MEDIUM: the user's choice text, or "cancel"
    """
    if level.upper() == "HIGH":
        return prompt_yes_no(reasoning)

    if level.upper() == "MEDIUM":
        return prompt_choice(reasoning)

    return None
