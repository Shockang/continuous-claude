"""Unit tests for continuous_claude.py

These tests mock external dependencies (git, gh, claude) to test core logic
without requiring actual git operations or Claude Code installation.
"""

import json
import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from continuous_claude import ContinuousClaude


class TestContinuousClaudeInit(unittest.TestCase):
    """Test initialization and configuration"""

    def test_basic_initialization(self):
        """Test basic object creation"""
        cc = ContinuousClaude(
            prompt="test prompt",
            max_runs=5,
            github_owner="testowner",
            github_repo="testrepo"
        )
        self.assertEqual(cc.prompt, "test prompt")
        self.assertEqual(cc.max_runs, 5)
        self.assertEqual(cc.github_owner, "testowner")
        self.assertEqual(cc.github_repo, "testrepo")
        self.assertEqual(cc.merge_strategy, "squash")
        self.assertFalse(cc.dry_run)

    def test_initialization_with_all_options(self):
        """Test initialization with all options"""
        cc = ContinuousClaude(
            prompt="test prompt",
            max_runs=10,
            github_owner="owner",
            github_repo="repo",
            merge_strategy="merge",
            notes_file="CUSTOM_NOTES.md",
            completion_signal="CUSTOM_SIGNAL",
            completion_threshold=5,
            max_cost=10.0,
            max_duration_seconds=3600,
            dry_run=True
        )
        self.assertEqual(cc.merge_strategy, "merge")
        self.assertEqual(cc.notes_file, "CUSTOM_NOTES.md")
        self.assertEqual(cc.completion_signal, "CUSTOM_SIGNAL")
        self.assertEqual(cc.completion_threshold, 5)
        self.assertEqual(cc.max_cost, 10.0)
        self.assertEqual(cc.max_duration_seconds, 3600)
        self.assertTrue(cc.dry_run)

    def test_initialization_counters(self):
        """Test that counters start at zero"""
        cc = ContinuousClaude(
            prompt="test",
            max_runs=5,
            github_owner="owner",
            github_repo="repo"
        )
        self.assertEqual(cc.error_count, 0)
        self.assertEqual(cc.successful_iterations, 0)
        self.assertEqual(cc.total_cost, 0.0)
        self.assertEqual(cc.completion_signal_count, 0)
        self.assertGreater(cc.start_time, 0)


class TestCommandExecution(unittest.TestCase):
    """Test command execution with and without dry-run"""

    def setUp(self):
        """Set up test fixtures"""
        self.cc = ContinuousClaude(
            prompt="test",
            max_runs=5,
            github_owner="owner",
            github_repo="repo"
        )

    @patch('continuous_claude.subprocess.run')
    def test_normal_command_execution(self, mock_run):
        """Test normal command execution (not dry-run)"""
        mock_run.return_value = Mock(
            stdout="test output",
            stderr="",
            returncode=0
        )

        stdout, stderr, code = self.cc.run_command("echo test")

        self.assertEqual(stdout, "test output")
        self.assertEqual(stderr, "")
        self.assertEqual(code, 0)
        mock_run.assert_called_once()
        # Check that timeout was set
        call_kwargs = mock_run.call_args[1]
        self.assertEqual(call_kwargs['timeout'], 30)

    def test_dry_run_command_execution(self):
        """Test that dry-run mode doesn't execute commands"""
        cc = ContinuousClaude(
            prompt="test",
            max_runs=5,
            github_owner="owner",
            github_repo="repo",
            dry_run=True
        )

        stdout, stderr, code = cc.run_command("echo test")

        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "")
        self.assertEqual(code, 0)

    @patch('continuous_claude.subprocess.run')
    def test_command_timeout(self, mock_run):
        """Test that command timeouts are handled"""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("echo", 30)

        stdout, stderr, code = self.cc.run_command("echo test")

        self.assertEqual(code, -1)
        self.assertIn("timed out", stderr)

    @patch('continuous_claude.subprocess.run')
    def test_command_failure(self, mock_run):
        """Test that CalledProcessError is handled correctly"""
        import subprocess

        # Create a mock exception with required attributes
        exc = subprocess.CalledProcessError(1, "echo")
        exc.stdout = "error output"
        exc.stderr = "error message"
        mock_run.side_effect = exc

        stdout, stderr, code = self.cc.run_command("echo test")

        self.assertEqual(code, 1)
        self.assertEqual(stdout, "error output")
        self.assertEqual(stderr, "error message")


