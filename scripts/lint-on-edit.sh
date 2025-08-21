#!/bin/bash

# Claude Code Hook Script for linting after Write/Edit operations
# This script runs mypy, ruff format, and bandit on modified Python files

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the project directory (parent of scripts directory)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# Read the JSON input from stdin
INPUT=$(cat)

# Extract the tool name and file path from the JSON input
# This is a simplified extraction - in production you'd use jq
TOOL_NAME=$(echo "$INPUT" | grep -o '"tool":"[^"]*"' | cut -d'"' -f4)
FILE_PATH=$(echo "$INPUT" | grep -o '"file_path":"[^"]*"' | cut -d'"' -f4)

# If no file path found, try to extract from other possible fields
if [ -z "$FILE_PATH" ]; then
    FILE_PATH=$(echo "$INPUT" | grep -o '"path":"[^"]*"' | cut -d'"' -f4)
fi

# Function to run checks on a Python file
check_python_file() {
    local file="$1"
    local has_errors=0
    local output=""

    echo -e "${YELLOW}Checking: $file${NC}" >&2

    # Run ruff format check (non-destructive)
    if ! uv run ruff format --check "$file" >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠ File needs formatting${NC}" >&2
        # Auto-format the file
        uv run ruff format "$file" >/dev/null 2>&1
        output="${output}✓ Auto-formatted with ruff\n"
    fi

    # Run ruff linting with auto-fix
    if ! uv run ruff check --fix "$file" >/dev/null 2>&1; then
        # Check if there are still errors after auto-fix
        if ! uv run ruff check "$file" >/dev/null 2>&1; then
            echo -e "${RED}✗ Linting errors remain${NC}" >&2
            ruff_errors=$(uv run ruff check "$file" 2>&1)
            output="${output}Ruff errors:\n${ruff_errors}\n"
            has_errors=1
        else
            output="${output}✓ Fixed linting issues\n"
        fi
    fi

    # Run mypy type checking
    if ! uv run mypy "$file" --ignore-missing-imports >/dev/null 2>&1; then
        echo -e "${RED}✗ Type errors found${NC}" >&2
        mypy_errors=$(uv run mypy "$file" --ignore-missing-imports 2>&1)
        output="${output}MyPy errors:\n${mypy_errors}\n"
        has_errors=1
    fi

    # Run bandit security check (only on source files, not tests)
    if [[ ! "$file" =~ tests/ ]]; then
        if ! uv run bandit -ll "$file" >/dev/null 2>&1; then
            echo -e "${YELLOW}⚠ Security issues found${NC}" >&2
            bandit_output=$(uv run bandit -ll "$file" 2>&1)
            output="${output}Bandit warnings:\n${bandit_output}\n"
            # Don't fail on bandit warnings, just notify
        fi
    fi

    # Run vulture dead code detection
    if ! uv run vulture "$file" --config .vulture.ini --min-confidence 90 >/dev/null 2>&1; then
        # Only warn about dead code, don't fail the build
        vulture_output=$(uv run vulture "$file" --config .vulture.ini --min-confidence 90 2>&1)
        if [ -n "$vulture_output" ]; then
            echo -e "${YELLOW}⚠ Possible dead code found${NC}" >&2
            output="${output}Vulture warnings:\n${vulture_output}\n"
        fi
    fi

    if [ $has_errors -eq 0 ]; then
        echo -e "${GREEN}✓ All checks passed${NC}" >&2
    fi

    # Return feedback to Claude
    if [ -n "$output" ]; then
        echo "$output"
    fi

    return $has_errors
}

# Main logic
if [ -n "$FILE_PATH" ] && [[ "$FILE_PATH" == *.py ]]; then
    # Check if the file exists
    if [ -f "$FILE_PATH" ]; then
        if check_python_file "$FILE_PATH"; then
            exit 0  # All checks passed
        else
            # Return exit code 2 to provide feedback to Claude
            exit 2
        fi
    fi
fi

# For non-Python files or when file path not found, just exit successfully
exit 0
