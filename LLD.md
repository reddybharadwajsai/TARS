# Low-Level Design — Lantern Desk

## 1. Module Specifications

### 1.1 sandbox.py

**Purpose**: Enforce the desk boundary for all file operations.

**Classes**:
```python
class SandboxViolation(Exception):
    """Raised when a path resolves outside the desk boundary."""
```

**Functions**:
```python
def validate_path(requested_path: str, desk_root: str) -> str:
    """
    Input:  A path string (relative or absolute) and the desk root.
    Output: The resolved absolute path if valid.
    Raises: SandboxViolation if the resolved path is outside desk_root.
    
    Algorithm:
    1. desk_root = os.path.realpath(desk_root)  # resolve symlinks in desk itself
    2. If requested_path is absolute:
         resolved = os.path.realpath(requested_path)
       Else:
         resolved = os.path.realpath(os.path.join(desk_root, requested_path))
    3. If resolved == desk_root → return (accessing desk root itself is OK)
    4. If resolved.startswith(desk_root + os.sep) → return (inside desk)
    5. Otherwise → raise SandboxViolation
    
    The os.sep check prevents prefix collisions:
      desk = "/tmp/abc", path resolves to "/tmp/abcdef" → blocked
    """
```

**Security invariants**:
- `os.path.realpath` is called BEFORE the boundary check (resolves symlinks)
- The check uses `desk_root + os.sep` (not just `startswith(desk_root)`)
- No try/except around this function — violations must propagate

---

### 1.2 formats.py

**Purpose**: Extract plain text from supported file formats.

**Classes**:
```python
class UnsupportedFormat(Exception):
    """Raised for unreadable file extensions."""
```

**Functions**:
```python
def read_text(path: str) -> str
    # Opens file as UTF-8, returns full content.

def read_docx(path: str) -> str
    # Uses python-docx Document class.
    # Extracts text from all paragraphs, joins with double newlines.
    # Skips empty paragraphs.

def read_pdf(path: str) -> str
    # Uses pypdf PdfReader.
    # Iterates all pages, calls page.extract_text().
    # Joins pages with double newlines.
    # Skips pages where extract_text() returns None.

def read_document(path: str) -> str
    # Dispatcher: checks os.path.splitext(path)[1].lower()
    # Routes: .txt/.md → read_text, .docx → read_docx, .pdf → read_pdf
    # Unknown → raises UnsupportedFormat
```

---

### 1.3 policies.py

**Purpose**: Load policy documents from the `policies/` folder.

**Functions**:
```python
def load_policies(desk_root: str) -> list[dict]:
    """
    Returns: [{"filename": "editorial_policy.md", "content": "..."}, ...]
    
    Algorithm:
    1. policy_dir = os.path.join(desk_root, "policies")
    2. If not a directory → return []
    3. For each file in sorted(os.listdir(policy_dir)):
       a. Skip if not a file (directories ignored)
       b. Try read_document(filepath)
       c. If UnsupportedFormat → skip silently
       d. Append {"filename", "content"} to list
    4. Return sorted list
    """
```

**Design choice**: Policies are loaded once at session start and cached in the Session object. They're re-injected into the system prompt on every API call.

---

### 1.4 prompts.py

**Purpose**: Assemble the system prompt from template + dynamic content.

**Constants**:
```python
SYSTEM_PROMPT_TEMPLATE = """..."""  # ~50 lines covering:
    # - Role definition (Lantern, editorial assistant)
    # - Desk boundary rule (hard constraint, no override)
    # - Confidence level instructions (NONE/LOW/MEDIUM/HIGH)
    # - How to handle content ambiguity (ask in text) vs action ambiguity (tool param)
    # - Policy section (injected dynamically)
    # - Critical rules (5 numbered rules)

POLICY_SECTION_TEMPLATE = """### {filename}\n{content}\n"""

NO_POLICIES_TEXT = "No policy documents found in the policies/ folder."
```

**Functions**:
```python
def build_system_prompt(desk_path: str, policies: list[dict]) -> str:
    """
    Substitutes {desk_path} and {policies_section} into the template.
    If policies list is empty, uses NO_POLICIES_TEXT.
    Called on every API request (cheap string formatting).
    """
```