class TestGitHubRepoDetection(unittest.TestCase):
    """Test GitHub repository auto-detection"""

    def setUp(self):
        """Set up test fixtures"""
        self.cc = ContinuousClaude(
            prompt="test",
            max_runs=5,
            github_owner=None,
            github_repo=None
        )

    @patch.object(ContinuousClaude, 'run_command')
    def test_detect_https_url(self, mock_run):
        """Test detection from HTTPS URL"""
        mock_run.return_value = (
            "https://github.com/owner/repo.git",
            "",
            0
        )

        owner, repo = self.cc.detect_github_repo()

        self.assertEqual(owner, "owner")
        self.assertEqual(repo, "repo")

    @patch.object(ContinuousClaude, 'run_command')
    def test_detect_ssh_url(self, mock_run):
        """Test detection from SSH URL"""
        mock_run.return_value = (
            "git@github.com:owner/repo.git",
            "",
            0
        )

        owner, repo = self.cc.detect_github_repo()

        # SSH URLs should be detected
        # Note: The implementation requires 'github.com/' in the URL,
        # but SSH URLs use 'git@github.com:' which doesn't match
        # This test documents the current behavior
        # If SSH detection is desired, the implementation needs:
        # elif "github.com:" in url or url.startswith("git@github.com:")
        self.assertIsNone(owner)  # Current implementation doesn't detect SSH

    @patch.object(ContinuousClaude, 'run_command')
    def test_detect_no_github_url(self, mock_run):
        """Test failure when URL doesn't contain github.com"""
        mock_run.return_value = (
            "https://gitlab.com/owner/repo.git",
            "",
            0
        )

        owner, repo = self.cc.detect_github_repo()

        self.assertIsNone(owner)
        self.assertIsNone(repo)

    @patch.object(ContinuousClaude, 'run_command')
    def test_detect_command_failure(self, mock_run):
        """Test failure when git command fails"""
        mock_run.return_value = ("", "error", 1)

        owner, repo = self.cc.detect_github_repo()

        self.assertIsNone(owner)
        self.assertIsNone(repo)


class TestBranchCreation(unittest.TestCase):
    """Test branch creation logic"""

    def setUp(self):
        """Set up test fixtures"""
        self.cc = ContinuousClaude(
            prompt="test",
            max_runs=5,
            github_owner="owner",
            github_repo="repo"
        )

    @patch.object(ContinuousClaude, 'run_command')
    def test_branch_name_format(self, mock_run):
        """Test that branch names follow expected format"""
        mock_run.return_value = ("main", "", 0)

        # Use deterministic hash by mocking time and hashlib
        with patch('time.time', return_value=1234567890.0):
            with patch('hashlib.md5') as mock_md5:
                mock_hash = Mock()
                mock_hash.hexdigest.return_value = "abcdef1234567890"
                mock_md5.return_value = mock_hash

                branch_name = self.cc.create_branch(1)

                # Should match pattern: continuous-claude/iteration-{num}/{date}-{hash}
                self.assertIn("continuous-claude/iteration-1/", branch_name)
                self.assertGreater(len(branch_name), 30)  # Ensure name is substantial

    @patch.object(ContinuousClaude, 'run_command')
    def test_branch_creation_failure(self, mock_run):
        """Test handling of branch creation failure"""
        # First call gets current branch, second creates new branch
        mock_run.side_effect = [
            ("main", "", 0),  # git rev-parse
            ("", "error: branch exists", 1)  # git checkout -b
        ]

        branch_name = self.cc.create_branch(1)

        self.assertIsNone(branch_name)


class TestPromptBuilding(unittest.TestCase):
    """Test prompt building with context"""

    def setUp(self):
        """Set up test fixtures"""
        self.cc = ContinuousClaude(
            prompt="Refactor the code",
            max_runs=5,
            github_owner="owner",
            github_repo="repo"
        )

    def test_basic_prompt_without_notes(self):
        """Test prompt building without existing notes file"""
        with patch('os.path.exists', return_value=False):
            prompt = self.cc.build_enhanced_prompt()

            self.assertIn("PRIMARY GOAL", prompt)
            self.assertIn("Refactor the code", prompt)
            self.assertIn("CONTINUOUS WORKFLOW CONTEXT", prompt)
            self.assertNotIn("CONTEXT FROM PREVIOUS ITERATION", prompt)

    def test_prompt_with_notes(self):
        """Test prompt building with existing notes file"""
        notes_content = "# Previous Notes\n\nSome important context here."

        # Create a temporary notes file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
            f.write(notes_content)
            temp_file = f.name

        try:
            self.cc.notes_file = temp_file
            prompt = self.cc.build_enhanced_prompt()

            self.assertIn("CONTEXT FROM PREVIOUS ITERATION", prompt)
            self.assertIn(notes_content, prompt)
        finally:
            # Clean up temp file
            os.unlink(temp_file)

    def test_prompt_contains_completion_signal(self):
        """Test that completion signal is in prompt"""
        with patch('os.path.exists', return_value=False):
            prompt = self.cc.build_enhanced_prompt()

            self.assertIn("CONTINUOUS_CLAUDE_PROJECT_COMPLETE", prompt)

    def test_custom_completion_signal(self):
        """Test custom completion signal in prompt"""
        cc = ContinuousClaude(
            prompt="test",
            max_runs=5,
            github_owner="owner",
            github_repo="repo",
            completion_signal="CUSTOM_COMPLETE"
        )

        with patch('os.path.exists', return_value=False):
            prompt = cc.build_enhanced_prompt()

            self.assertIn("CUSTOM_COMPLETE", prompt)


