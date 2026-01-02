# Continuous Claude

Run Claude Code in a loop with automatic PR management.

## Features

- Iterative Claude Code execution with automatic branch creation
- Automatic PR creation, CI check monitoring, and merging
- Cost and duration limits to control budget and time
- Context persistence across iterations via SHARED_TASK_NOTES.md
- Project completion signal detection for early stopping

## Prerequisites

- Python 3.6+
- Claude Code CLI (https://claude.ai/code)
- GitHub CLI (gh) - authenticated

## Usage

```bash
# Basic usage
./continuous_claude.py -p "add unit tests" -m 5

# With cost limit
./continuous_claude.py -p "fix bugs" -m 10 --max-cost 5.50

# With duration limit
./continuous_claude.py -p "add features" -m 5 --max-duration 1h

# With explicit repo
./continuous_claude.py -p "refactor" -m 3 --owner myuser --repo myproject

# Use merge commits instead of squash
./continuous_claude.py -p "update docs" -m 5 --merge-strategy merge
```

## Options

- `-p, --prompt`: Task prompt for Claude Code (required)
- `-m, --max-runs`: Maximum number of iterations (required)
- `--owner`: GitHub repository owner (auto-detected if not provided)
- `--repo`: GitHub repository name (auto-detected if not provided)
- `--merge-strategy`: PR merge strategy: squash, merge, or rebase (default: squash)
- `--max-cost`: Maximum total cost in USD (e.g., 5.50 for $5.50)
- `--max-duration`: Maximum duration (e.g., 1h, 30m, 45s)
- `--notes-file`: Path to shared task notes file (default: SHARED_TASK_NOTES.md)
- `--completion-signal`: Phrase that signals project completion
- `--completion-threshold`: Number of consecutive signals to stop (default: 3)

## How It Works

1. Creates a new git branch for each iteration
2. Runs Claude Code with your prompt and previous context
3. Commits changes and creates a pull request
4. Waits for CI checks to pass
5. Merges the PR and returns to main branch
6. Repeats until max runs, cost limit, duration limit, or completion signal

## License

MIT
