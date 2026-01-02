# Continuous Claude Refactoring - Next Iteration Notes

## Current Status

The project has been refactored from a Bash script to a Python script. The core functionality has been preserved while removing non-essential features.

## What Was Done

### Completed
- ✅ Converted `continuous_claude.sh` to `continuous_claude.py`
- ✅ Kept core features:
  - Iterative Claude Code execution loop
  - Automatic git branch creation per iteration
  - PR creation and management
  - CI check monitoring with timeout
  - PR merging with configurable strategies (squash/merge/rebase)
  - SHARED_TASK_NOTES.md context persistence
  - Completion signal detection for early stopping
  - GitHub repo auto-detection from git remote
- ✅ Removed non-essential features:
  - Update checking and installation
  - Worktree management
  - Dry-run mode
  - Cost limits (--max-cost)
  - Duration limits (--max-duration)
  - Extensive documentation and examples
- ✅ Simplified interface:
  - Only essential flags: -p (prompt), -m (max-runs), --owner, --repo, --merge-strategy
  - Removed complex duration parsing logic
  - Removed auto-update prompts
- ✅ Streamlined README to basic usage

## Known Limitations of Current Python Implementation

1. **Error Handling**: Less robust than Bash version - needs more edge case handling
2. **PR Check Logic**: Simplified check waiting - may miss some edge cases with complex CI configurations
3. **No Max Cost/Duration**: These features were removed to simplify, but might be useful to add back
4. **Branch Conflict Handling**: Doesn't handle merge conflicts during PR updates
5. **JSON Parsing**: Assumes Claude Code always returns valid JSON - could be more defensive

## Suggested Improvements for Next Iteration

### High Priority
1. **Add max-cost and max-duration support** - These are useful limits that should be in core
2. **Improve PR check waiting** - More robust status checking, handle edge cases better
3. **Better error recovery** - More graceful handling of git/gh command failures
4. **Add tests** - Create test suite for core functionality

### Medium Priority
5. **Configuration file support** - Allow loading defaults from `.continuous-claude.yml`
6. **Progress indicators** - Show progress while waiting for PR checks
7. **Better logging** - Structured logging with optional verbosity levels
8. **Merge conflict handling** - Detect and handle merge conflicts gracefully

### Low Priority
9. **Re-add worktree support** - Useful for parallel execution (was removed for simplicity)
10. **Add dry-run mode back** - Useful for testing (was removed for simplicity)
11. **Package as Python module** - Allow `pip install continuous-claude`

## Files Modified

- ✅ `continuous_claude.py` - New Python implementation (core functionality)
- ✅ `README.md` - Simplified to essential documentation only
- ⚠️  `continuous_claude.sh` - Original Bash script (kept for reference, consider removing)

## Files Not Modified (Can Be Removed)

- `install.sh` - Installation script (no longer needed with Python version)
- `CHANGELOG.md` - Historical changelog (can be removed or simplified)
- `.github/` - GitHub Actions/Issue templates (likely not needed for refactored version)
- `tests/` - Test suite (need to add Python tests)

## Testing Checklist

Before considering this refactor complete:

- [ ] Test basic iteration with actual Claude Code
- [ ] Test PR creation and merging
- [ ] Test completion signal detection
- [ ] Test error handling (git failures, gh failures)
- [ ] Test with different merge strategies
- [ ] Test SHARED_TASK_NOTES.md persistence
- [ ] Add Python unit tests
- [ ] Test on different OS (macOS, Linux)

## Decision Points for Next Developer

1. **Should we keep the Bash script?** It's currently still in the repo. Could:
   - Delete it entirely (clean break)
   - Keep as reference/migration guide
   - Move to `legacy/` folder

2. **Should we re-add some removed features?**
   - Max cost/duration limits are actually quite useful
   - Dry-run mode helps with testing
   - Worktree support enables parallel execution

3. **Package structure?** Should this be:
   - Single script (current approach - simplest)
   - Python package with modules (more maintainable for larger features)
   - Hybrid: single script but with optional package install

4. **Breaking changes?** The Python version has a different CLI than the Bash version:
   - Missing flags: --max-cost, --max-duration, --worktree, --dry-run, --disable-commits, etc.
   - Is this acceptable or should we maintain parity?
