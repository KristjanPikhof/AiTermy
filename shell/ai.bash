# AiTermy V3 - Bash Shell Integration
# This file is sourced by ~/.bashrc to provide the 'ai' command
# It captures real-time shell context and passes it to the Python script

# Configuration
AITERMY_HOME="${AITERMY_HOME:-$HOME/.aitermy}"
AITERMY_PYTHON="${AITERMY_HOME}/venv/bin/python"
AITERMY_SCRIPT="${AITERMY_HOME}/bin/aitermy.py"

# Session data directory for terminal output capture
AITERMY_SESSION_DIR="${AITERMY_HOME}/data/sessions"
mkdir -p "$AITERMY_SESSION_DIR" 2>/dev/null

# Unique terminal session ID (based on TTY)
AITERMY_TTY_ID=$(tty 2>/dev/null | tr '/' '_' || echo "unknown")

# Track last command and its exit status
AITERMY_LAST_CMD=""
AITERMY_LAST_STATUS="0"

# DEBUG trap - runs before each command executes (bash equivalent of preexec)
_aitermy_debug_trap() {
    # Skip if we're in the PROMPT_COMMAND
    if [[ -n "${COMP_LINE:-}" ]] || [[ "${BASH_COMMAND}" == "${PROMPT_COMMAND:-}" ]]; then
        return
    fi
    AITERMY_LAST_CMD="${BASH_COMMAND}"
    # Store command being run
    echo "${BASH_COMMAND}" > "${AITERMY_SESSION_DIR}/current_command_${AITERMY_TTY_ID}" 2>/dev/null
}

# PROMPT_COMMAND - runs before each prompt (bash equivalent of precmd)
_aitermy_prompt_command() {
    AITERMY_LAST_STATUS="$?"
    # Move current to last
    if [[ -f "${AITERMY_SESSION_DIR}/current_command_${AITERMY_TTY_ID}" ]]; then
        mv "${AITERMY_SESSION_DIR}/current_command_${AITERMY_TTY_ID}" \
           "${AITERMY_SESSION_DIR}/last_command_${AITERMY_TTY_ID}" 2>/dev/null
    fi
}

# Register hooks if not already registered
if [[ -z "${_aitermy_hooks_registered:-}" ]]; then
    # Add our debug trap
    trap '_aitermy_debug_trap' DEBUG

    # Add to PROMPT_COMMAND (preserve existing)
    if [[ -n "${PROMPT_COMMAND:-}" ]]; then
        PROMPT_COMMAND="_aitermy_prompt_command; ${PROMPT_COMMAND}"
    else
        PROMPT_COMMAND="_aitermy_prompt_command"
    fi

    _aitermy_hooks_registered=1
fi

# Main ai function - captures context and invokes Python
# COMMAND_PLACEHOLDER will be replaced by install.sh with actual command name
COMMAND_PLACEHOLDER() {
    # Capture current shell state
    local current_pwd
    current_pwd="$(pwd)"
    local old_pwd="${OLDPWD:-}"

    # Get recent history (last 20 commands)
    # Using history command and cutting the line numbers
    local shell_history
    shell_history="$(history 20 2>/dev/null | sed 's/^[[:space:]]*[0-9]*[[:space:]]*//')"

    # Get last command and its status
    local last_cmd="${AITERMY_LAST_CMD:-}"
    local last_status="${AITERMY_LAST_STATUS:-0}"

    # Get terminal size for better formatting
    local term_cols="${COLUMNS:-80}"
    local term_lines="${LINES:-24}"

    # Check if Python script exists
    if [[ ! -f "$AITERMY_SCRIPT" ]]; then
        echo "Error: AiTermy not found at $AITERMY_SCRIPT"
        echo "Please run the installer: ~/.aitermy/install.sh"
        return 1
    fi

    # Check if Python venv exists
    if [[ ! -f "$AITERMY_PYTHON" ]]; then
        # Fallback to system python
        AITERMY_PYTHON="python3"
    fi

    # Pass all context via environment variables
    AITERMY_PWD="$current_pwd" \
    AITERMY_OLDPWD="$old_pwd" \
    AITERMY_SHELL="bash" \
    AITERMY_SHELL_VERSION="${BASH_VERSION:-unknown}" \
    AITERMY_HISTORY="$shell_history" \
    AITERMY_LAST_CMD="$last_cmd" \
    AITERMY_LAST_STATUS="$last_status" \
    AITERMY_TERM_COLS="$term_cols" \
    AITERMY_TERM_LINES="$term_lines" \
    AITERMY_TTY="$AITERMY_TTY_ID" \
    AITERMY_USER="${USER:-$(whoami)}" \
    AITERMY_HOST="${HOSTNAME:-$(hostname)}" \
    "$AITERMY_PYTHON" "$AITERMY_SCRIPT" "$@"
}
