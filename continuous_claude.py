#!/usr/bin/env python3
"""
Continuous Claude - Run Claude Code iteratively with automatic PR management
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


class ContinuousClaude:
    def __init__(self, prompt, max_runs, github_owner, github_repo,
                 merge_strategy="squash", notes_file="SHARED_TASK_NOTES.md",
                 completion_signal="CONTINUOUS_CLAUDE_PROJECT_COMPLETE",
                 completion_threshold=3, max_cost=None, max_duration_seconds=None,
                 dry_run=False):
        self.prompt = prompt
        self.max_runs = max_runs
        self.github_owner = github_owner
        self.github_repo = github_repo
        self.merge_strategy = merge_strategy
        self.notes_file = notes_file
        self.completion_signal = completion_signal
        self.completion_threshold = completion_threshold
        self.max_cost = max_cost
        self.max_duration_seconds = max_duration_seconds
        self.dry_run = dry_run

        self.error_count = 0
        self.successful_iterations = 0
        self.total_cost = 0.0
        self.completion_signal_count = 0
        self.start_time = time.time()

    def log(self, message):
        """Print message to stderr"""
        prefix = "[DRY RUN] " if self.dry_run else ""
        print(f"{prefix}{message}", file=sys.stderr)

    def run_command(self, cmd, capture_output=True, check=False):
        """Run a shell command (or simulate in dry-run mode)"""
        if self.dry_run:
            self.log(f"🔍 Would run: {cmd}")
            if capture_output:
                return "", "", 0
            return None, None, 0

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=capture_output,
                text=True,
                check=check,
                timeout=30  # Add timeout to prevent hanging
            )
            if capture_output:
                return result.stdout.strip(), result.stderr.strip(), result.returncode
            return None, None, result.returncode
        except subprocess.CalledProcessError as e:
            if capture_output:
                return e.stdout.strip(), e.stderr.strip(), e.returncode
            return None, None, e.returncode
        except subprocess.TimeoutExpired:
            self.log(f"⚠️  Command timed out: {cmd}")
            if capture_output:
                return "", "Command timed out after 30s", -1
            return None, None, -1

    def detect_github_repo(self):
        """Auto-detect GitHub owner and repo from git remote"""
        stdout, stderr, code = self.run_command("git remote get-url origin")
        if code != 0:
            return None, None

        url = stdout
        # Parse HTTPS: https://github.com/owner/repo.git
        if url.startswith("https://github.com/"):
            parts = url.replace("https://github.com/", "").replace(".git", "").split("/")
            if len(parts) >= 2:
                return parts[0], parts[1]
        # Parse SSH: git@github.com:owner/repo.git
        elif url.startswith("git@github.com:"):
            parts = url.replace("git@github.com:", "").replace(".git", "").split("/")
            if len(parts) >= 2:
                return parts[0], parts[1]

        return None, None

    def create_branch(self, iteration_num):
        """Create a new git branch for this iteration"""
        current_branch, _, _ = self.run_command("git rev-parse --abbrev-ref HEAD")
        date_str = time.strftime("%Y-%m-%d")

        # Generate random hash
        import hashlib
        random_hash = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]

        branch_name = f"continuous-claude/iteration-{iteration_num}/{date_str}-{random_hash}"

        self.log(f"🌿 Creating branch: {branch_name}")

        stdout, stderr, code = self.run_command(f"git checkout -b {branch_name}")
        if code != 0:
            self.log(f"⚠️  Failed to create branch: {stderr}")
            return None

        return branch_name

    def commit_changes(self):
        """Commit changes using Claude Code"""
        commit_prompt = (
            "Please review all uncommitted changes in the git repository. "
            "Write a commit message. Run 'git add .' to stage all changes, "
            "then commit using 'git commit -m \"your message\"'."
        )

        stdout, stderr, code = self.run_command(
            f'claude -p "{commit_prompt}" --allowedTools "Bash(git)" --dangerously-skip-permissions',
            check=False
        )

        if code != 0:
            return False

        # Verify all changes were committed
        stdout, stderr, code = self.run_command("git status --porcelain")
        if stdout.strip():
            return False

        return True

    def create_pr(self, branch_name):
        """Create a pull request and wait for checks"""
        # Get commit message
        stdout, _, _ = self.run_command("git log -1 --format=%B")
        commit_message = stdout
        commit_title = commit_message.split("\n")[0]
        commit_body = "\n".join(commit_message.split("\n")[3:])

        # Push branch
        self.log("📤 Pushing branch...")
        stdout, stderr, code = self.run_command(f"git push -u origin {branch_name}")
        if code != 0:
            self.log(f"⚠️  Failed to push branch: {stderr}")
            return False

        # Create PR
        self.log("🔨 Creating pull request...")
        cmd = (
            f'gh pr create --repo "{self.github_owner}/{self.github_repo}" '
            f'--title "{commit_title}" '
            f'--body "{commit_body}"'
        )
        stdout, stderr, code = self.run_command(cmd)

        if code != 0:
            self.log(f"⚠️  Failed to create PR: {stderr}")
            return False

        # Extract PR number
        import re
        pr_match = re.search(r'#(\d+)', stdout)
        if not pr_match:
            self.log("⚠️  Failed to extract PR number")
            return False

        pr_number = pr_match.group(1)
        self.log(f"🔍 PR #{pr_number} created, waiting for checks...")

        # Wait for PR checks
        if not self.wait_for_pr_checks(pr_number):
            self.log("⚠️  PR checks failed, closing PR...")
            self.run_command(f"gh pr close {pr_number} --repo '{self.github_owner}/{self.github_repo}' --delete-branch")
            return False

        # Merge PR
        return self.merge_pr(pr_number, branch_name)

    def wait_for_pr_checks(self, pr_number, timeout=1800):
        """Wait for PR checks to complete with better error handling"""
        max_iterations = timeout // 10
        failed_checks = []

        for i in range(max_iterations):
            stdout, stderr, code = self.run_command(
                f"gh pr view {pr_number} --repo '{self.github_owner}/{self.github_repo}' "
                "--json state,reviewDecision,statusCheckRollup"
            )

            if code != 0:
                self.log(f"⚠️  Failed to check PR status (attempt {i+1}/{max_iterations}): {stderr}")
                time.sleep(10)
                continue

            try:
                pr_data = json.loads(stdout)
                review_decision = pr_data.get("reviewDecision", "null")
                pr_state = pr_data.get("state", "OPEN")

                # Check if PR was closed
                if pr_state != "OPEN":
                    self.log(f"⚠️  PR is not open: {pr_state}")
                    return False

                # Check status checks
                checks = pr_data.get("statusCheckRollup", [])

                # Separate pending, completed, and failed checks
                pending_checks = [c for c in checks if c.get("status") in ["PENDING", "QUEUED"]]
                completed_checks = [c for c in checks if c.get("status") == "COMPLETED"]
                failed_checks = [
                    c for c in completed_checks
                    if c.get("conclusion") in ["FAILURE", "TIMED_OUT", "CANCELLED"]
                ]

                # Log pending checks periodically
                if i % 6 == 0 and pending_checks:  # Every minute
                    pending_names = [c.get("name", "unknown") for c in pending_checks]
                    self.log(f"⏳ Waiting for checks: {', '.join(pending_names)}")

                # If all checks are complete
                if not pending_checks:
                    if failed_checks:
                        failed_names = [c.get("name", "unknown") for c in failed_checks]
                        self.log(f"❌ Failed checks: {', '.join(failed_names)}")
                        return False

                    # All checks passed
                    if review_decision == "APPROVED":
                        self.log("✅ All PR checks passed and PR approved")
                    elif review_decision == "CHANGES_REQUESTED":
                        self.log("⚠️  PR checks passed but changes requested")
                        return False
                    else:
                        self.log("✅ All PR checks passed")

                    return True

            except (json.JSONDecodeError, KeyError) as e:
                self.log(f"⚠️  Failed to parse PR status: {e}")
                time.sleep(10)
                continue

            time.sleep(10)

        self.log(f"⏱️  Timeout waiting for PR checks ({timeout}s)")
        return False

    def merge_pr(self, pr_number, branch_name):
        """Merge the pull request"""
        merge_flag = {
            "squash": "--squash",
            "merge": "--merge",
            "rebase": "--rebase"
        }.get(self.merge_strategy, "--squash")

        self.log(f"🔀 Merging PR #{pr_number}...")
        stdout, stderr, code = self.run_command(
            f"gh pr merge {pr_number} --repo '{self.github_owner}/{self.github_repo}' {merge_flag}"
        )

        if code != 0:
            self.log(f"⚠️  Failed to merge PR: {stderr}")
            return False

        self.log("📥 Pulling latest from main...")
        current_branch, _, _ = self.run_command("git rev-parse --abbrev-ref HEAD")
        self.run_command(f"git checkout {current_branch or 'main'}")
        self.run_command(f"git pull origin {current_branch or 'main'}")

        self.log(f"🗑️  Deleting local branch: {branch_name}")
        self.run_command(f"git branch -D {branch_name}")

        self.log(f"✅ PR #{pr_number} merged")
        return True

    def run_claude_iteration(self, iteration_num):
        """Run a single Claude Code iteration"""
        iteration_display = f"({iteration_num}/{self.max_runs})" if self.max_runs > 0 else f"({iteration_num})"
        self.log(f"🔄 {iteration_display} Starting iteration...")

        # Create branch
        branch_name = self.create_branch(iteration_num)
        if not branch_name:
            return False

        # Build prompt with context
        enhanced_prompt = self.build_enhanced_prompt()

        # Run Claude Code
        self.log("🤖 Running Claude Code...")
        cmd = f'claude -p "{enhanced_prompt}" --dangerously-skip-permissions --output-format json'
        stdout, stderr, code = self.run_command(cmd)

        if code != 0:
            self.log(f"❌ Error running Claude Code: {stderr}")
            self.cleanup_branch(branch_name)
            return False

        # Parse result with defensive error handling
        try:
            result = json.loads(stdout)
            if isinstance(result, list):
                if not result:
                    self.log("❌ Claude returned empty list")
                    self.cleanup_branch(branch_name)
                    return False
                result = result[-1]

            result_text = result.get("result", "")

            # Handle missing or invalid cost
            try:
                cost = float(result.get("total_cost_usd", 0))
            except (ValueError, TypeError):
                cost = 0.0

            self.log(f"📝 {iteration_display} Output: {result_text[:200]}...")

            if cost > 0:
                self.log(f"💰 {iteration_display} Cost: ${cost:.3f}")
                self.total_cost += cost

            # Check for completion signal
            if self.completion_signal in result_text:
                self.completion_signal_count += 1
                self.log(f"🎯 Completion signal detected ({self.completion_signal_count}/{self.completion_threshold})")
            else:
                self.completion_signal_count = 0

        except json.JSONDecodeError as e:
            self.log(f"❌ Failed to parse Claude JSON output: {e}")
            self.log(f"🔍 Raw output (first 500 chars): {stdout[:500]}")
            self.cleanup_branch(branch_name)
            return False
        except (KeyError, IndexError, AttributeError) as e:
            self.log(f"❌ Unexpected Claude output structure: {e}")
            self.log(f"🔍 Raw output (first 500 chars): {stdout[:500]}")
            self.cleanup_branch(branch_name)
            return False

        # Commit and create PR
        self.log("💬 Committing changes...")
        if not self.commit_changes():
            self.log("⚠️  Failed to commit changes")
            self.cleanup_branch(branch_name)
            return False

        self.log("📦 Changes committed")

        if not self.create_pr(branch_name):
            self.log("⚠️  Failed to create/merge PR")
            return False

        self.successful_iterations += 1
        self.error_count = 0
        return True

    def build_enhanced_prompt(self):
        """Build the enhanced prompt with context"""
        prompt = f"""## CONTINUOUS WORKFLOW CONTEXT

