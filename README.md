# Continuous Claude

Run Claude Code in a loop with automatic PR management.

## Features

- Iterative Claude Code execution
- Automatic git branch creation and PR management
- CI check monitoring and merging
- Context persistence across iterations

## Installation

```bash
# Install dependencies
pip install -r requirements.txt  # No Python dependencies needed

# Or use directly
chmod +x continuous_claude.py
```

## Prerequisites

- Claude Code CLI (https://claude.ai/code)
- GitHub CLI (gh) - authenticated
- jq - JSON parsing utility

## Usage

```bash
./continuous_claude.py -p "add unit tests" -m 5

# Or with explicit repo
./continuous_claude.py -p "fix bugs" -m 10 --owner myuser --repo myproject

# Use merge commits
./continuous_claude.py -p "add features" -m 5 --merge-strategy merge
```

## Options

- `-p, --prompt`: Task prompt for Claude Code (required)
- `-m, --max-runs`: Maximum number of iterations (required)
- `--owner`: GitHub repository owner (auto-detected if not provided)
- `--repo`: GitHub repository name (auto-detected if not provided)
- `--merge-strategy`: PR merge strategy: squash, merge, or rebase (default: squash)
- `--notes-file`: Path to shared task notes file (default: SHARED_TASK_NOTES.md)
- `--completion-signal`: Phrase that signals project completion
- `--completion-threshold`: Number of consecutive signals to stop (default: 3)

## License

MIT
