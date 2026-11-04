# Setup Guide

## Prerequisites

- Python 3.10 or later
- An Anthropic API key

## Installation

1. **Create a virtual environment** (recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**:

```bash
pip install -r requirements.txt
```

3. **Set the API key**:

```bash
export ANTHROPIC_API_KEY=your-api-key-here
```

Optionally, set a specific model (defaults to `claude-haiku-4-5-20251001`):

```bash
export LANTERN_MODEL=claude-haiku-4-5-20251001
```

## Running Lantern

### New session in the example workspace

```bash
python lantern.py workspace/
```

### Resume the most recent session

```bash
python lantern.py workspace/ --resume
```

### Resume a specific session by ID

```bash
python lantern.py workspace/ --resume --session <session-id>
```

### Record a transcript

```bash
python lantern.py workspace/ --transcript transcripts/my_run.md
```

### Interactive commands

Once running, you can use:
- `/help` — show available commands
- `/save` — save session without exiting
- `/sessions` — list all saved sessions
- `/quit` — save and exit

## Running Automated Tests

```bash
pytest tests/ -v
```

Expected: 110 tests pass, 0 failures.

## Running with the Demo Workspace

The `workspace/` directory contains a pre-built editorial project with:
- 14 source documents across 5 folders
- 2 policy documents defining editorial rules
- Mixed formats (.md, .txt, .docx, .pdf)
- An output folder for generated content

Example interactions to try:

```bash
# Simple search
python lantern.py workspace/
> What do our notes say about coral reefs?

# Multi-step generation
> Find discussions about the coastal chapter and prepare an editor's note

# Ambiguous request (will ask for clarification)
> Turn these notes into a document

# Policy test (will be refused)
> Update chapter_3_approved_final.md with new data

# Sandbox test (will be refused)
> Read /etc/passwd
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ANTHROPIC_API_KEY not set` | Run `export ANTHROPIC_API_KEY=your-key` |
| `model: not found` | Set `LANTERN_MODEL` to an available model |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| Tests fail on PDF | Install `reportlab` for PDF creation tests |
