#!/usr/bin/env bash
# AiTermy V3 Installer
# Installs AiTermy to ~/.aitermy with shell integration for zsh and bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Configuration
AITERMY_HOME="$HOME/.aitermy"
AITERMY_VERSION="3.0.0"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Logging functions
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Print banner
print_banner() {
    echo -e "${CYAN}${BOLD}"
    echo "    _    _ _____                          "
    echo "   / \\  (_)_   _|__ _ __ _ __ ___  _   _  "
    echo "  / _ \\ | | | |/ _ \\ '__| '_ \` _ \\| | | | "
    echo " / ___ \\| | | |  __/ |  | | | | | | |_| | "
    echo "/_/   \\_\\_| |_|\\___|_|  |_| |_| |_|\\__, | "
    echo "                                   |___/  "
    echo -e "${NC}"
    echo -e "${BOLD}AiTermy V${AITERMY_VERSION} Installer${NC}"
    echo ""
}

# Detect shell type
detect_shell() {
    local user_shell
    user_shell=$(basename "$SHELL")

    case "$user_shell" in
        zsh)
            SHELL_TYPE="zsh"
            SHELL_RC="$HOME/.zshrc"
            ;;
        bash)
            SHELL_TYPE="bash"
            # On macOS, use .bash_profile, on Linux use .bashrc
            if [[ "$(uname)" == "Darwin" ]]; then
                SHELL_RC="$HOME/.bash_profile"
            else
                SHELL_RC="$HOME/.bashrc"
            fi
            ;;
        *)
            warn "Unsupported shell: $user_shell"
            warn "Defaulting to bash integration"
            SHELL_TYPE="bash"
            SHELL_RC="$HOME/.bashrc"
            ;;
    esac

    info "Detected shell: $SHELL_TYPE (rc file: $SHELL_RC)"
}

# Check for Python 3
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        info "Found Python $PYTHON_VERSION"
    elif command -v python &> /dev/null; then
        # Check if 'python' is Python 3
        if python -c 'import sys; exit(0 if sys.version_info.major >= 3 else 1)' 2>/dev/null; then
            PYTHON_CMD="python"
            PYTHON_VERSION=$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
            info "Found Python $PYTHON_VERSION"
        else
            error "Python 3 is required but not found. Please install Python 3.8+"
        fi
    else
        error "Python is not installed. Please install Python 3.8+"
    fi

    # Check minimum version
    if ! $PYTHON_CMD -c 'import sys; exit(0 if sys.version_info >= (3, 8) else 1)' 2>/dev/null; then
        error "Python 3.8+ is required. Found: $PYTHON_VERSION"
    fi
}

# Check for existing V2 installation
check_v2_migration() {
    local v2_detected=false

    # Check for old .aitermy_config.zsh
    if [[ -f "$SCRIPT_DIR/.aitermy_config.zsh" ]]; then
        v2_detected=true
    fi

    # Check for old .env in script directory
    if [[ -f "$SCRIPT_DIR/.env" ]]; then
        v2_detected=true
    fi

    if [[ "$v2_detected" == "true" ]]; then
        warn "Detected existing V2 installation"
        echo ""
        echo -e "${YELLOW}V2 Configuration Found${NC}"
        echo "This installer will:"
        echo "  1. Migrate your API key to the new config.toml format"
        echo "  2. Remove old shell integration from your rc file"
        echo "  3. Add new V3 shell integration"
        echo ""
        read -p "Continue with migration? [Y/n]: " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]?$ ]]; then
            info "Installation cancelled"
            exit 0
        fi
        MIGRATE_V2=true
    else
        MIGRATE_V2=false
    fi
}

# Create directory structure
create_directories() {
    info "Creating directory structure..."

    mkdir -p "$AITERMY_HOME/bin"
    mkdir -p "$AITERMY_HOME/shell"
    mkdir -p "$AITERMY_HOME/data/conversations"
    mkdir -p "$AITERMY_HOME/data/sessions"
    mkdir -p "$AITERMY_HOME/logs"

    success "Created $AITERMY_HOME"
}

