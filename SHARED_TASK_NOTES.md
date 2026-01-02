# Continuous Claude Refactoring - Next Iteration Notes

## Current Status

The project refactoring is progressing well. Core functionality has been implemented with robust error handling. Recently added dry-run mode and improved error recovery mechanisms.

## What Was Done (Latest Iteration)

### Completed (2026-01-02)
- ✅ **Added dry-run mode** (`--dry-run` flag):
  - Simulates execution without making real changes
  - Shows commands that would be executed
  - Useful for testing and development
- ✅ **Improved error recovery**:
  - Added 30s timeout to all git/gh commands to prevent hanging
  - Better error messages with raw output preview for debugging
  - Handles subprocess timeout exceptions gracefully
- ✅ **Enhanced JSON parsing**:
  - Defensive parsing with explicit error handling for empty lists
  - Safe cost value extraction with type checking
  - Separate error handlers for JSONDecodeError vs structure errors
  - Shows raw output on parse failures for debugging
- ✅ **Updated documentation** with dry-run feature

## Current Feature Set

The script now supports:
- Core iterative workflow with Claude Code
- Automatic branch creation, PR management, and merging
- Cost and duration limits (`--max-cost`, `--max-duration`)
- **Dry-run mode for safe testing** (`--dry-run`)
- Configurable merge strategies (squash/merge/rebase)
- SHARED_TASK_NOTES.md context persistence
- Completion signal detection for early stopping
- GitHub repo auto-detection from git remote
- Robust PR check waiting with detailed status reporting
- **Timeout protection** on all external commands
- **Defensive JSON parsing** with detailed error messages

## Remaining Known Limitations

1. **No Python unit tests** - Test suite was removed with Bash tests (HIGH PRIORITY)
2. **Branch Conflict Handling** - Doesn't handle merge conflicts during PR updates
3. **No configuration file support** - All options must be passed via CLI
4. **No worktree support** - Useful for parallel execution
5. **Limited logging options** - No verbosity levels or quiet mode

## Suggested Improvements for Next Iteration

### High Priority
1. **Add Python unit tests** - Test core functionality without needing git/gh
2. **Configuration file support** - Allow loading defaults from `.continuous-claude.yml`
3. **Merge conflict handling** - Detect and handle merge conflicts gracefully
4. **Structured logging** - Optional verbosity levels (-v, -vv, --quiet)

### Medium Priority
5. **Progress indicators** - Show spinner or progress bar while waiting for PR checks
6. **Continue on non-fatal errors** - More resilient error recovery
7. **Better Claude Code integration** - Handle edge cases in Claude output

### Low Priority
8. **Re-add worktree support** - Useful for parallel execution
9. **Package as Python module** - Allow `pip install continuous-claude`
10. **Interactive mode** - Allow approval before each iteration

## Testing Checklist

Before considering this refactor complete:

- [x] Remove legacy Bash and installation files
- [x] Add max-cost and max-duration support
- [x] Improve PR check error handling
- [x] Add dry-run mode
- [x] Improve error recovery with timeouts
- [x] Add defensive JSON parsing
- [ ] Test basic iteration with actual Claude Code
- [ ] Test PR creation and merging
- [ ] Test completion signal detection
- [ ] Test cost and duration limits
- [ ] Test dry-run mode doesn't make changes
- [ ] Test error handling (git failures, gh failures)
- [ ] Test with different merge strategies
- [ ] Add Python unit tests for core functions
- [ ] Test on different OS (macOS, Linux)

## Decision Points for Next Developer

1. **Should we add unit tests?** This is the biggest remaining gap:
   - Create `tests/test_continuous_claude.py`
   - Mock git/gh/Claude commands
   - Test core logic without external dependencies
   - Would significantly improve confidence in changes

2. **Configuration file format?** Would simplify usage for repeated runs:
   - YAML (`.continuous-claude.yml`) - more readable
   - JSON (`.continuous-claude.json`) - simpler parsing
   - TOML (`.continuous-claude.toml`) - Python-friendly

3. **Merge conflict handling?** Current limitation:
   - Auto-abort on merge conflicts
   - Could add conflict detection and user notification
   - Or implement auto-resolve strategies

4. **Project completion?** The refactoring is very close to complete:
   - All legacy code removed ✅
   - Core features working ✅
   - Cost/duration limits ✅
   - Dry-run mode ✅
   - Better error handling ✅
   - Main remaining gap: **no unit tests**

## Implementation Notes for Next Developer

- All external commands now have 30s timeout
- Dry-run mode simulates all operations but makes no changes
- JSON parsing handles empty lists, missing fields, and invalid types
- Error messages include raw output for debugging
- The codebase is now well-structured for adding unit tests

