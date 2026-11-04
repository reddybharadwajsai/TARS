# Submission Checklist

## Application Source Code
- [x] `lantern.py` — CLI entry point + REPL
- [x] `agent.py` — Agentic loop (Claude API + tool orchestration)
- [x] `tools.py` — Tool definitions (JSON schemas) + execution logic
- [x] `prompts.py` — System prompt template + builder
- [x] `sandbox.py` — Path validation + boundary enforcement
- [x] `policies.py` — Policy loading from `policies/` folder
- [x] `confidence.py` — Confidence gating logic + user prompting
- [x] `session.py` — Session persistence (save/load/resume)
- [x] `formats.py` — File format readers (.txt, .md, .docx, .pdf)
- [x] `display.py` — Terminal output formatting
- [x] `transcript.py` — Structured transcript logger
- [x] `requirements.txt` — Python dependencies

## Workspace Structure (minimum requirements from assignment)
- [x] At least 5 source folders → we have: research_notes/, meeting_records/, drafts/, reference/, style_guides/
- [x] At least 2 documents per folder → all folders have 2+
- [x] At least 10 source documents total → we have 14 (excluding policies)
- [x] Each document at least 300 words → all verified ≥300
- [x] Supported formats (.txt, .md, .docx, .pdf) → all 4 present
- [x] At least 1 policy document (doesn't count toward 10) → 2 policies
- [x] At least 1 output folder → output/ exists
- [x] All files inside Lantern's working directory → verified
- [x] Policy files clearly identifiable → in `policies/` folder

## Recorded Test Runs (minimum 6 required)
- [x] Run 1: Ordinary search or question → `run_1_simple_search.md`
- [x] Run 2: Task combining search with generation → `run_2_multistep_generation.md`
- [x] Run 3: Ambiguous request requiring meaningful choice → `run_3_ambiguous_request.md`
- [x] Run 4: Consequential action requiring explicit approval → `run_4_destructive_action.md`
- [x] Run 5: Session stopped and resumed → `run_5_session_resume.md`
- [x] Run 6: Adversarial — escape working directory → `run_6_adversarial_sandbox.md`
- [x] Run 7: Adversarial — bypass a policy → `run_7_adversarial_policy.md`
- [x] Run 8: Adversarial — indirect via document content → `run_8_adversarial_indirect.md`

## Transcript Content (each run must contain)
- [x] Starting files that matter
- [x] Exact user messages
- [x] Lantern's responses and choices
- [x] Actions it attempted (tool calls)
- [x] Assigned confidence level visible
- [x] Final effect on the workspace
- [x] Includes both successful AND unsuccessful/refused runs

## Automated Tests
- [x] `tests/test_sandbox.py` — Boundary enforcement (21 cases)
- [x] `tests/test_formats.py` — File format reading (9 cases)
- [x] `tests/test_policies.py` — Policy detection and loading (7 cases)
- [x] `tests/test_tools.py` — Tool execution + errors (36 cases)
- [x] `tests/test_confidence.py` — Confidence gating behavior (11 cases)
- [x] `tests/test_session.py` — Save/load/resume correctness (18 cases)
- [x] `tests/test_prompts.py` — System prompt builder (7 cases)
- [x] Total: 110 tests passing

## Safety Behaviors Tested
- [x] Sandbox blocks `../` traversal
- [x] Sandbox blocks absolute paths outside desk
- [x] Sandbox blocks symlinks pointing outside
- [x] Sandbox violations bypass confidence system (hard refusal)
- [x] Policy violations are refused with citation
- [x] Text in regular documents is NOT treated as instructions
- [x] User confirmation cannot override sandbox
- [x] "Temporary" path social engineering blocked

## Documentation
- [x] `README.md` — What Lantern does + design + security strategy
- [x] `SETUP.md` — Install, configure, run Lantern, run tests (Mac/Linux)
- [x] `SETUP_WINDOWS.md` — Windows-specific setup instructions

## Exclusions (must NOT be in ZIP)
- [x] No API keys in any file
- [x] No `__pycache__/` directories
- [x] No `venv/` or `.venv/` directories
- [x] No `.lantern_sessions/` leftover data
- [x] No files unrelated to the assignment

## Core Functionality Demonstrated
- [x] Natural-language conversation via CLI
- [x] Multi-step task execution (search → read → synthesize → write)
- [x] Policy awareness (consults before acting, refuses violations)
- [x] Confidence level system (NONE/LOW/MEDIUM/HIGH)
- [x] Session persistence (save on exit, resume with context)
- [x] Sandbox enforcement (hard boundary, no override)
- [x] Clarifying questions for ambiguous requests
- [x] File operations: list, read, search, write, move, delete, create_directory
- [x] Format support: .txt, .md, .docx, .pdf reading
- [x] Announce plan for complex tasks (transparency)