# Copy files
copy_files() {
    info "Copying files..."

    # Copy main script
    cp "$SCRIPT_DIR/aitermy.py" "$AITERMY_HOME/bin/aitermy.py"
    chmod +x "$AITERMY_HOME/bin/aitermy.py"

    # Copy shell integration files
    cp "$SCRIPT_DIR/shell/ai.zsh" "$AITERMY_HOME/shell/ai.zsh"
    cp "$SCRIPT_DIR/shell/ai.bash" "$AITERMY_HOME/shell/ai.bash"

    # Copy requirements
    cp "$SCRIPT_DIR/requirements.txt" "$AITERMY_HOME/requirements.txt"

    success "Files copied"
}

# Prompt for configuration
configure_api() {
    echo ""
    echo -e "${CYAN}${BOLD}Configuration${NC}"
    echo ""

    # Check if config already exists
    if [[ -f "$AITERMY_HOME/config.toml" ]]; then
        info "Existing config.toml found"
        read -p "Keep existing configuration? [Y/n]: " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]?$ ]]; then
            return
        fi
    fi

    # Check for V2 migration
    local existing_key=""
    local existing_model=""
    local existing_command=""

    if [[ "$MIGRATE_V2" == "true" && -f "$SCRIPT_DIR/.env" ]]; then
        info "Reading configuration from V2 .env file..."
        existing_key=$(grep -E "^OPENROUTER_API_KEY=" "$SCRIPT_DIR/.env" 2>/dev/null | cut -d'=' -f2 | tr -d '"' || echo "")
        existing_model=$(grep -E "^OPENROUTER_MODEL=" "$SCRIPT_DIR/.env" 2>/dev/null | cut -d'=' -f2 | tr -d '"' || echo "")
        existing_command=$(grep -E "^COMMAND_NAME=" "$SCRIPT_DIR/.env" 2>/dev/null | cut -d'=' -f2 | tr -d '"' || echo "")
    fi

    # API Key
    if [[ -n "$existing_key" && "$existing_key" != "sk-or-your-api-key-here" ]]; then
        echo -e "Found existing API key: ${CYAN}${existing_key:0:10}...${NC}"
        read -p "Use this key? [Y/n]: " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]?$ ]]; then
            API_KEY="$existing_key"
        else
            read -p "Enter OpenRouter API key: " API_KEY
        fi
    else
        echo -e "Get your API key at: ${CYAN}https://openrouter.ai/keys${NC}"
        read -p "Enter OpenRouter API key: " API_KEY
    fi

    # Validate API key format
    if [[ ! "$API_KEY" =~ ^sk-or- ]]; then
        warn "API key should start with 'sk-or-'"
    fi

    # Model
    local default_model="${existing_model:-x-ai/grok-4.1-fast}"
    echo ""
    echo -e "Default model: ${CYAN}$default_model${NC}"
    read -p "Enter model name (or press Enter for default): " MODEL_INPUT
    MODEL="${MODEL_INPUT:-$default_model}"

    # Command name
    local default_command="${existing_command:-ai}"
    echo ""
    echo -e "Command name (how you'll invoke AiTermy): ${CYAN}$default_command${NC}"
    read -p "Enter command name (or press Enter for default): " COMMAND_INPUT
    COMMAND_NAME="${COMMAND_INPUT:-$default_command}"

    # Write config.toml
    info "Writing configuration..."
    cat > "$AITERMY_HOME/config.toml" << EOF
# AiTermy V3 Configuration
# Generated by installer on $(date)

[api]
key = "$API_KEY"
model = "$MODEL"

[context]
include_history = true
history_lines = 20
include_env = true
max_context_tokens = 2000

[ui]
command = "$COMMAND_NAME"

[logging]
enabled = false
file = "~/.aitermy/logs/aitermy.log"

[output_capture]
enabled = true
max_size = 10240
max_system_chars = 4000

[conversation]
max_turns = 10
storage_dir = "~/.aitermy/data/conversations"
EOF

    chmod 600 "$AITERMY_HOME/config.toml"
    success "Configuration saved"
    info "✓ Output capture enabled by default (AI will see command output)"
    info "  To disable: export AITERMY_CAPTURE_OUTPUT=0"
}

