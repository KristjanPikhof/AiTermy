#!/bin/bash

# Check if running as root
if [ "$(id -u)" -eq 0 ]; then
   echo -e "${RED}Error: This script should not be run as root or with sudo.${NC}"
   echo "Please run it as your regular user."
   exit 1
fi

# --- Colors ---
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[0;37m'
NC='\033[0m' # No Color

# --- Detect OS ---
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE="macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS_TYPE="Linux"
else
    OS_TYPE="Other"
fi
echo -e "${CYAN}Detected OS: ${OS_TYPE}${NC}"

# --- Find Python & Pip ---
PYTHON_CMD=""
PIP_CMD=""

# Try python3
if command -v python3 &> /dev/null; then
    if python3 --version 2>&1 | grep -q "Python 3\\."; then
        PYTHON_CMD="python3"
    fi
fi

# If python3 not found or not version 3, try python
if [ -z "$PYTHON_CMD" ]; then
    if command -v python &> /dev/null; then
        # Suppress "Python 2.7 is deprecated" warning on stderr
        if python --version 2>&1 | grep -q "Python 3\\."; then
            PYTHON_CMD="python"
        fi
    fi
fi

# Check if Python 3 found
if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}Error: Could not find a Python 3 interpreter (tried 'python3' and 'python'). Please install Python 3.${NC}"
    exit 1
else
    echo -e "${GREEN}Using Python command: ${BLUE}$PYTHON_CMD${NC}"
fi

# Find Pip using the found Python command
if $PYTHON_CMD -m pip --version &> /dev/null; then
    PIP_CMD="$PYTHON_CMD -m pip"
else
    # Try pip3
    if command -v pip3 &> /dev/null; then
        PIP_CMD="pip3"
    # Try pip
    elif command -v pip &> /dev/null; then
        if pip --version 2>&1 | grep -q "$PYTHON_CMD"; then
            PIP_CMD="pip"
        fi
    fi
fi

# Verify pip was found
if [ -z "$PIP_CMD" ]; then
    echo -e "${RED}Error: Could not find pip for $PYTHON_CMD. Please ensure pip is installed.${NC}"
    exit 1
else
    echo -e "${GREEN}Using Pip command: ${BLUE}$PIP_CMD${NC}"
fi

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

# --- Basic Setup ---
INSTALL_DIR=$(pwd)
echo -e "${CYAN}Using installation directory: ${INSTALL_DIR}${NC}"

