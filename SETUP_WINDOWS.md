# Setup Guide — Windows

## Prerequisites

- Python 3.10 or later (download from [python.org](https://www.python.org/downloads/))
- During installation, check "Add Python to PATH"
- An Anthropic API key

## Installation

1. **Open Command Prompt or PowerShell**

2. **Navigate to the project directory**:

```cmd
cd path\to\lantern
```

3. **Create a virtual environment**:

```cmd
python -m venv venv
venv\Scripts\activate
```

4. **Install dependencies**:

```cmd
pip install -r requirements.txt
```

5. **Set the API key**:

Command Prompt:
```cmd
set ANTHROPIC_API_KEY=your-api-key-here
```

PowerShell:
```powershell
$env:ANTHROPIC_API_KEY = "your-api-key-here"
```

Optionally, set a specific model:
```cmd
set LANTERN_MODEL=claude-haiku-4-5-20251001
```

## Running Lantern

### New session in the example workspace

```cmd
python lantern.py workspace\
```

### Resume the most recent session

```cmd
python lantern.py workspace\ --resume
```

### Resume a specific session by ID

```cmd
python lantern.py workspace\ --resume --session <session-id>
```

### Record a transcript

```cmd
python lantern.py workspace\ --transcript transcripts\my_run.md
```

### Interactive commands

Once running:
- `/help` — show available commands
- `/save` — save session without exiting
- `/sessions` — list all saved sessions
- `/quit` — save and exit

## Running Automated Tests

```cmd
pytest tests\ -v
```

Expected: 110 tests pass, 0 failures.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `python` not recognized | Reinstall Python with "Add to PATH" checked, or use `py` instead |
| `ANTHROPIC_API_KEY not set` | Run `set ANTHROPIC_API_KEY=your-key` (CMD) or `$env:ANTHROPIC_API_KEY = "your-key"` (PowerShell) |
| `model: not found` | Set `LANTERN_MODEL` to an available model |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| Encoding errors reading .docx/.pdf | Ensure you're using Python 3.10+ (older versions may have issues) |
| `venv\Scripts\activate` fails in PowerShell | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` first |

## Notes

- Use backslashes (`\`) for paths in CMD, or forward slashes (`/`) in PowerShell (both work in Python)
- The workspace boundary uses OS-native path resolution, so all sandbox checks work correctly on Windows
- Session files are stored in `workspace\.lantern_sessions\`