# Create virtual environment
setup_venv() {
    info "Setting up Python virtual environment..."

    # Create venv
    $PYTHON_CMD -m venv "$AITERMY_HOME/venv"

    # Install dependencies
    "$AITERMY_HOME/venv/bin/pip" install --upgrade pip -q
    "$AITERMY_HOME/venv/bin/pip" install -r "$AITERMY_HOME/requirements.txt" -q

    success "Virtual environment ready"
}

# Setup shell integration
setup_shell_integration() {
    info "Setting up shell integration..."

    # Read command name from config
    COMMAND_NAME=$(grep -E "^command = " "$AITERMY_HOME/config.toml" 2>/dev/null | cut -d'"' -f2 || echo "ai")

    # Create customized shell integration file
    local shell_file="$AITERMY_HOME/shell/ai.$SHELL_TYPE"
    sed -i.bak "s/COMMAND_PLACEHOLDER/${COMMAND_NAME}/g" "$shell_file" 2>/dev/null || \
        sed -i '' "s/COMMAND_PLACEHOLDER/${COMMAND_NAME}/g" "$shell_file"
    rm -f "${shell_file}.bak" 2>/dev/null

    # Also update the other shell file (in case user switches)
    local other_shell_type
    if [[ "$SHELL_TYPE" == "zsh" ]]; then
        other_shell_type="bash"
    else
        other_shell_type="zsh"
    fi
    local other_shell_file="$AITERMY_HOME/shell/ai.$other_shell_type"
    sed -i.bak "s/COMMAND_PLACEHOLDER/${COMMAND_NAME}/g" "$other_shell_file" 2>/dev/null || \
        sed -i '' "s/COMMAND_PLACEHOLDER/${COMMAND_NAME}/g" "$other_shell_file"
    rm -f "${other_shell_file}.bak" 2>/dev/null

    # Remove old V2 integration if present
    if [[ -f "$SHELL_RC" ]]; then
        # Remove old source lines
        grep -v ".aitermy_config.zsh" "$SHELL_RC" > "${SHELL_RC}.tmp" 2>/dev/null || true
        grep -v "# AiTermy V2" "${SHELL_RC}.tmp" > "${SHELL_RC}.tmp2" 2>/dev/null || true
        mv "${SHELL_RC}.tmp2" "$SHELL_RC" 2>/dev/null || true
        rm -f "${SHELL_RC}.tmp" 2>/dev/null
    fi

    # Add new V3 integration
    local source_line="# AiTermy V3"
    local source_cmd="source \"$AITERMY_HOME/shell/ai.$SHELL_TYPE\""

    # Check if already added
    if ! grep -q "AiTermy V3" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "$source_line" >> "$SHELL_RC"
        echo "$source_cmd" >> "$SHELL_RC"
        success "Added shell integration to $SHELL_RC"
    else
        info "Shell integration already present in $SHELL_RC"
    fi
}

# Clean up V2 files
cleanup_v2() {
    if [[ "$MIGRATE_V2" == "true" ]]; then
        info "Cleaning up V2 installation..."

        # Don't delete .env and .aitermy_config.zsh - just leave them
        # User might want to keep them as backup

        warn "Old V2 files kept in $SCRIPT_DIR as backup"
        warn "You can safely delete them after confirming V3 works"
    fi
}

# Print success message
print_success() {
    echo ""
    echo -e "${GREEN}${BOLD}Installation Complete!${NC}"
    echo ""
    echo -e "To start using AiTermy, run:"
    echo -e "  ${CYAN}source $SHELL_RC${NC}"
    echo ""
    echo -e "Or open a new terminal, then:"
    echo -e "  ${CYAN}${COMMAND_NAME} \"Hello, world!\"${NC}   # Quick question"
    echo -e "  ${CYAN}${COMMAND_NAME}${NC}                    # Interactive mode"
    echo ""
    echo -e "Configuration: ${CYAN}$AITERMY_HOME/config.toml${NC}"
    echo -e "Logs: ${CYAN}$AITERMY_HOME/logs/aitermy.log${NC}"
    echo ""
    echo -e "${YELLOW}Tip:${NC} Run '${COMMAND_NAME} --help' for usage information"
    echo ""
}

# Main installation flow
main() {
    print_banner
    detect_shell
    check_python
    check_v2_migration
    create_directories
    copy_files
    configure_api
    setup_venv
    setup_shell_integration
    cleanup_v2
    print_success
}

# Run main
main "$@"