---

### 1.5 tools.py

**Purpose**: Define tool schemas for the Anthropic API and implement execution logic.

**Data structures**:
```python
TOOL_DEFINITIONS: list[dict]    # 8 tool schemas (Anthropic JSON Schema format)
MUTATING_TOOLS: set[str]        # {"write_file", "move_file", "delete_file", "create_directory"}
READ_ONLY_TOOLS: set[str]       # {"list_files", "read_file", "search_files"}
META_TOOLS: set[str]            # {"announce_plan"}
PATH_FIELDS: dict[str, list]    # Maps tool name → list of parameter names containing paths
```

**Helper functions**:
```python
def has_path_arg(tool_name: str, args: dict) -> list[str]:
    """Returns list of path field names that are non-empty in args."""

def validate_tool_paths(tool_name: str, args: dict, desk_root: str) -> None:
    """Calls validate_path for each path argument. Raises SandboxViolation."""
```

**Executor functions** (one per tool):
```python
def execute_list_files(args, desk_root) -> str:
    # validate_path → os.listdir → format as "[dir] name" / "[file] name"
    # Skips hidden files (starting with .)
    
def execute_read_file(args, desk_root) -> str:
    # validate_path → read_document → returns "[File: path | N words]\n\ncontent"
    
def execute_search_files(args, desk_root) -> str:
    # validate_path on base dir → os.walk (skip hidden dirs)
    # For each supported file: read content, search query.lower() in each line
    # Returns matching filenames + first 3 line snippets (120 chars max)
    
def execute_write_file(args, desk_root) -> str:
    # validate_path → check extension (.txt/.md only) → create parent dirs → write
    # Returns "Created 'path' (N words)." or "Overwrote 'path' (N words)."
    
def execute_move_file(args, desk_root) -> str:
    # validate both paths → check source exists → create dest parent → os.rename
    
def execute_delete_file(args, desk_root) -> str:
    # validate_path → check exists → check not directory → os.remove
    
def execute_create_directory(args, desk_root) -> str:
    # validate_path → os.makedirs(exist_ok=True)
    
def execute_announce_plan(args, desk_root) -> str:
    # Pure formatting — no side effects. Returns plan + numbered steps.
```

**Dispatcher**:
```python
EXECUTORS: dict[str, callable]  # Maps tool name → executor function

def execute_tool(tool_name: str, args: dict, desk_root: str) -> str:
    """
    Catches all exceptions and returns error strings (never crashes).
    Exception hierarchy:
      SandboxViolation → "Error: Access denied..."
      FileNotFoundError → "Error: File not found..."
      PermissionError → "Error: Permission denied..."
      UnsupportedFormat → "Error: Cannot read..."
      Any other → "Error executing {tool}: {type}: {message}"
    """
```

---

### 1.6 confidence.py

**Purpose**: Gate mutating tool execution based on confidence level.

**Constants**:
```python
PROCEED = "PROCEED"
WAIT_FOR_USER = "WAIT_FOR_USER"
```

**Functions**:
```python
def gate_on_confidence(level: str, reasoning: str, tool_name: str, args: dict) -> str:
    """
    Decision table:
      NONE → display + return PROCEED
      LOW  → display + return PROCEED
      MEDIUM → display + return WAIT_FOR_USER
      HIGH → display + return WAIT_FOR_USER
      Unknown → treat as HIGH → WAIT_FOR_USER
    """

def prompt_for_decision(level: str, reasoning: str, tool_name: str, args: dict) -> str | None:
    """
    Routes to appropriate UI:
      HIGH → prompt_yes_no() → returns "yes" or "no"
      MEDIUM → prompt_choice() → returns selected option text or "cancel"
    """
```

**How MEDIUM/HIGH flow back into the agent loop** (in agent.py):
```
MEDIUM:
  1. Tool call blocked (not executed)
  2. User selects an option
  3. Tool result returned: "Action paused. User chose: {choice}. Please re-issue..."
  4. Model receives this, re-issues the tool call with correct parameters

HIGH:
  1. Tool call blocked
  2. User says "yes" or "no"
  3. If "yes" → tool executes normally
  4. If "no" → tool result: "Action cancelled by user."
```

