#!/bin/bash

ADDITIONAL_FLAGS="--dangerously-skip-permissions --output-format json"
MAX_RUNS=""
PROMPT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--prompt)
            PROMPT="$2"
            shift 2
            ;;
        -m|--max-runs)
            MAX_RUNS="$2"
            shift 2
            ;;
        *)
            # Ignore unknown flags
            shift
            ;;
    esac
done

if [ -z "$PROMPT" ]; then
    echo "❌ Error: Prompt is required. Use -p to provide a prompt." >&2
    echo "Usage: $0 -p \"your prompt\" -m max_runs" >&2
    exit 1
fi

if [ -z "$MAX_RUNS" ]; then
    echo "❌ Error: MAX_RUNS is required. Use -m to provide max runs (0 for infinite)." >&2
    echo "Usage: $0 -p \"your prompt\" -m max_runs" >&2
    exit 1
fi

if ! [[ "$MAX_RUNS" =~ ^[0-9]+$ ]]; then
    echo "❌ Error: MAX_RUNS must be a non-negative integer (0 for infinite)" >&2
    exit 1
fi

if ! command -v claude &> /dev/null; then
    echo "❌ Error: Claude Code is not installed: https://claude.ai/code" >&2
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo "⚠️ jq is required for JSON parsing but is not installed. Asking Claude Code to install it..." >&2
    claude -p "Please install jq for JSON parsing" --allowedTools "Bash,Read"
    if ! command -v jq &> /dev/null; then
        echo "❌ Error: jq is still not installed after Claude Code attempt." >&2
        exit 1
    fi
fi

ERROR_LOG=$(mktemp)
trap "rm -f $ERROR_LOG" EXIT

continuous_claude_commit() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        return 0
    fi

    if git diff --quiet && git diff --cached --quiet; then
        echo "🫙 $iteration_display No changes detected" >&2
        return 0
    fi

    echo "💬 $iteration_display Committing changes..." >&2
    
    commit_prompt="Please review the dirty files in the git repository, write a commit message with: (1) a short one-line summary, (2) two newlines, (3) then a detailed explanation. Do not include any footers or metadata like 'Generated with Claude Code' or 'Co-Authored-By'. Feel free to look at the last few commits to get a sense of the commit message style. Track all files and commit the changes using 'git commit -am \"your message\"' (don't push, just commit, no need to ask for confirmation)."
    
    if claude -p "$commit_prompt" --allowedTools "Bash(git)" --dangerously-skip-permissions >/dev/null 2>&1; then
        if git diff --quiet && git diff --cached --quiet; then
            echo "📦 $iteration_display Changes committed" >&2
        else
            echo "⚠️  $iteration_display Commit command ran but changes still present" >&2
        fi
    else
        echo "⚠️  $iteration_display Failed to commit changes" >&2
    fi
}

error_count=0
extra_iterations=0
successful_iterations=0
i=1

while [ $MAX_RUNS -eq 0 ] || [ $successful_iterations -lt $MAX_RUNS ]; do
    if [ $MAX_RUNS -eq 0 ]; then
        iteration_display="($i)"
    else
        total_iterations=$((MAX_RUNS + extra_iterations))
        iteration_display="($i/$total_iterations)"
    fi

    echo "🔄 $iteration_display Starting iteration..." >&2

    iteration_failed=false

    if ! result=$(claude -p "$PROMPT" $ADDITIONAL_FLAGS 2>$ERROR_LOG); then
        error_count=$((error_count + 1))
        extra_iterations=$((extra_iterations + 1))
        echo "❌ $iteration_display Error occurred ($error_count consecutive errors):" >&2
        cat "$ERROR_LOG" >&2
        
        if [ $error_count -ge 3 ]; then
            echo "❌ Fatal: 3 consecutive errors occurred. Exiting." >&2
            exit 1
        fi
        
        iteration_failed=true
    fi

    if [ "$iteration_failed" = "false" ] && [ -s "$ERROR_LOG" ]; then
        echo "⚠️  $iteration_display Warnings or errors in stderr:" >&2
        cat "$ERROR_LOG" >&2
    fi

    if [ "$iteration_failed" = "false" ] && ! echo "$result" | jq -e . >/dev/null 2>&1; then
        error_count=$((error_count + 1))
        extra_iterations=$((extra_iterations + 1))
        echo "❌ $iteration_display Error: Invalid JSON response ($error_count consecutive errors):" >&2
        echo "$result" >&2
        
        if [ $error_count -ge 3 ]; then
            echo "❌ Fatal: 3 consecutive errors occurred. Exiting." >&2
            exit 1
        fi
        
        iteration_failed=true
    fi

    if [ "$iteration_failed" = "false" ]; then
        is_error=$(echo "$result" | jq -r '.is_error // false')
        if [ "$is_error" = "true" ]; then
            error_count=$((error_count + 1))
            extra_iterations=$((extra_iterations + 1))
            echo "❌ $iteration_display Error in Claude Code response ($error_count consecutive errors):" >&2
            echo "$result" | jq -r '.result // .' >&2
            
            if [ $error_count -ge 3 ]; then
                echo "❌ Fatal: 3 consecutive errors occurred. Exiting." >&2
                exit 1
            fi
            
            iteration_failed=true
        fi
    fi

    if [ "$iteration_failed" = "false" ]; then
        error_count=0
        if [ $extra_iterations -gt 0 ]; then
            extra_iterations=$((extra_iterations - 1))
        fi
        
        echo "📝 $iteration_display Output:" >&2
        result_text=$(echo "$result" | jq -r '.result // empty')
        if [ -n "$result_text" ]; then
            echo "$result_text"
        else
            echo "(no output)" >&2
        fi

        cost=$(echo "$result" | jq -r '.total_cost_usd // empty')
        if [ -n "$cost" ]; then
            echo "" >&2
            printf "💰 $iteration_display Cost: \$%.3f\n" "$cost" >&2
        fi

        echo "✅ $iteration_display Work completed" >&2
        continuous_claude_commit
        successful_iterations=$((successful_iterations + 1))
    fi

    if [ $MAX_RUNS -eq 0 ] || [ $successful_iterations -lt $MAX_RUNS ]; then
        sleep 1
    fi

    i=$((i + 1))
done

if [ $MAX_RUNS -ne 0 ]; then
    echo "🎉 Done"
fi
