"""Tool definitions (JSON schemas) and execution logic for the Lantern agent."""

import os
import glob
from sandbox import validate_path, SandboxViolation
from formats import read_document, UnsupportedFormat

# --- Tool JSON Schemas (for Anthropic API) ---

TOOL_DEFINITIONS = [
    {
        "name": "announce_plan",
        "description": "Announce your intended approach for a multi-step task. This is informational only — no approval is needed. Call this before starting complex tasks so the user can see your plan.",
        "input_schema": {
            "type": "object",
            "properties": {
                "plan": {
                    "type": "string",
                    "description": "A brief description of what you plan to do."
                },
                "steps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "The sequence of steps you intend to take."
                }
            },
            "required": ["plan", "steps"]
        }
    },
    {
        "name": "list_files",
        "description": "List files and directories at the given path (relative to the desk root). Returns names with type indicators (file/directory).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to list. Use '.' or '' for the desk root."
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "read_file",
        "description": "Read the full text content of a file. Supports .txt, .md, .docx, and .pdf formats.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file to read."
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "search_files",
        "description": "Search for text across all readable files in the desk (or a subfolder). Returns matching filenames with line snippets. Case-insensitive substring search.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The text to search for (case-insensitive)."
                },
                "path": {
                    "type": "string",
                    "description": "Optional: restrict search to this subdirectory. Defaults to entire desk."
                }
            },
            "required": ["query"]
        }
    },
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
    },
    {
        "name": "move_file",
        "description": "Move or rename a file within the desk.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Current relative path of the file."
                },
                "destination": {
                    "type": "string",
                    "description": "New relative path for the file."
                },
                "confidence_level": {
                    "type": "string",
                    "enum": ["NONE", "LOW", "MEDIUM", "HIGH"],
                    "description": "How strongly a human should be involved before this action executes."
                },
                "confidence_reasoning": {
                    "type": "string",
                    "description": "Explanation of why this confidence level was chosen."
                }
            },
            "required": ["source", "destination", "confidence_level", "confidence_reasoning"]
        }
    },
    {
        "name": "delete_file",
        "description": "Permanently delete a file from the desk. This cannot be undone.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path of the file to delete."
                },
                "confidence_level": {
                    "type": "string",
                    "enum": ["NONE", "LOW", "MEDIUM", "HIGH"],
                    "description": "How strongly a human should be involved before this action executes."
                },
                "confidence_reasoning": {
                    "type": "string",
                    "description": "Explanation of why this confidence level was chosen."
                }
            },
            "required": ["path", "confidence_level", "confidence_reasoning"]
        }
    },
    {
        "name": "create_directory",
        "description": "Create a new directory within the desk.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path of the directory to create."
                },
                "confidence_level": {
                    "type": "string",
                    "enum": ["NONE", "LOW", "MEDIUM", "HIGH"],
                    "description": "How strongly a human should be involved before this action executes."
                },
                "confidence_reasoning": {
                    "type": "string",
                    "description": "Explanation of why this confidence level was chosen."
                }
            },
            "required": ["path", "confidence_level", "confidence_reasoning"]
        }
    },
]

MUTATING_TOOLS = {"write_file", "move_file", "delete_file", "create_directory"}
READ_ONLY_TOOLS = {"list_files", "read_file", "search_files"}
META_TOOLS = {"announce_plan"}

# Path argument field names per tool
PATH_FIELDS = {
    "list_files": ["path"],
    "read_file": ["path"],
    "search_files": ["path"],
    "write_file": ["path"],
    "move_file": ["source", "destination"],
    "delete_file": ["path"],
    "create_directory": ["path"],
}


def has_path_arg(tool_name: str, args: dict) -> list[str]:
    """Return list of path field names that exist in args for this tool."""
    fields = PATH_FIELDS.get(tool_name, [])
    return [f for f in fields if f in args and args[f]]


def validate_tool_paths(tool_name: str, args: dict, desk_root: str) -> None:
    """Validate all path arguments in a tool call against the sandbox."""
    for field in has_path_arg(tool_name, args):
        validate_path(args[field], desk_root)


# --- Tool Execution Functions ---

def execute_list_files(args: dict, desk_root: str) -> str:
    """List directory contents."""
    path = args.get("path", ".")
    resolved = validate_path(path, desk_root)

    if not os.path.isdir(resolved):
        return f"Error: '{path}' is not a directory."

    entries = []
    for name in sorted(os.listdir(resolved)):
        full = os.path.join(resolved, name)
        if name.startswith("."):
            continue
        entry_type = "dir" if os.path.isdir(full) else "file"
        entries.append(f"  [{entry_type}] {name}")

    if not entries:
        return f"Directory '{path}' is empty."

    return f"Contents of '{path}':\n" + "\n".join(entries)


