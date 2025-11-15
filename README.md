# 🔂 Continuous Claude

Automated workflow that orchestrates Claude Code in a continuous loop, autonomously creating PRs, waiting for checks, and merging—so multi-step projects complete while you sleep.

## ⚙️ How it works

Using Claude Code to drive iterative development, this script fully automates the PR lifecycle from code changes through to merged commits:

- Claude Code runs in a loop based on your prompt
- All changes are committed to a new branch
- A new pull request is created
- It waits for all required PR checks and code reviews to complete
- Once checks pass and reviews are approved, the PR is merged
- This process repeats until your task is complete
- A `SHARED_TASK_NOTES.md` file maintains continuity by passing context between iterations, enabling seamless handoffs across AI and human developers

## 🚀 Quick start

### Installation

Install with a single command:

```bash
curl -fsSL https://raw.githubusercontent.com/AnandChowdhary/continuous-claude/main/install.sh | bash
```

This will:

- Install `continuous-claude` to `~/.local/bin`
- Check for required dependencies
- Guide you through adding it to your PATH if needed

### Manual installation

If you prefer to install manually:

```bash
# Download the script
curl -fsSL https://raw.githubusercontent.com/AnandChowdhary/continuous-claude/main/continuous_claude.sh -o continuous-claude

# Make it executable
chmod +x continuous-claude

# Move to a directory in your PATH
sudo mv continuous-claude /usr/local/bin/
```

### Prerequisites

Before using `continuous-claude`, you need:

1. **[Claude Code CLI](https://code.claude.com)** - Authenticate with `claude auth`
2. **[GitHub CLI](https://cli.github.com)** - Authenticate with `gh auth login`
3. **jq** - Install with `brew install jq` (macOS) or `apt-get install jq` (Linux)

### Usage

```bash
# Run with your prompt, infinite max runs, and GitHub repo
continuous-claude --prompt "add unit tests until all code is covered" --max-runs 0 --owner AnandChowdhary --repo continuous-claude
```

## 🎯 Flags

- `-p, --prompt`: Task prompt for Claude Code (required)
- `-m, --max-runs`: Number of iterations, use `0` for infinite (required)
- `--owner`: GitHub repository owner (required)
- `--repo`: GitHub repository name (required)
- `--git-branch-prefix`: Prefix for git branch names (default: `continuous-claude/`)
- `--disable-commits`: Disable automatic git commits, PR creation, and merging (useful for testing)

## 📝 Examples

```bash
# Run 5 iterations
continuous-claude -p "improve code quality" -m 5 --owner AnandChowdhary --repo continuous-claude

# Run infinitely until stopped
continuous-claude -p "add unit tests until all code is covered" -m 0 --owner AnandChowdhary --repo continuous-claude

# Use custom branch prefix
continuous-claude -p "refactor code" -m 3 --owner AnandChowdhary --repo continuous-claude --git-branch-prefix "feature/"

# Test without creating commits or PRs
continuous-claude -p "test changes" -m 2 --owner AnandChowdhary --repo continuous-claude --disable-commits
```

## 🗑️ Uninstall

To uninstall `continuous-claude`:

```bash
rm ~/.local/bin/continuous-claude
# or if you installed to /usr/local/bin:
sudo rm /usr/local/bin/continuous-claude
```

## 📊 Example output

Here's what a successful run looks like:

```
💰 (1/1) Cost: $0.042
✅ (1/1) Work completed
🌿 (1/1) Creating branch: continuous-claude/1-1763205620
💬 (1/1) Committing changes...
📦 (1/1) Changes committed on branch: continuous-claude/1-1763205620
📤 (1/1) Pushing branch...
🔨 (1/1) Creating pull request...
🔍 (1/1) PR #3 created, waiting for checks...
✅ (1/1) No checks configured
✅ (1/1) All PR checks and reviews passed
🔀 (1/1) Merging PR #3...
📥 (1/1) Pulling latest from main...
🗑️  (1/1) Deleting local branch: continuous-claude/1-1763205620
✅ (1/1) PR merged and local branch cleaned up
🎉 Done with total cost: $0.042
```

## 🔄 Releases

This project uses automated semantic versioning based on commit messages:

- **Major version** (1.0.0): Breaking changes (commits with `BREAKING CHANGE`, `feat!`, `fix!`, etc.)
- **Minor version** (0.1.0): New features (commits starting with `feat:`)
- **Patch version** (0.0.1): Bug fixes and other changes

Every push to `main` automatically creates a new GitHub release. View all releases on the [releases page](https://github.com/AnandChowdhary/continuous-claude/releases).

## 📃 License

MIT (c) [Anand Chowdhary](https://anandchowdhary.com)
