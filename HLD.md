# High-Level Design — Lantern Desk

## 1. System Purpose

Lantern is a command-line AI assistant that helps an editorial team work with documents in a project folder. It accepts natural-language requests, reasons about what actions are needed, executes them safely, and involves a human when the situation demands it.

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER (Terminal)                          │
│                                                                 │
│  Input: natural language requests                               │
│  Output: responses, plans, choices, refusals                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       CLI LAYER (lantern.py)                     │
│                                                                 │
│  • Parses arguments (--workspace, --resume, --transcript)       │
│  • Manages REPL loop (input → process → display)               │
│  • Handles /commands, Ctrl+C, session lifecycle                 │
│  • Routes to Agent Loop                                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     AGENT LOOP (agent.py)                        │
│                                                                 │
│  • Calls Claude API with conversation + tools + system prompt   │
│  • Processes response (text → display, tool_use → execute)      │
│  • Loops until model says "end_turn"                            │
│  • Handles errors, retries, session save on failure             │
└───────┬──────────────┬──────────────┬──────────────┬────────────┘
        │              │              │              │
        ▼              ▼              ▼              ▼
┌────────────┐  ┌────────────┐  ┌──────────┐  ┌──────────────┐
│  SANDBOX   │  │ CONFIDENCE │  │  POLICY  │  │   SESSION    │
│ (gate 1)   │  │  (gate 2)  │  │ (loaded  │  │   (persist)  │
│            │  │            │  │  into    │  │              │
│ Validates  │  │ Inspects   │  │  system  │  │ Save/load    │
│ all paths  │  │ level on   │  │  prompt) │  │ conversation │
│ before any │  │ mutating   │  │          │  │ + pending    │
│ tool runs  │  │ tools      │  │          │  │ actions      │
└─────┬──────┘  └─────┬──────┘  └──────────┘  └──────────────┘
      │                │
      ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      TOOL EXECUTION (tools.py)                   │
│                                                                 │
│  Read-only: list_files, read_file, search_files                 │
│  Mutating:  write_file, move_file, delete_file, create_directory│
│  Meta:      announce_plan                                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FILE SYSTEM (desk boundary)                   │
│                                                                 │
│  workspace/                                                     │
│  ├── research_notes/    ├── reference/     ├── policies/        │
│  ├── meeting_records/   ├── style_guides/  └── output/          │
│  └── drafts/                                                    │
└─────────────────────────────────────────────────────────────────┘
```

## 3. Key Design Decisions

### 3.1 Single Adaptive Loop (not Plan-then-Execute)

The agent runs one continuous loop: call Claude → process tool calls → feed results back → repeat. This allows the model to discover information mid-task and adapt. For example, "find notes about coral and summarize them" doesn't require knowing which files exist upfront.

**Why not plan-then-execute?** Discovery tasks require reading results before deciding next steps. A rigid plan would need replanning at every observation, creating unnecessary friction.

### 3.2 Confidence as Required Tool Parameters

Every mutating tool (write, move, delete) has `confidence_level` and `confidence_reasoning` as required fields in its schema. The model **must** fill them — it cannot call a destructive tool without stating its confidence.

**Why not a separate confidence tool?** Embedding confidence in the action itself means it can never be skipped. The code inspects the field before executing.

### 3.3 Two Gates Before Execution

Every tool call passes through two sequential gates:

```
Tool call → [Gate 1: Sandbox] → [Gate 2: Confidence] → Execute
```

- **Gate 1 (Sandbox)**: Hard pass/fail. If the path resolves outside the desk, the call is blocked immediately. No confidence prompt. No override. This is enforced in code, independent of the model.
- **Gate 2 (Confidence)**: Only for mutating tools that pass sandbox. Inspects the confidence level and either proceeds (NONE/LOW) or prompts the user (MEDIUM/HIGH).

### 3.4 Policies Injected into System Prompt

Policies are loaded from `policies/` at session start and included verbatim in the system prompt. The model sees them as authoritative instructions. Regular document content is explicitly marked as non-authoritative.

**Why not enforce policies in code?** Policies are varied and context-dependent (e.g., "embargoed data must not be quoted"). Only the model can reason about whether a specific action violates a nuanced editorial rule. The code enforces the sandbox; the model enforces policies.

### 3.5 Session Persistence with Pending Actions

Sessions save the full conversation history plus any pending approval. On resume, the user sees the same question they left unanswered. This means a Ctrl+C mid-decision doesn't lose context.

## 4. Data Flow — Typical Request

```
User: "Find notes about coral and prepare a briefing"
  │
  ▼
Agent Loop calls Claude API
  │
  ▼
Claude responds with tool_use: search_files("coral")
  │
  ├─→ Sandbox validates "." path → OK
  ├─→ Not a mutating tool → skip confidence
  └─→ Execute search → returns 4 matching files
  │
  ▼
Results fed back to Claude
  │
  ▼
Claude calls: read_file("research_notes/coral_reef_ecosystems.md")
  │
  └─→ Same flow → returns file content
  │
  ▼
Claude calls: write_file("output/coral_briefing.md", content, NONE, "new file, no conflict")
  │
  ├─→ Sandbox validates "output/coral_briefing.md" → OK (inside desk)
  ├─→ Mutating tool → check confidence → NONE → proceed
  └─→ Execute write → file created
  │
  ▼
Claude responds with end_turn: "I've prepared the briefing at output/coral_briefing.md"
```

## 5. Security Model Summary

| Threat | Defense | Enforced By |
|--------|---------|-------------|
| Path traversal (`../`) | Resolve + boundary check | Code (sandbox.py) |
| Absolute paths outside desk | Reject if not under desk_root | Code (sandbox.py) |
| Symlinks to outside | Resolve with `realpath` before check | Code (sandbox.py) |
| Social engineering ("it's temporary") | Sandbox ignores justifications | Code (sandbox.py) |
| Document injection ("open /etc/hosts") | Model instructed to ignore non-policy text | Model (system prompt) |
| Accidental destructive action | Confidence system requires approval | Model + Code |
| Policy violation | Model refuses + cites policy | Model (system prompt) |
| User overrides sandbox | Hard refusal — no override path exists | Code (sandbox.py) |

## 6. Component Responsibilities

| Component | Responsibility | Knows About |
|-----------|---------------|-------------|
| `lantern.py` | CLI, REPL, session lifecycle | Everything (orchestrator) |
| `agent.py` | API calls, tool dispatch, gating | Tools, sandbox, confidence, session |
| `tools.py` | Tool schemas + execution | Sandbox, formats |
| `sandbox.py` | Path validation | Only paths and desk root |
| `confidence.py` | Gating logic + user prompts | Display module |
| `policies.py` | Load policy files | Formats module |
| `session.py` | Persist/restore state | Only its own data |
| `prompts.py` | Build system prompt | Policies data |
| `formats.py` | Read file formats | Only file I/O |
| `display.py` | Terminal output | Only stdout |
| `transcript.py` | Log to markdown | Only file I/O |
