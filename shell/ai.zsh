# AiTermy V3 - Zsh Shell Integration
# This file is sourced by ~/.zshrc to provide the 'ai' command
# It captures real-time shell context and passes it to the Python script

# Configuration
AITERMY_HOME="${AITERMY_HOME:-$HOME/.aitermy}"
AITERMY_PYTHON="${AITERMY_HOME}/venv/bin/python"
AITERMY_SCRIPT="${AITERMY_HOME}/bin/aitermy.py"

# Session data directory for terminal output capture
AITERMY_SESSION_DIR="${AITERMY_HOME}/data/sessions"
mkdir -p "$AITERMY_SESSION_DIR" 2>/dev/null

# Unique terminal session ID (based on TTY)
AITERMY_TTY_ID=$(tty | tr '/' '_' 2>/dev/null || echo "unknown")

# Track last command and its exit status
typeset -g AITERMY_LAST_CMD=""
typeset -g AITERMY_LAST_STATUS="0"

# preexec hook - runs before each command executes
_aitermy_preexec() {
    AITERMY_LAST_CMD="$1"
    # Store command being run
    echo "$1" > "${AITERMY_SESSION_DIR}/current_command_${AITERMY_TTY_ID}" 2>/dev/null
}

# precmd hook - runs before each prompt
_aitermy_precmd() {
    AITERMY_LAST_STATUS="$?"
    # Move current to last
    if [[ -f "${AITERMY_SESSION_DIR}/current_command_${AITERMY_TTY_ID}" ]]; then
        mv "${AITERMY_SESSION_DIR}/current_command_${AITERMY_TTY_ID}" \
           "${AITERMY_SESSION_DIR}/last_command_${AITERMY_TTY_ID}" 2>/dev/null
    fi
}

# Register hooks if not already registered
if [[ -z "${_aitermy_hooks_registered}" ]]; then
    autoload -Uz add-zsh-hook
    add-zsh-hook preexec _aitermy_preexec
    add-zsh-hook precmd _aitermy_precmd
    typeset -g _aitermy_hooks_registered=1
fi

# Main ai function - captures context and invokes Python
# COMMAND_PLACEHOLDER will be replaced by install.sh with actual command name
COMMAND_PLACEHOLDER() {
    # Capture current shell state
    local current_pwd="$(pwd)"
    local old_pwd="${OLDPWD:-}"

    # Get recent history (last 20 commands)
    # fc -ln gets history without line numbers, -20 gets last 20
    local shell_history
    shell_history="$(fc -ln -20 2>/dev/null | tail -20)"

    # Get last command from session file (to avoid self-capture)
    # The precmd hook moves current_command to last_command BEFORE this runs
    local last_cmd=""
    local session_file="${AITERMY_SESSION_DIR}/last_command_${AITERMY_TTY_ID}"
    if [[ -f "$session_file" ]]; then
        last_cmd="$(cat "$session_file" 2>/dev/null || echo '')"
    fi

    # Get last command status (still from env var)
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
    AITERMY_SHELL="zsh" \
    AITERMY_SHELL_VERSION="${ZSH_VERSION:-unknown}" \
    AITERMY_HISTORY="$shell_history" \
    AITERMY_LAST_CMD="$last_cmd" \
    AITERMY_LAST_STATUS="$last_status" \
    AITERMY_TERM_COLS="$term_cols" \
    AITERMY_TERM_LINES="$term_lines" \
    AITERMY_TTY="$AITERMY_TTY_ID" \
    AITERMY_USER="${USER:-$(whoami)}" \
    AITERMY_HOST="${HOST:-$(hostname)}" \
    "$AITERMY_PYTHON" "$AITERMY_SCRIPT" "$@"
}