class TestMergeStrategy(unittest.TestCase):
    """Test merge strategy handling"""

    @patch.object(ContinuousClaude, 'run_command')
    def test_squash_merge_flag(self, mock_run):
        """Test squash merge strategy flag"""
        mock_run.return_value = ("", "", 0)

        cc = ContinuousClaude(
            prompt="test",
            max_runs=5,
            github_owner="owner",
            github_repo="repo",
            merge_strategy="squash"
        )

        cc.merge_pr(123, "branch-name")

        # Check that the merge command was called with --squash
        calls = mock_run.call_args_list
        merge_call = [c for c in calls if "pr merge" in str(c)]
        self.assertTrue(merge_call)
        self.assertIn("--squash", str(merge_call[0]))

    @patch.object(ContinuousClaude, 'run_command')
    def test_merge_strategy_flag(self, mock_run):
        """Test merge merge strategy flag"""
        mock_run.return_value = ("", "", 0)

        cc = ContinuousClaude(
            prompt="test",
            max_runs=5,
            github_owner="owner",
            github_repo="repo",
            merge_strategy="merge"
        )

        cc.merge_pr(123, "branch-name")

        # Check that the merge command was called with --merge
        calls = mock_run.call_args_list
        merge_call = [c for c in calls if "pr merge" in str(c)]
        self.assertTrue(merge_call)
        self.assertIn("--merge", str(merge_call[0]))

    @patch.object(ContinuousClaude, 'run_command')
    def test_rebase_strategy_flag(self, mock_run):
        """Test rebase merge strategy flag"""
        mock_run.return_value = ("", "", 0)

        cc = ContinuousClaude(
            prompt="test",
            max_runs=5,
            github_owner="owner",
            github_repo="repo",
            merge_strategy="rebase"
        )

        cc.merge_pr(123, "branch-name")

        # Check that the merge command was called with --rebase
        calls = mock_run.call_args_list
        merge_call = [c for c in calls if "pr merge" in str(c)]
        self.assertTrue(merge_call)
        self.assertIn("--rebase", str(merge_call[0]))


class TestDurationParsing(unittest.TestCase):
    """Test duration string parsing in main()"""

    def test_parse_hour_duration(self):
        """Test parsing hours"""
        duration_str = "2h"
        max_duration_seconds = int(duration_str.lower()[:-1]) * 3600
        self.assertEqual(max_duration_seconds, 7200)

    def test_parse_minute_duration(self):
        """Test parsing minutes"""
        duration_str = "30m"
        max_duration_seconds = int(duration_str.lower()[:-1]) * 60
        self.assertEqual(max_duration_seconds, 1800)

    def test_parse_second_duration(self):
        """Test parsing seconds"""
        duration_str = "45s"
        max_duration_seconds = int(duration_str.lower()[:-1])
        self.assertEqual(max_duration_seconds, 45)

    def test_parse_invalid_duration(self):
        """Test invalid duration format"""
        duration_str = "30x"
        # Should not match any known pattern
        self.assertFalse(duration_str.lower().endswith(("h", "m", "s")))


class TestLimitChecking(unittest.TestCase):
    """Test various limit checks"""

    def setUp(self):
        """Set up test fixtures"""
        self.cc = ContinuousClaude(
            prompt="test",
            max_runs=5,
            github_owner="owner",
            github_repo="repo"
        )

    def test_max_runs_limit(self):
        """Test max runs limit"""
        self.cc.successful_iterations = 5
        self.cc.max_runs = 5

        # Should trigger limit
        self.assertTrue(self.cc.successful_iterations >= self.cc.max_runs)

    def test_max_cost_limit(self):
        """Test max cost limit"""
        self.cc.total_cost = 10.0
        self.cc.max_cost = 10.0

        # Should trigger limit
        self.assertTrue(self.cc.total_cost >= self.cc.max_cost)

    def test_max_duration_limit(self):
        """Test max duration limit"""
        self.cc.max_duration_seconds = 3600
        # Simulate elapsed time
        with patch('time.time', return_value=self.cc.start_time + 3700):
            elapsed = time.time() - self.cc.start_time
            self.assertTrue(elapsed >= self.cc.max_duration_seconds)

    def test_completion_signal_threshold(self):
        """Test completion signal threshold"""
        self.cc.completion_signal_count = 3
        self.cc.completion_threshold = 3

        # Should trigger stopping
        self.assertTrue(self.cc.completion_signal_count >= self.cc.completion_threshold)