---

### 1.7 session.py

**Purpose**: Persist conversation state between sessions.

**Storage**: `<desk>/.lantern_sessions/<session_id>.json`

**Class**:
```python
class Session:
    id: str                        # 8-char UUID prefix
    created_at: str                # ISO 8601 UTC
    updated_at: str                # ISO 8601 UTC (refreshed on every save)
    desk_path: str                 # Absolute path to desk root
    messages: list[dict]           # Anthropic API message format
    pending_action: dict | None    # Tool call awaiting user decision
    policies: list[dict]           # Cached policy content
    
    def add_message(role, content)           # Append text message
    def add_raw_assistant_message(blocks)    # Append tool_use + text blocks
    def add_tool_results(results)            # Append as user role (API format)
    def save()                               # Write to JSON file
    def to_dict()                            # Serialize
```

**Message format** (follows Anthropic API conventions):
```json
// User text message
{"role": "user", "content": "Find coral reef notes"}

// Assistant with tool use
{"role": "assistant", "content": [
  {"type": "text", "text": "I'll search for that."},
  {"type": "tool_use", "id": "toolu_123", "name": "search_files", "input": {"query": "coral"}}
]}

// Tool results (sent as user role per API spec)
{"role": "user", "content": [
  {"type": "tool_result", "tool_use_id": "toolu_123", "content": "Found in 3 files..."}
]}
```

**Pending action format**:
```json
{
  "tool_id": "toolu_456",
  "tool_name": "delete_file",
  "tool_args": {"path": "drafts/old.md", "confidence_level": "HIGH", ...},
  "level": "HIGH",
  "reasoning": "This will permanently delete 1,800 words of content."
}
```

**Resume flow**:
1. Load session from JSON
2. If `pending_action` is not null:
   a. Display the pending question to user
   b. Get their response
   c. Inject as tool_result into messages
   d. Clear pending_action
   e. Continue agent loop (model sees the result and proceeds)

---

### 1.8 agent.py

**Purpose**: Orchestrate the agentic loop — Claude API calls, tool dispatch, gating.

**Configuration**:
```python
MODEL = os.environ.get("LANTERN_MODEL", "claude-haiku-4-5-20251001")
MAX_TOKENS = 4096
MAX_RETRIES = 1
RETRY_DELAY = 2  # seconds
```

**Main function**:
```python
def run_agent_loop(user_input: str, session: Session, transcript_logger=None) -> None:
```

**Loop pseudocode**:
```
1. Append user_input to session.messages
2. LOOP:
   a. Call client.messages.create(model, system, messages, tools, max_tokens)
      - On APIConnectionError/RateLimitError: retry once, then save + return
      - On other APIError: save + return
   b. For each block in response.content:
      - If text: display to user, add to assistant content
      - If tool_use:
        i.   Sandbox validation → if SandboxViolation: return error as tool_result
        ii.  If mutating tool:
             - Check confidence level
             - If WAIT_FOR_USER:
               * Save session (pending_action)
               * Prompt user
               * HIGH + "yes" → execute
               * HIGH + "no" → return "cancelled"
               * MEDIUM + choice → return "User chose: X. Re-issue."
               * MEDIUM + cancel → return "cancelled"
             - If PROCEED → execute
        iii. If read-only tool: execute directly
        iv.  If meta tool: execute (no side effects)
   c. Append assistant message + tool results to session.messages
   d. If stop_reason == "end_turn": break
   e. If tool_use: continue loop (model wants to see results)
```

---

### 1.9 display.py

**Purpose**: Format terminal output with ANSI colors.

**Platform handling**:
```python
if sys.platform == "win32":
    os.system("")  # Enable VT100 mode on Windows 10+
```

**Functions**:
```python
def display_text(text)                    # "Lantern: {text}" in cyan
def display_confidence(level, reasoning)  # "[CONFIDENCE: X] icon reasoning" in color
def display_tool_call(name, args)         # "→ name(args)" in dim (filters confidence fields)
def display_plan(plan, steps)             # "📋 Plan: ..." with numbered steps in blue
def display_error(message)                # "Error: ..." in red
def prompt_yes_no(message)                # "Proceed? [yes/no]:" — returns "yes"/"no"
def prompt_choice(reasoning)              # Parses numbered options, shows menu, returns choice
```