def execute_read_file(args: dict, desk_root: str) -> str:
    """Read file content."""
    path = args["path"]
    resolved = validate_path(path, desk_root)

    if not os.path.isfile(resolved):
        return f"Error: File '{path}' not found."

    try:
        content = read_document(resolved)
        word_count = len(content.split())
        return f"[File: {path} | {word_count} words]\n\n{content}"
    except UnsupportedFormat as e:
        return f"Error: {e}"


def execute_search_files(args: dict, desk_root: str) -> str:
    """Search for text across files."""
    query = args["query"].lower()
    search_path = args.get("path", ".")
    resolved_base = validate_path(search_path, desk_root)

    if not os.path.isdir(resolved_base):
        return f"Error: '{search_path}' is not a directory."

    results = []
    supported_exts = {".txt", ".md", ".docx", ".pdf"}

    for root, dirs, files in os.walk(resolved_base):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for filename in sorted(files):
            if filename.startswith("."):
                continue
            ext = os.path.splitext(filename)[1].lower()
            if ext not in supported_exts:
                continue

            filepath = os.path.join(root, filename)
            try:
                content = read_document(filepath)
            except (UnsupportedFormat, Exception):
                continue

            lines = content.split("\n")
            matching_lines = []
            for i, line in enumerate(lines, 1):
                if query in line.lower():
                    snippet = line.strip()[:120]
                    matching_lines.append(f"    Line {i}: {snippet}")

            if matching_lines:
                rel_path = os.path.relpath(filepath, desk_root)
                results.append(f"  {rel_path}:\n" + "\n".join(matching_lines[:3]))

    if not results:
        return f"No files found containing '{args['query']}'."

    return f"Found '{args['query']}' in {len(results)} file(s):\n" + "\n".join(results)


def execute_write_file(args: dict, desk_root: str) -> str:
    """Create or overwrite a file."""
    path = args["path"]
    content = args["content"]
    resolved = validate_path(path, desk_root)

    ext = os.path.splitext(path)[1].lower()
    if ext not in (".txt", ".md"):
        return f"Error: Cannot write '{ext}' files. Supported write formats: .txt, .md"

    # Create parent directories if needed
    parent = os.path.dirname(resolved)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

    existed = os.path.isfile(resolved)
    with open(resolved, "w", encoding="utf-8") as f:
        f.write(content)

    word_count = len(content.split())
    action = "Overwrote" if existed else "Created"
    return f"{action} '{path}' ({word_count} words)."


def execute_move_file(args: dict, desk_root: str) -> str:
    """Move or rename a file."""
    source = args["source"]
    destination = args["destination"]
    resolved_src = validate_path(source, desk_root)
    resolved_dst = validate_path(destination, desk_root)

    if not os.path.exists(resolved_src):
        return f"Error: Source '{source}' not found."

    # Create parent directories if needed
    parent = os.path.dirname(resolved_dst)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

    os.rename(resolved_src, resolved_dst)
    return f"Moved '{source}' → '{destination}'."


def execute_delete_file(args: dict, desk_root: str) -> str:
    """Delete a file."""
    path = args["path"]
    resolved = validate_path(path, desk_root)

    if not os.path.exists(resolved):
        return f"Error: '{path}' not found."

    if os.path.isdir(resolved):
        return f"Error: '{path}' is a directory. Only files can be deleted."

    os.remove(resolved)
    return f"Deleted '{path}'."


def execute_create_directory(args: dict, desk_root: str) -> str:
    """Create a directory."""
    path = args["path"]
    resolved = validate_path(path, desk_root)

    if os.path.exists(resolved):
        return f"Directory '{path}' already exists."

    os.makedirs(resolved, exist_ok=True)
    return f"Created directory '{path}'."


def execute_announce_plan(args: dict, desk_root: str) -> str:
    """Announce a plan (informational, no side effects)."""
    plan = args["plan"]
    steps = args.get("steps", [])
    steps_text = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(steps))
    return f"Plan announced: {plan}\nSteps:\n{steps_text}"


# --- Dispatcher ---

EXECUTORS = {
    "list_files": execute_list_files,
    "read_file": execute_read_file,
    "search_files": execute_search_files,
    "write_file": execute_write_file,
    "move_file": execute_move_file,
    "delete_file": execute_delete_file,
    "create_directory": execute_create_directory,
    "announce_plan": execute_announce_plan,
}


def execute_tool(tool_name: str, args: dict, desk_root: str) -> str:
    """Execute a tool by name. Returns result string or error."""
    executor = EXECUTORS.get(tool_name)
    if not executor:
        return f"Error: Unknown tool '{tool_name}'."

    try:
        return executor(args, desk_root)
    except SandboxViolation as e:
        return f"Error: {e}"
    except FileNotFoundError as e:
        return f"Error: File not found — {e}"
    except PermissionError as e:
        return f"Error: Permission denied — {e}"
    except UnsupportedFormat as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error executing {tool_name}: {type(e).__name__}: {e}"