This is part of a continuous development loop where work happens incrementally across multiple iterations.

**Important**: You don't need to complete the entire goal in one iteration. Just make meaningful progress on one thing.

**Project Completion Signal**: If you determine that the ENTIRE project goal is fully complete, only include the exact phrase "{self.completion_signal}" in your response.

## PRIMARY GOAL

{self.prompt}
"""

        # Add context from previous iterations
        if os.path.exists(self.notes_file):
            with open(self.notes_file, "r") as f:
                notes_content = f.read()
            prompt += f"""

## CONTEXT FROM PREVIOUS ITERATION

The following is from {self.notes_file}, maintained by previous iterations:

{notes_content}
"""

        prompt += """

## ITERATION NOTES

"""
        if os.path.exists(self.notes_file):
            prompt += f"Update the `{self.notes_file}` file with relevant context for the next iteration."
        else:
            prompt += f"Create a `{self.notes_file}` file with relevant context for the next iteration."

        prompt += """

Keep it concise and actionable. Don't include lists of completed work or unnecessary details.
"""

        return prompt

    def cleanup_branch(self, branch_name):
        """Clean up a failed branch"""
        current_branch, _, _ = self.run_command("git rev-parse --abbrev-ref HEAD")
        self.run_command(f"git checkout {current_branch or 'main'}")
        self.run_command(f"git branch -D {branch_name}")

    def run(self):
        """Main execution loop"""
        # Auto-detect GitHub repo if not provided
        if not self.github_owner or not self.github_repo:
            owner, repo = self.detect_github_repo()
            if owner and repo:
                self.github_owner = owner
                self.github_repo = repo
                self.log(f"ℹ️  Auto-detected repository: {owner}/{repo}")
            else:
                self.log("❌ Could not auto-detect GitHub repository")
                sys.exit(1)

        iteration = 1
        while True:
            # Check limits
            if self.max_runs > 0 and self.successful_iterations >= self.max_runs:
                self.log(f"✅ Reached maximum runs limit: {self.max_runs}")
                break

            if self.completion_signal_count >= self.completion_threshold:
                self.log(f"🎉 Project completion signal detected {self.completion_signal_count} times!")
                break

            if self.max_cost and self.total_cost >= self.max_cost:
                self.log(f"💰 Reached maximum cost limit: ${self.max_cost:.3f}")
                break

            if self.max_duration_seconds:
                elapsed = time.time() - self.start_time
                if elapsed >= self.max_duration_seconds:
                    self.log(f"⏱️  Reached maximum duration limit: {int(elapsed)}s")
                    break

            # Run iteration
            if not self.run_claude_iteration(iteration):
                self.error_count += 1
                if self.error_count >= 3:
                    self.log("❌ Fatal: 3 consecutive errors. Exiting.")
                    sys.exit(1)

            iteration += 1
            time.sleep(1)

        # Show summary
        elapsed = time.time() - self.start_time
        if self.total_cost > 0:
            self.log(f"🎉 Done with total cost: ${self.total_cost:.3f} in {int(elapsed)}s")
        else:
            self.log(f"🎉 Done in {int(elapsed)}s")


def main():
    parser = argparse.ArgumentParser(
        description="Continuous Claude - Run Claude Code iteratively with automatic PR management"
    )
    parser.add_argument("-p", "--prompt", required=True, help="Task prompt for Claude Code")
    parser.add_argument("-m", "--max-runs", type=int, required=True, help="Maximum number of iterations")
    parser.add_argument("--owner", help="GitHub repository owner (auto-detected if not provided)")
    parser.add_argument("--repo", help="GitHub repository name (auto-detected if not provided)")
    parser.add_argument("--merge-strategy", choices=["squash", "merge", "rebase"],
                       default="squash", help="PR merge strategy (default: squash)")
    parser.add_argument("--notes-file", default="SHARED_TASK_NOTES.md",
                       help="Shared notes file for iteration context")
    parser.add_argument("--completion-signal", default="CONTINUOUS_CLAUDE_PROJECT_COMPLETE",
                       help="Phrase that signals project completion")
    parser.add_argument("--completion-threshold", type=int, default=3,
                       help="Number of consecutive completion signals to stop (default: 3)")
    parser.add_argument("--max-cost", type=float,
                       help="Maximum total cost in USD (e.g., 5.50 for $5.50)")
    parser.add_argument("--max-duration",
                       help="Maximum duration (e.g., 1h, 30m, 45s)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Simulate execution without making real changes")

    args = parser.parse_args()

    # Parse max duration
    max_duration_seconds = None
    if args.max_duration:
        duration_str = args.max_duration.lower()
        if duration_str.endswith("h"):
            max_duration_seconds = int(duration_str[:-1]) * 3600
        elif duration_str.endswith("m"):
            max_duration_seconds = int(duration_str[:-1]) * 60
        elif duration_str.endswith("s"):
            max_duration_seconds = int(duration_str[:-1])
        else:
            print("❌ Invalid --max-duration format. Use format like 1h, 30m, or 45s", file=sys.stderr)
            sys.exit(1)

    # Check requirements
    for cmd in ["claude", "gh"]:
        result = subprocess.run(
            ["which", cmd],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"❌ Required command not found: {cmd}", file=sys.stderr)
            sys.exit(1)

    cc = ContinuousClaude(
        prompt=args.prompt,
        max_runs=args.max_runs,
        github_owner=args.owner,
        github_repo=args.repo,
        merge_strategy=args.merge_strategy,
        notes_file=args.notes_file,
        completion_signal=args.completion_signal,
        completion_threshold=args.completion_threshold,
        max_cost=args.max_cost,
        max_duration_seconds=max_duration_seconds,
        dry_run=args.dry_run
    )

    cc.run()


if __name__ == "__main__":
    main()