**Color mapping**:
```
NONE/LOW → green
MEDIUM   → yellow
HIGH     → red
```

---

### 1.10 transcript.py

**Purpose**: Write structured markdown logs during a session.

**Class**:
```python
class TranscriptLogger:
    def __init__(filepath, desk_path)     # Write header + initial workspace tree
    def log_user_input(text)              # "### User\n> {text}"
    def log_assistant_text(text)          # "### Lantern\n{text}"
    def log_tool_call(name, args)         # "**Tool call**: `name` [CONFIDENCE: X]\n```json...```"
    def log_tool_result(name, result)     # "**Result**: ```...```" (truncated at 500 chars)
    def log_user_decision(level, decision)# "**User decision**: ..."
    def finalize()                        # Append final workspace tree + timestamp
    def save_partial()                    # Write current state without finalization
```

**Workspace tree format** (logged at start and end):
```
workspace/
  research_notes/
    coral_reef_ecosystems.md
    tide_pool_biodiversity.txt
  drafts/
    ...
```

---

### 1.11 lantern.py

**Purpose**: CLI entry point, argument parsing, REPL loop, session management.

**Arguments**:
```
workspace         Positional, default "." — path to desk
--resume          Flag — resume latest session
--session ID      String — resume specific session
--transcript FILE String — write transcript to file
```

**REPL loop**:
```
1. Parse args → resolve desk path → load policies
2. Create/resume session
3. If resumed + pending_action: re-prompt user
4. Register SIGINT handler (save session + finalize transcript)
5. LOOP:
   a. Read input (EOFError → save + exit)
   b. If starts with "/": handle_special_command
   c. Log to transcript
   d. run_agent_loop(input, session, transcript_logger)
   e. Auto-save session
   f. Save partial transcript
```

**Special commands**:
```
/quit, /exit, /q  → save + finalize transcript + exit
/save             → save session
/sessions         → list all sessions (ID, updated_at, message_count, pending)
/help             → show command list
```

---

## 2. Interaction Sequences

### 2.1 Normal Read-Only Request

```
User ──"What's in research_notes?"──→ CLI
CLI ──add_message("user", ...)──→ Session
CLI ──run_agent_loop()──→ Agent
Agent ──messages.create()──→ Claude API
Claude API ──tool_use: list_files("research_notes")──→ Agent
Agent ──validate_path("research_notes", desk)──→ Sandbox ✓
Agent ──execute_list_files()──→ Tools
Tools ──"Contents of 'research_notes': ..."──→ Agent
Agent ──append tool_result──→ Session
Agent ──messages.create()──→ Claude API
Claude API ──end_turn: "The folder contains..."──→ Agent
Agent ──display_text()──→ User
```

### 2.2 Mutating Request with HIGH Confidence

```
User ──"Delete chapter_2.md"──→ Agent
Agent ──→ Claude API
Claude API ──tool_use: delete_file(path, HIGH, "permanently deletes 642 words")──→ Agent
Agent ──validate_path()──→ Sandbox ✓
Agent ──gate_on_confidence("HIGH", ...)──→ Confidence
Confidence ──display "[CONFIDENCE: HIGH] ⚠ ..."──→ User
Agent ──save pending_action──→ Session (to disk)
Agent ──prompt_yes_no()──→ User
User ──"yes"──→ Agent
Agent ──clear pending_action──→ Session
Agent ──execute_delete_file()──→ Tools
Tools ──"Deleted 'drafts/chapter_2.md'"──→ Agent
Agent ──tool_result──→ Claude API
Claude API ──end_turn: "Done, I've deleted..."──→ User
```

### 2.3 Sandbox Violation (hard refusal)

```
User ──"Read /etc/passwd"──→ Agent
Agent ──→ Claude API
Claude API ──end_turn: "I cannot access /etc/passwd..."──→ User
                          (model refuses in text, no tool called)
```

Or if the model does call a tool:
```
Claude API ──tool_use: read_file("/etc/passwd")──→ Agent
Agent ──validate_path("/etc/passwd", desk)──→ Sandbox ✗ RAISES
Agent ──"Error: Access denied..."──→ tool_result──→ Claude API
Claude API ──end_turn: "I cannot access that path..."──→ User
```