# Check for existing .env file
if [ -f ".env" ]; then
  echo -e "${YELLOW}Found existing .env file. Reading configuration...${NC}"

  # Read existing values
  EXISTING_API_KEY=$(grep -i '^[[:space:]]*OPENROUTER_API_KEY' .env | sed -n 's/^[[:space:]]*OPENROUTER_API_KEY[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p')
  EXISTING_MODEL=$(grep -i '^[[:space:]]*OPENROUTER_MODEL' .env | sed -n 's/^[[:space:]]*OPENROUTER_MODEL[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p')
  EXISTING_COMMAND=$(grep -i '^[[:space:]]*COMMAND_NAME' .env | sed -n 's/^[[:space:]]*COMMAND_NAME[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p')
  EXISTING_LOGGING=$(grep -i '^[[:space:]]*LOGGING_ENABLED' .env | sed -n 's/^[[:space:]]*LOGGING_ENABLED[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p')
  EXISTING_LOG_FILE=$(grep -i '^[[:space:]]*LOG_FILE' .env | sed -n 's/^[[:space:]]*LOG_FILE[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p')
  
  # Handle command name
  if [ -n "$EXISTING_COMMAND" ]; then
    if confirm "Keep existing command name '$EXISTING_COMMAND'?"; then
      COMMAND_NAME="$EXISTING_COMMAND"
      echo -e "${GREEN}Using existing command name: ${COMMAND_NAME}${NC}"
    else
      read -r -p "Enter the desired command name (e.g., ai, termy, ask): " COMMAND_NAME
      echo -e "${GREEN}Using new command name: ${COMMAND_NAME}${NC}"
    fi
  else
    read -r -p "Enter the desired command name (e.g., ai, termy, ask): " COMMAND_NAME
    echo -e "${GREEN}Using command name: ${COMMAND_NAME}${NC}"
  fi
  
  # Handle API key
  if [ -n "$EXISTING_API_KEY" ]; then
    MASKED_KEY="${EXISTING_API_KEY:0:6}...${EXISTING_API_KEY: -4}"
    if confirm "Keep existing API key ($MASKED_KEY)?"; then
      API_KEY="$EXISTING_API_KEY"
      echo -e "${GREEN}Using existing API key${NC}"
    else
      read -r -s -p "Enter your OpenRouter API key: " API_KEY
      echo # Newline after hidden input
      echo -e "${GREEN}API key updated${NC}"
    fi
  else
    read -r -s -p "Enter your OpenRouter API key: " API_KEY
    echo # Newline after hidden input
    echo -e "${GREEN}API key received${NC}"
  fi
  
  # Handle model
  if [ -n "$EXISTING_MODEL" ]; then
    if confirm "Keep existing model '$EXISTING_MODEL'?"; then
      PREFERRED_MODEL="$EXISTING_MODEL"
      echo -e "${GREEN}Using existing model: ${PREFERRED_MODEL}${NC}"
    else
      echo -e "${CYAN}Available models include:${NC}"
      echo -e "  ${WHITE}meta-llama/llama-4-scout${NC} (fast responses & cost-effective)"
      echo -e "  ${WHITE}google/gemini-2.0-flash-001${NC} (more capable & cost-effective)"
      echo -e "  ${WHITE}anthropic/claude-3.7-sonnet${NC} (most capable but expensive)"
      echo -e "  ${WHITE}google/gemini-2.5-pro-preview-03-25${NC} (balanced)"
      read -r -p "Enter your preferred model (default: google/gemini-2.5-pro-preview-03-25): " MODEL_INPUT
      if [ -z "$MODEL_INPUT" ]; then
        PREFERRED_MODEL="google/gemini-2.5-pro-preview-03-25"
      else
        PREFERRED_MODEL="$MODEL_INPUT"
      fi
      echo -e "${GREEN}Using model: ${PREFERRED_MODEL}${NC}"
    fi
  else
    PREFERRED_MODEL="google/gemini-2.5-pro-preview-03-25"
    echo -e "${GREEN}Using default model: ${PREFERRED_MODEL}${NC}"
  fi
  
  # Handle logging
  if [ -n "$EXISTING_LOGGING" ]; then
    LOGGING_ENABLED="$EXISTING_LOGGING"
    echo -e "${GREEN}Using existing logging setting: ${LOGGING_ENABLED}${NC}"
  else
    LOGGING_ENABLED="false"
    echo -e "${GREEN}Using default logging setting: ${LOGGING_ENABLED}${NC}"
  fi
  
  # Handle log file
  if [ -n "$EXISTING_LOG_FILE" ]; then
    LOG_FILE="$EXISTING_LOG_FILE"
    echo -e "${GREEN}Using existing log file path: ${LOG_FILE}${NC}"
  else
    LOG_FILE="~/.aitermy/logs/aitermy.log"
    echo -e "${GREEN}Using default log file path: ${LOG_FILE}${NC}"
  fi
  
else
  # No existing .env file - proceed with normal setup
  
  # Get command name
  read -r -p "Enter the desired command name (e.g., ai, termy, ask): " COMMAND_NAME
  echo -e "${GREEN}Using command name: ${COMMAND_NAME}${NC}"
  
  # Get API key
  read -r -s -p "Enter your OpenRouter API key: " API_KEY
  echo # Newline after hidden input
  echo -e "${GREEN}API key received${NC}"
  
  # Get preferred model
  PREFERRED_MODEL="google/gemini-2.5-pro-preview-03-25"
  echo -e "${GREEN}Using model: ${PREFERRED_MODEL}${NC}"
  
  # Set logging defaults
  LOGGING_ENABLED="false"
  echo -e "${GREEN}Using default logging setting: ${LOGGING_ENABLED}${NC}"
  
  LOG_FILE="~/.aitermy/logs/aitermy.log"
  echo -e "${GREEN}Using default log file path: ${LOG_FILE}${NC}"