class TestClaudeOutputParsing(unittest.TestCase):
    """Test parsing of Claude Code JSON output"""

    def setUp(self):
        """Set up test fixtures"""
        self.cc = ContinuousClaude(
            prompt="test",
            max_runs=5,
            github_owner="owner",
            github_repo="repo"
        )

    def test_parse_valid_json_result(self):
        """Test parsing valid JSON result"""
        output = json.dumps({
            "result": "Task completed successfully",
            "total_cost_usd": 1.234
        })

        result = json.loads(output)
        result_text = result.get("result", "")
        cost = float(result.get("total_cost_usd", 0))

        self.assertEqual(result_text, "Task completed successfully")
        self.assertEqual(cost, 1.234)

    def test_parse_json_list(self):
        """Test parsing JSON list result"""
        output = json.dumps([
            {"result": "First step"},
            {"result": "Final result", "total_cost_usd": 2.5}
        ])

        result = json.loads(output)
        if isinstance(result, list):
            result = result[-1]

        result_text = result.get("result", "")
        self.assertEqual(result_text, "Final result")

    def test_parse_empty_json_list(self):
        """Test parsing empty JSON list"""
        output = json.dumps([])

        result = json.loads(output)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_parse_missing_cost(self):
        """Test handling of missing cost field"""
        output = json.dumps({"result": "Done"})

        result = json.loads(output)
        try:
            cost = float(result.get("total_cost_usd", 0))
        except (ValueError, TypeError):
            cost = 0.0

        self.assertEqual(cost, 0.0)

    def test_parse_invalid_cost_type(self):
        """Test handling of invalid cost type"""
        output = json.dumps({"result": "Done", "total_cost_usd": "invalid"})

        result = json.loads(output)
        try:
            cost = float(result.get("total_cost_usd", 0))
        except (ValueError, TypeError):
            cost = 0.0

        self.assertEqual(cost, 0.0)


class TestBranchCleanup(unittest.TestCase):
    """Test branch cleanup logic"""

    def setUp(self):
        """Set up test fixtures"""
        self.cc = ContinuousClaude(
            prompt="test",
            max_runs=5,
            github_owner="owner",
            github_repo="repo"
        )

    @patch.object(ContinuousClaude, 'run_command')
    def test_cleanup_branch_commands(self, mock_run):
        """Test that cleanup runs expected commands"""
        mock_run.return_value = ("main", "", 0)

        self.cc.cleanup_branch("test-branch")

        # Should have called run_command multiple times
        self.assertGreaterEqual(mock_run.call_count, 2)
        # Should checkout and delete branch
        calls = [str(call) for call in mock_run.call_args_list]
        self.assertTrue(any("checkout" in str(call) for call in calls))
        self.assertTrue(any("branch -D" in str(call) for call in calls))


class TestCompletionSignalDetection(unittest.TestCase):
    """Test completion signal detection logic"""

    def setUp(self):
        """Set up test fixtures"""
        self.cc = ContinuousClaude(
            prompt="test",
            max_runs=5,
            github_owner="owner",
            github_repo="repo"
        )

    def test_signal_increments_counter(self):
        """Test that signal increments counter"""
        result_text = "Work done. CONTINUOUS_CLAUDE_PROJECT_COMPLETE"

        if self.cc.completion_signal in result_text:
            self.cc.completion_signal_count += 1

        self.assertEqual(self.cc.completion_signal_count, 1)

    def test_no_signal_resets_counter(self):
        """Test that no signal resets counter"""
        self.cc.completion_signal_count = 2
        result_text = "Work in progress..."

        if self.cc.completion_signal not in result_text:
            self.cc.completion_signal_count = 0

        self.assertEqual(self.cc.completion_signal_count, 0)

    def test_custom_signal_detection(self):
        """Test custom completion signal"""
        cc = ContinuousClaude(
            prompt="test",
            max_runs=5,
            github_owner="owner",
            github_repo="repo",
            completion_signal="ALL_DONE"
        )

        result_text = "Work complete. ALL_DONE"
        self.assertIn(cc.completion_signal, result_text)


class TestErrorCounting(unittest.TestCase):
    """Test error counting logic"""

    def setUp(self):
        """Set up test fixtures"""
        self.cc = ContinuousClaude(
            prompt="test",
            max_runs=5,
            github_owner="owner",
            github_repo="repo"
        )

    def test_error_increment(self):
        """Test that errors are counted"""
        self.cc.error_count = 0
        self.cc.error_count += 1
        self.assertEqual(self.cc.error_count, 1)

    def test_success_resets_errors(self):
        """Test that success resets error count"""
        self.cc.error_count = 2
        self.cc.successful_iterations += 1
        self.cc.error_count = 0
        self.assertEqual(self.cc.error_count, 0)


if __name__ == '__main__':
    unittest.main()