### 2.4 Session Resume with Pending Action

```
[Previous session ended with pending HIGH approval]

User starts: python lantern.py workspace/ --resume
CLI ──load_latest_session()──→ Session (has pending_action)
CLI ──resume_pending_action()──→ 
  display: "⏸ Resuming — you had a pending decision:"
  display: "[CONFIDENCE: HIGH] This will delete..."
  prompt: "Proceed? [yes/no]:"
User ──"no"──→
CLI ──inject tool_result "Action cancelled"──→ Session.messages
CLI ──clear pending_action──→ Session
CLI ──save──→ disk
[Normal REPL continues]
```

---

## 3. Error Handling Matrix

| Error Source | Error Type | Handling | User Sees |
|-------------|-----------|----------|-----------|
| Anthropic API | ConnectionError | Retry once (2s delay), then save + return | "Connection error, retrying..." / "Persistent error" |
| Anthropic API | RateLimitError | Retry once (2s delay), then save + return | "Rate limited, retrying..." |
| Anthropic API | Other APIError | Save session + return immediately | "API error: {details}" |
| Tool execution | SandboxViolation | Return error string as tool_result | Model explains the refusal |
| Tool execution | FileNotFoundError | Return error string as tool_result | Model suggests alternatives |
| Tool execution | PermissionError | Return error string as tool_result | Model explains |
| Tool execution | UnsupportedFormat | Return error string as tool_result | Model offers alternatives |
| Tool execution | Any other Exception | Catch-all, return formatted error | Model adapts |
| User input | EOFError (pipe ends) | Save session + finalize transcript + exit | "Session saved. Goodbye." |
| User input | KeyboardInterrupt | SIGINT handler: save + finalize + exit | "Interrupted. Saving..." |

---

## 4. File Format: Session JSON

```json
{
  "id": "d26d1966",
  "created_at": "2025-02-10T14:30:00+00:00",
  "updated_at": "2025-02-10T14:35:22+00:00",
  "desk_path": "/absolute/path/to/workspace",
  "messages": [
    {"role": "user", "content": "What files are here?"},
    {"role": "assistant", "content": [
      {"type": "tool_use", "id": "toolu_1", "name": "list_files", "input": {"path": "."}}
    ]},
    {"role": "user", "content": [
      {"type": "tool_result", "tool_use_id": "toolu_1", "content": "Contents of '.':\n  [dir] drafts\n  ..."}
    ]},
    {"role": "assistant", "content": [
      {"type": "text", "text": "The workspace contains the following folders: ..."}
    ]}
  ],
  "pending_action": null,
  "policies": [
    {"filename": "editorial_policy.md", "content": "...full text..."}
  ]
}
```

---

## 5. Tool Schema Example (write_file)

```json
{
  "name": "write_file",
  "description": "Create or overwrite a file with the given content. Only supports .txt and .md formats for writing.",
  "input_schema": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "Relative path for the file to create/overwrite."
      },
      "content": {
        "type": "string",
        "description": "The text content to write to the file."
      },
      "confidence_level": {
        "type": "string",
        "enum": ["NONE", "LOW", "MEDIUM", "HIGH"],
        "description": "How strongly a human should be involved before this action executes."
      },
      "confidence_reasoning": {
        "type": "string",
        "description": "Explanation of why this confidence level was chosen. For MEDIUM: list 2-3 options. For HIGH: explain the consequence."
      }
    },
    "required": ["path", "content", "confidence_level", "confidence_reasoning"]
  }
}
```

---

## 6. Dependencies and Versions

| Package | Version | Purpose |
|---------|---------|---------|
| `anthropic` | ≥0.30.0 | Claude API SDK (tool-use support) |
| `python-docx` | ≥0.8.11 | Read .docx files |
| `pypdf` | ≥4.0.0 | Read .pdf files |
| `pytest` | ≥7.0.0 | Automated testing |
| `reportlab` | (optional) | Create test PDFs in test suite |

Python: 3.10+ (uses `match` statements, `X | None` type unions)