fi

# Create .env file
echo "OPENROUTER_API_KEY=\"$API_KEY\"" > .env
echo "OPENROUTER_MODEL=\"$PREFERRED_MODEL\"" >> .env
echo "COMMAND_NAME=\"$COMMAND_NAME\"" >> .env
echo "LOGGING_ENABLED=\"$LOGGING_ENABLED\"" >> .env
echo "LOG_FILE=\"$LOG_FILE\"" >> .env
echo -e "${GREEN}Created .env file${NC}"

# Secure permissions
chmod 600 .env
echo -e "${GREEN}Set secure permissions on .env file${NC}"

# Create the command file
cat > .aitermy_config.zsh << 'EOF'
# AiTermy Configuration

# Define the command
function COMMAND_NAME {
  # Use absolute path for the script
  AI_TERM_PATH="INSTALL_DIR"
  
  # Call the main python script with proper quoting
  command PYTHON_CMD_PLACEHOLDER "$AI_TERM_PATH/aitermy.py" "$@"
}
EOF

# Replace placeholders based on OS
if [[ "$OSTYPE" == "darwin"* ]]; then
  # macOS sed
  sed -i '' "s|COMMAND_NAME|$COMMAND_NAME|g" .aitermy_config.zsh
  sed -i '' "s|INSTALL_DIR|$INSTALL_DIR|g" .aitermy_config.zsh
  sed -i '' "s|PYTHON_CMD_PLACEHOLDER|$PYTHON_CMD|g" .aitermy_config.zsh
else
  # Linux/other sed
  sed -i "s|COMMAND_NAME|$COMMAND_NAME|g" .aitermy_config.zsh
  sed -i "s|INSTALL_DIR|$INSTALL_DIR|g" .aitermy_config.zsh
  sed -i "s|PYTHON_CMD_PLACEHOLDER|$PYTHON_CMD|g" .aitermy_config.zsh
fi

echo -e "${GREEN}Created command configuration${NC}"

# Set up virtual environment if needed
if confirm "Set up virtual environment?"; then
  echo -e "${CYAN}Setting up virtual environment...${NC}"
  $PYTHON_CMD -m venv venv
  
  # Define paths to virtual environment executables
  if [ -f "venv/bin/python" ]; then
    VENV_PYTHON="$INSTALL_DIR/venv/bin/python"
    VENV_PIP="$INSTALL_DIR/venv/bin/pip"
  elif [ -f "venv/Scripts/python.exe" ]; then
    # Windows path
    VENV_PYTHON="$INSTALL_DIR/venv/Scripts/python.exe"
    VENV_PIP="$INSTALL_DIR/venv/Scripts/pip.exe"
  else
    echo -e "${RED}Error: Could not locate Python in the virtual environment.${NC}"
    exit 1
  fi
  
  # Install dependencies using the virtual environment's pip
  echo -e "${CYAN}Installing dependencies...${NC}"
  "$VENV_PYTHON" -m pip install --upgrade pip
  "$VENV_PYTHON" -m pip install -r requirements.txt
  
  # Update to use venv python
  if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS sed
    sed -i '' "s|command $PYTHON_CMD|\"$VENV_PYTHON\"|g" .aitermy_config.zsh
  else
    # Linux/other sed
    sed -i "s|command $PYTHON_CMD|\"$VENV_PYTHON\"|g" .aitermy_config.zsh
  fi
  echo -e "${GREEN}Virtual environment set up${NC}"
fi

# Add to .zshrc if needed
if confirm "Add command to your .zshrc?"; then
  CONFIG_LINE="source \"$INSTALL_DIR/.aitermy_config.zsh\""
  if grep -q "$CONFIG_LINE" ~/.zshrc; then
    echo -e "${YELLOW}Already in .zshrc${NC}"
  else
    echo "$CONFIG_LINE" >> ~/.zshrc
    echo -e "${GREEN}Added to .zshrc${NC}"
  fi
fi

# Done!
echo -e "${MAGENTA}Installation complete!${NC}"
echo -e "${GREEN}You can now use the '${COMMAND_NAME}' command${NC}"
exit 0 