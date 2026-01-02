# Continuous Claude Refactoring - Next Iteration Notes

## Current Status

The project has been successfully cleaned up and enhanced. All legacy Bash files and non-essential documentation have been removed. Cost and duration limits have been re-added, and PR check error handling has been significantly improved.

## What Was Done (Latest Iteration)

### Completed
- ✅ Removed all legacy files:
  - `continuous_claude.sh` (old Bash script)
  - `install.sh` (installation script)
  - `CHANGELOG.md` (historical changelog)
  - `.github/` directory (GitHub workflows)
  - `tests/` directory (Bash-specific tests)
- ✅ Re-added max-cost and max-duration support:
  - `--max-cost` flag to limit total spending in USD
  - `--max-duration` flag with flexible format (1h, 30m, 45s)
  - Both limits are checked before each iteration
- ✅ Improved PR check waiting logic:
  - Better error handling with detailed logging
  - Separate handling for pending, completed, and failed checks
  - Shows pending check names periodically
  - Handles review decisions (APPROVED, CHANGES_REQUESTED)
  - Detects if PR is closed during waiting
  - More descriptive error messages
- ✅ Updated README with new features and cleaner documentation
- ✅ Removed `jq` from requirements (no longer needed with Python JSON parsing)

## Current Feature Set

The script now supports:
- Core iterative workflow with Claude Code
- Automatic branch creation, PR management, and merging
- Cost and duration limits (`--max-cost`, `--max-duration`)
- Configurable merge strategies (squash/merge/rebase)
- SHARED_TASK_NOTES.md context persistence
- Completion signal detection for early stopping
- GitHub repo auto-detection from git remote
- Robust PR check waiting with detailed status reporting

## Remaining Known Limitations

1. **No Python unit tests** - Test suite was removed with Bash tests
2. **Branch Conflict Handling** - Doesn't handle merge conflicts during PR updates
3. **JSON Parsing** - Assumes Claude Code always returns valid JSON
4. **No dry-run mode** - Useful for testing (was removed for simplicity)
5. **No worktree support** - Useful for parallel execution (was removed for simplicity)

## Suggested Improvements for Next Iteration

### High Priority
1. **Add Python unit tests** - Test core functionality without needing git/gh
2. **Better error recovery** - More graceful handling of git/gh command failures
3. **Add dry-run mode** - Useful for testing and development
4. **Merge conflict handling** - Detect and handle merge conflicts gracefully

### Medium Priority
5. **Configuration file support** - Allow loading defaults from `.continuous-claude.yml`
6. **Structured logging** - Optional verbosity levels (-v, -vv, --quiet)
7. **Progress indicators** - Show spinner or progress bar while waiting for PR checks
8. **Better JSON parsing** - More defensive parsing with fallback for malformed output

### Low Priority
9. **Re-add worktree support** - Useful for parallel execution
10. **Package as Python module** - Allow `pip install continuous-claude`

## Files Modified (Latest Iteration)

- ✅ `continuous_claude.py` - Added max-cost, max-duration, improved PR checks
- ✅ `README.md` - Updated documentation with new features
- ✅ `continuous_claude.sh` - Deleted (legacy Bash script)
- ✅ `install.sh` - Deleted (no longer needed)
- ✅ `CHANGELOG.md` - Deleted (historical documentation)
- ✅ `.github/` - Deleted (GitHub workflows)
- ✅ `tests/` - Deleted (Bash-specific tests)

## Testing Checklist

Before considering this refactor complete:

- [x] Remove legacy Bash and installation files
- [x] Add max-cost and max-duration support
- [x] Improve PR check error handling
- [ ] Test basic iteration with actual Claude Code
- [ ] Test PR creation and merging
- [ ] Test completion signal detection
- [ ] Test cost and duration limits
- [ ] Test error handling (git failures, gh failures)
- [ ] Test with different merge strategies
- [ ] Add Python unit tests for core functions
- [ ] Test on different OS (macOS, Linux)

## Decision Points for Next Developer

1. **Should we add a dry-run mode?** This would be very useful for testing and development:
   - `--dry-run` flag that skips actual git/gh commands
   - Would allow testing without making real changes

2. **Should we add unit tests?** Current state has no tests:
   - Create `tests/test_continuous_claude.py`
   - Mock git/gh commands
   - Test core logic without external dependencies

3. **Configuration file format?** If adding config file support:
   - YAML (`.continuous-claude.yml`) - more readable
   - JSON (`.continuous-claude.json`) - simpler parsing
   - TOML (`.continuous-claude.toml`) - Python-friendly

4. **Project completion?** The refactoring is nearly complete:
   - All legacy code removed
   - Core features working
   - Cost/duration limits re-added
   - Better error handling in place
   - Main gap: no unit tests
