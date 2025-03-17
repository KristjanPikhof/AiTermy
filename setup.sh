#!/bin/bash

# Check if we're continuing after a shell reload
if [ "$1" = "--continue" ]; then
  echo -e "\033[0;32mContinuing setup after shell reload...\033[0m"
  # Remove the temporary continuation file if it exists
  if [ -f /tmp/aitermy_continue ]; then
    rm /tmp/aitermy_continue
  fi
fi

# --- Helper Functions ---

# Function to ask for confirmation
confirm() {
  read -r -p "${1} [y/N]: " response
  case "$response" in
    [yY][eE][sS]|[yY])
      true
      ;;
    *)
      false
      ;;
  esac
}

# Function to add a line to .zshrc (idempotent)
add_to_zshrc() {
  LINE="$1"
  if grep -q "$LINE" ~/.zshrc; then
    echo -e "${YELLOW}Line already exists in ~/.zshrc.${NC}"
  else
    echo "$LINE" >> ~/.zshrc
    echo -e "${GREEN}Added line to ~/.zshrc.${NC}"
  fi
}

# --- Colors ---
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[0;37m'
NC='\033[0m' # No Color

# --- 1. Determine Installation Directory ---

# Display current working directory
CURRENT_DIR=$(pwd)
echo -e "${YELLOW}Current working directory: ${BLUE}$CURRENT_DIR${NC}"

# Ask if the user wants to use the current directory
if confirm "Do you want to use the current directory as the installation directory? "; then
  INSTALL_DIR="$CURRENT_DIR"
else
  # If not, prompt for a custom directory
  INSTALL_DIR=""
  while [ -z "$INSTALL_DIR" ]; do
    read -r -p "Enter the desired installation directory (e.g., ~/Desktop/AiTermy): " INSTALL_DIR
    if [ -z "$INSTALL_DIR" ]; then
      echo -e "${RED}Installation directory cannot be empty.${NC}"
    elif [ ! -d "$(dirname "$INSTALL_DIR")" ]; then
      echo -e "${RED}Invalid directory, it must exist.${NC}"
      INSTALL_DIR=""
    fi
  done
fi

echo -e "The AiTermy will be installed to: ${GREEN}$INSTALL_DIR${NC}"

# --- 2. Collect User Configuration ---

# --- 2.1 Get Command Name ---
while [ -z "$COMMAND_NAME" ]; do
  read -r -p "Enter the desired command name (e.g., ai, termy, ask): " COMMAND_NAME
  if [ -z "$COMMAND_NAME" ]; then
    echo -e "${RED}Command name cannot be empty.${NC}"
  fi
done

# --- 2.2 Get OpenRouter API Key ---
while :; do
  read -r -s -p "Enter your OpenRouter API key (hidden input): " API_KEY
  echo # Newline after hidden input
  if [[ "$API_KEY" != sk-or-* ]]; then
    echo -e "${RED}Invalid API key format - must start with 'sk-or-'.${NC}"
  else
    break
  fi
done

# --- 2.3 Get Preferred Model ---
echo -e "${CYAN}Available models include:${NC}"
echo -e "  ${WHITE}google/gemini-2.0-flash-001${NC} (fast responses)"
echo -e "  ${WHITE}google/gemini-2.0-pro-exp-02-05:free${NC} (more capable)"
echo -e "  ${WHITE}anthropic/claude-3.7-sonnet${NC} (most capable)"
echo -e "  ${WHITE}openai/o1-mini${NC} (balanced)"

PREFERRED_MODEL=""
while [ -z "$PREFERRED_MODEL" ]; do
  read -r -p "Enter your preferred model (default: google/gemini-2.0-flash-001): " PREFERRED_MODEL
  if [ -z "$PREFERRED_MODEL" ]; then
    PREFERRED_MODEL="google/gemini-2.0-flash-001"
    echo -e "${YELLOW}Using default model: ${PREFERRED_MODEL}${NC}"
  fi
done

# --- 3. Create .env file from template ---

# Handle .env configuration
if [ -f "$INSTALL_DIR/.example.env" ]; then
  cp "$INSTALL_DIR/.example.env" "$INSTALL_DIR/.env"
  echo -e "${GREEN}Created .env file from example${NC}"
  
  # Detect OS for sed command compatibility
  if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s|OPENROUTER_API_KEY=.*|OPENROUTER_API_KEY=\"$API_KEY\"|g" "$INSTALL_DIR/.env"
    sed -i '' "s|OPENROUTER_MODEL=.*|OPENROUTER_MODEL=\"$PREFERRED_MODEL\"|g" "$INSTALL_DIR/.env"
  else
    # Linux
    sed -i "s|OPENROUTER_API_KEY=.*|OPENROUTER_API_KEY=\"$API_KEY\"|g" "$INSTALL_DIR/.env"
    sed -i "s|OPENROUTER_MODEL=.*|OPENROUTER_MODEL=\"$PREFERRED_MODEL\"|g" "$INSTALL_DIR/.env"
  fi
  
  # Set secure permissions
  chmod 600 "$INSTALL_DIR/.env"
  echo -e "${GREEN}Secured .env file permissions${NC}"
else
  echo -e "${RED}Error: .example.env file missing - installation cannot continue${NC}"
  exit 1
fi

# Create .aitermy_config.zsh
cat > "$INSTALL_DIR/.aitermy_config.zsh" << EOF
# AiTermy Configuration

# Define the '$COMMAND_NAME' command
function $COMMAND_NAME {
  # Use absolute path for the script
  AI_TERM_PATH='$INSTALL_DIR'
  
  # Call the main python script with proper quoting
  command python3 "\$AI_TERM_PATH/aitermy.py" "\$@"
}
EOF
echo -e "${GREEN}Created .aitermy_config.zsh with command name: ${BLUE}$COMMAND_NAME${NC}"

# --- 4. Ask About Adding to ~/.zshrc ---

if confirm "Do you want to automatically add the AiTermy configuration to your ~/.zshrc?"; then

# Construct the line to add to .zshrc
CONFIG_LINE="source \"$INSTALL_DIR/.aitermy_config.zsh\""

# Add the line, prompting for permission
    add_to_zshrc "$CONFIG_LINE"

  

if grep -q "$CONFIG_LINE" ~/.zshrc; then
  # Verify configuration
  if [ -f ~/.zshrc ] && grep -q "$CONFIG_LINE" ~/.zshrc; then
    echo -e "${GREEN}Configuration successfully added to ~/.zshrc${NC}"
    echo -e "${YELLOW}Configuration will be loaded at the end of setup.${NC}"
  else
    echo -e "${RED}Error: Missing .zshrc file${NC}"
    echo -e "${YELLOW}Manual setup required:${NC}"
    echo "  1. touch ~/.zshrc"
    echo "  2. Add: source \"$INSTALL_DIR/.aitermy_config.zsh\""
  fi
fi

else
  echo -e "${YELLOW}You will need to manually add 'source \"$INSTALL_DIR/.aitermy_config.zsh\"' to your ~/.zshrc.${NC}"
fi

# --- 5. Virtual Environment Setup ---

if confirm "Set up the virtual environment for AiTermy?"; then
  echo -e "${CYAN}Setting up virtual environment...${NC}"
  cd "$INSTALL_DIR" || exit 1
  
  # Create virtual environment
  python3 -m venv venv
  echo -e "${GREEN}Virtual environment created${NC}"
  
  # Install dependencies using the virtual environment's pip
  echo -e "${CYAN}Installing dependencies...${NC}"
  "$INSTALL_DIR/venv/bin/pip" install --upgrade pip
  "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
  
  echo -e "${GREEN}Dependencies installed successfully${NC}"
  
  # Update the command function to use the virtual environment
  if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s|command python3|\"$INSTALL_DIR/venv/bin/python3\"|g" "$INSTALL_DIR/.aitermy_config.zsh"
  else
    # Linux
    sed -i "s|command python3|\"$INSTALL_DIR/venv/bin/python3\"|g" "$INSTALL_DIR/.aitermy_config.zsh"
  fi
  
  echo -e "${GREEN}Command configured to use virtual environment${NC}"
else
  echo -e "${YELLOW}Skipping virtual environment setup. Ensure dependencies are installed manually.${NC}"
fi

# Add .zshrc calling here or user will mess up directory
# Detect OS for sed command compatibility
if [[ "$OSTYPE" == "darwin"* ]]; then
  # macOS
  sed -i "" "s+AI_TERM_PATH=.*+AI_TERM_PATH=\"$INSTALL_DIR\"+g" "$INSTALL_DIR/.aitermy_config.zsh"
else
  # Linux
  sed -i "s+AI_TERM_PATH=.*+AI_TERM_PATH=\"$INSTALL_DIR\"+g" "$INSTALL_DIR/.aitermy_config.zsh"
fi

# --- Final Instructions ---
echo ""
echo -e "${MAGENTA}AiTermy setup is complete!${NC}"
echo ""

# Test API connection
echo -e "${CYAN}Testing OpenRouter API connection...${NC}"
TEST_RESPONSE=$(python3 -c "import os,requests; print(requests.get('https://openrouter.ai/api/v1/auth/key', headers={'Authorization': 'Bearer ${API_KEY}'}).status_code)")
if [ "$TEST_RESPONSE" -eq 200 ]; then
  echo -e "${GREEN}API connection successful!${NC}"
else
  echo -e "${RED}API connection failed (HTTP $TEST_RESPONSE). Check your API key.${NC}"
fi

# Create log directory if logging is enabled
if [[ "$OSTYPE" == "darwin"* ]]; then
  # macOS
  LOG_ENABLED=$(sed -n 's/LOGGING_ENABLED="\(.*\)"/\1/p' "$INSTALL_DIR/.env")
  LOG_FILE=$(sed -n 's/LOG_FILE="\(.*\)"/\1/p' "$INSTALL_DIR/.env")
else
  # Linux
  LOG_ENABLED=$(sed -n 's/LOGGING_ENABLED="\(.*\)"/\1/p' "$INSTALL_DIR/.env")
  LOG_FILE=$(sed -n 's/LOG_FILE="\(.*\)"/\1/p' "$INSTALL_DIR/.env")
fi

if [ "$LOG_ENABLED" = "true" ]; then
  LOG_FILE=$(echo "$LOG_FILE" | sed "s|~|$HOME|g")
  LOG_DIR=$(dirname "$LOG_FILE")
  mkdir -p "$LOG_DIR"
  echo -e "${GREEN}Created log directory: ${LOG_DIR}${NC}"
  echo -e "${CYAN}Logs will be written to: ${LOG_FILE}${NC}"
fi

# Source the changes to make the command immediately available
echo -e "${CYAN}Sourcing changes to make the command available immediately...${NC}"
if [ -f ~/.zshrc ] && grep -q "source \"$INSTALL_DIR/.aitermy_config.zsh\"" ~/.zshrc; then
  # Source the zshrc file to make changes available in current shell
  source ~/.zshrc 2>/dev/null || true
  echo -e "${GREEN}Changes sourced successfully!${NC}"
  echo -e "${CYAN}The ${COMMAND_NAME} command is now available in your terminal.${NC}"
else
  echo -e "${YELLOW}Could not automatically source changes.${NC}"
fi

# Display usage instructions with proper color escaping
printf "\n\033[0;35mSetup Complete! Usage:\033[0m\n"
printf "\033[0;37mRun your custom command:\033[0m\n"
printf "  %s \"your question here\"\n" "$COMMAND_NAME"
printf "\n\033[0;37mWith terminal context:\033[0m\n"
printf "  %s \"your question here\" -l 10\n" "$COMMAND_NAME"
printf "\n\033[0;37mWith file context:\033[0m\n"
printf "  %s \"your question here\" -f filename.py\n" "$COMMAND_NAME"
printf "\n\033[0;37mGet help:\033[0m\n"
printf "  %s -h\n" "$COMMAND_NAME"
printf "\n\033[1;33mIf the command is not available, restart your terminal or run:\033[0m\n"
printf "  source ~/.zshrc\n"

# Make the command available in the current shell
export PATH="$PATH:$INSTALL_DIR"
exit 0
