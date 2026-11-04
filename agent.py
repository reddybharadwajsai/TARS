"""Agent loop — orchestrates Claude API calls with tool-use."""

import os
import time
import anthropic
from tools import (
    TOOL_DEFINITIONS,
    MUTATING_TOOLS,
    META_TOOLS,
    validate_tool_paths,
    execute_tool,
)
from sandbox import SandboxViolation
from prompts import build_system_prompt
from confidence import gate_on_confidence, prompt_for_decision, PROCEED, WAIT_FOR_USER
from display import display_text, display_tool_call, display_plan, display_error


MODEL = os.environ.get("LANTERN_MODEL", "claude-haiku-4-5-20251001")
MAX_TOKENS = 4096
MAX_RETRIES = 1
RETRY_DELAY = 2


def create_client() -> anthropic.Anthropic:
    """Create Anthropic client from environment variable."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY environment variable is not set. "
            "Set it with: export ANTHROPIC_API_KEY=your-key-here"
        )
    return anthropic.Anthropic(api_key=api_key)


def run_agent_loop(user_input: str, session, transcript_logger=None) -> None:
    """
    Run the agent loop for a single user turn.
    Sends the message, processes tool calls, loops until end_turn.
    Modifies session.messages in place.
    """
    session.add_message("user", user_input)

    client = create_client()
    system_prompt = build_system_prompt(session.desk_path, session.policies)

    retries = 0
    while True:
        # Call Claude API
        try:
            response = client.messages.create(
                model=MODEL,
                system=system_prompt,
                messages=session.messages,
                tools=TOOL_DEFINITIONS,
                max_tokens=MAX_TOKENS,
            )
        except anthropic.APIConnectionError as e:
            if retries < MAX_RETRIES:
                retries += 1
                display_error(f"Connection error, retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
                continue
            display_error(f"Persistent connection error: {e}")
            session.save()
            return
        except anthropic.RateLimitError as e:
            if retries < MAX_RETRIES:
                retries += 1
                display_error(f"Rate limited, retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
                continue
            display_error(f"Rate limit exceeded: {e}")
            session.save()
            return
        except anthropic.APIError as e:
            display_error(f"API error: {e}")
            session.save()
            return

        # Reset retry counter on success
        retries = 0

        # Process response
        assistant_content = []
        tool_results = []
        has_tool_use = False
        medium_cancelled = False

        for block in response.content:
            if block.type == "text":
                display_text(block.text)
                assistant_content.append({"type": "text", "text": block.text})
                if transcript_logger:
                    transcript_logger.log_assistant_text(block.text)

            elif block.type == "tool_use":
                has_tool_use = True
                tool_name = block.name
                tool_args = block.input
                tool_id = block.id

                assistant_content.append({
                    "type": "tool_use",
                    "id": tool_id,
                    "name": tool_name,
                    "input": tool_args,
                })

                if transcript_logger:
                    transcript_logger.log_tool_call(tool_name, tool_args)

                # Handle announce_plan specially
                if tool_name in META_TOOLS:
                    if tool_name == "announce_plan":
                        display_plan(tool_args.get("plan", ""), tool_args.get("steps", []))
                    result = execute_tool(tool_name, tool_args, session.desk_path)
                    tool_results.append({"type": "tool_result", "tool_use_id": tool_id, "content": result})
                    if transcript_logger:
                        transcript_logger.log_tool_result(tool_name, result)
                    continue

                # Step 1: Sandbox validation
                try:
                    validate_tool_paths(tool_name, tool_args, session.desk_path)
                except SandboxViolation as e:
                    error_msg = f"Error: {e}"
                    display_error(str(e))
                    tool_results.append({"type": "tool_result", "tool_use_id": tool_id, "content": error_msg})
                    if transcript_logger:
                        transcript_logger.log_tool_result(tool_name, error_msg)
                    continue

                # Step 2: Confidence gating (mutating tools only)
                if tool_name in MUTATING_TOOLS:
                    level = tool_args.get("confidence_level", "HIGH")
                    reasoning = tool_args.get("confidence_reasoning", "No reasoning provided.")

                    display_tool_call(tool_name, tool_args)
                    action = gate_on_confidence(level, reasoning, tool_name, tool_args)

                    if action == WAIT_FOR_USER:
                        # Save session before blocking
                        session.pending_action = {
                            "tool_id": tool_id,
                            "tool_name": tool_name,
                            "tool_args": tool_args,
                            "level": level,
                            "reasoning": reasoning,
                        }
                        session.save()

                        # Prompt user
                        user_response = prompt_for_decision(level, reasoning, tool_name, tool_args)

                        if transcript_logger:
                            transcript_logger.log_user_decision(level, user_response)

                        session.pending_action = None

                        if level.upper() == "HIGH":
                            if user_response == "no":
                                result = "Action cancelled by user."
                                tool_results.append({"type": "tool_result", "tool_use_id": tool_id, "content": result})
                                if transcript_logger:
                                    transcript_logger.log_tool_result(tool_name, result)
                                continue
                            # User approved — fall through to execute
                        elif level.upper() == "MEDIUM":
                            if user_response == "cancel":
                                result = "Action cancelled by user."
                                tool_results.append({"type": "tool_result", "tool_use_id": tool_id, "content": result})
                                if transcript_logger:
                                    transcript_logger.log_tool_result(tool_name, result)
                                continue
                            # MEDIUM: cancel this tool call, inject user choice, let model re-reason
                            result = f"Action paused. User chose: {user_response}. Please re-issue the appropriate tool call based on the user's selection."
                            tool_results.append({"type": "tool_result", "tool_use_id": tool_id, "content": result})
                            if transcript_logger:
                                transcript_logger.log_tool_result(tool_name, result)
                            medium_cancelled = True
                            continue
                else:
                    # Read-only tool — just show execution
                    display_tool_call(tool_name, tool_args)

                # Step 3: Execute the tool
                result = execute_tool(tool_name, tool_args, session.desk_path)
                tool_results.append({"type": "tool_result", "tool_use_id": tool_id, "content": result})
                if transcript_logger:
                    transcript_logger.log_tool_result(tool_name, result)

        # Add assistant message to conversation
        session.add_raw_assistant_message(assistant_content)

        # Add tool results to conversation
        if tool_results:
            session.add_tool_results(tool_results)

        # Decide whether to loop
        if response.stop_reason == "end_turn":
            break
        elif has_tool_use:
            # Model wants to continue after seeing tool results
            continue
        else:
            break
