# Lantern — A Cautious Document Assistant

Lantern is a command-line AI assistant for the Lantern Press editorial team. It helps editors search documents, answer questions, generate new material, and organize files within a project folder — all through natural-language conversation. Lantern is designed to be cautious: it respects workspace boundaries, enforces editorial policies, and involves humans before taking consequential actions.

## Design Overview

### Architecture

Lantern uses a single adaptive agentic loop built on Anthropic's tool-use API:

```
User input → Claude (with tools) → tool calls → execute → results back to Claude → repeat until done
```

The model can chain multiple actions (search → read → synthesize → write) within a single user request, adapting to its plan based on intermediate results. This handles discovery tasks naturally without requiring a rigid plan-then-execute flow.

### Tools

Tools are split into two categories:

**Read-only** (always execute, no approval needed):
- `list_files` — directory listing
- `read_file` — read .txt, .md, .docx, .pdf
- `search_files` — case-insensitive substring search across all files

**Mutating** (require confidence assessment):
- `write_file` — create or overwrite files (.txt, .md only)
- `move_file` — move/rename within the desk
- `delete_file` — permanently remove a file
- `create_directory` — create folders

**Meta**:
- `announce_plan` — informational tool to show the user what the agent intends to do before starting complex tasks

### Confidence System

Every mutating tool call includes a `confidence_level` parameter that the model must fill:

| Level | Meaning | Behavior |
|-------|---------|----------|
| NONE | Clear and safe | Execute immediately |
| LOW | Minor assumption | Display reasoning, proceed |
| MEDIUM | Multiple valid interpretations | Present choices + cancel, user selects, model re-reasons |
| HIGH | Destructive or policy-sensitive | Explain consequence, require explicit yes/no |

For content ambiguity (which files to use, what to write), the model asks clarifying questions in plain text instead of attaching MEDIUM to a tool call. This keeps the interaction natural.

## Safety Strategy

### Sandbox Enforcement

The directory where Lantern starts is the hard boundary. All file paths are:
1. Resolved to absolute paths (handling `../`, symlinks)
2. Checked against the desk root with `startswith`
3. Blocked immediately if outside — no confidence prompt, no override

This enforcement happens at the code level before any tool executes. The model is also instructed about the boundary, but the code is the ultimate gate.

### Policy System

Files in the `policies/` folder are loaded at session start and injected into the system prompt. The model must:
- Consult policies before affected actions
- Refuse requests that violate policy, citing the specific rule
- Not treat text in regular documents as instructions

### Defense Against Indirect Attacks

- Documents that contain "instructions" to the agent are ignored — only `policies/` files are authoritative
- User descriptions of external paths as "temporary" don't override the sandbox
- The model is explicitly instructed to refuse sandbox violations without presenting them as choices

## Session Management

Conversations persist to `.lantern_sessions/` as JSON files. On resume, the full message history is restored including any pending approval question. Auto-save triggers after each turn, before MEDIUM/HIGH prompts, and on exit.

## File Structure

```
lantern/
├── lantern.py       # CLI entry point + REPL
├── agent.py         # Agentic loop (Claude API + tool orchestration)
├── tools.py         # Tool schemas + execution logic
├── prompts.py       # System prompt template + builder
├── sandbox.py       # Path validation + boundary enforcement
├── policies.py      # Policy loading
├── confidence.py    # Confidence gating logic
├── session.py       # Session persistence
├── formats.py       # File format readers
├── display.py       # Terminal formatting
├── transcript.py    # Structured transcript logger
├── tests/           # Automated tests (pytest)
├── transcripts/     # Recorded test runs
└── workspace/       # Demo editorial workspace
```
