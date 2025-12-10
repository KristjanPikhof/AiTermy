# AiTermy - Terminal AI Assistant

A powerful terminal AI assistant powered by OpenRouter, providing contextual assistance directly in your terminal. AiTermy can analyze your terminal output, file contents, or both to provide relevant and helpful responses.

## Features

*   **Multiple AI Models**: Choose from various models available through OpenRouter.
*   **Contextual Awareness**: Includes recent terminal history, file contents, and console output.
*   **Console Output Context**: Automatically captures and includes recent command outputs for enhanced context.
*   **Persistent Conversations**: Maintains conversation history between commands for natural follow-up questions.
*   **Multi-File Analysis**: Process and analyze multiple files at once for code comparison, debugging, or comprehension.
*   **Cross-Platform**: Works on both macOS and Linux.
*   **Rich Formatting**: Provides formatted output using Markdown.
*   **Easy Setup & Updates**: Simple installation script with guided configuration that handles updates gracefully.
*   **Custom Command Name**: Choose your own command to invoke the assistant.
*   **Optional Logging**: Log interactions for debugging.
*   **Configurable Console Output**: Control token limits and enable/disable console output capture.

## Requirements

*   **Python 3**: The script automatically detects `python3` or `python` and its associated `pip`.
*   **Zsh shell**: Configuration is added to `~/.zshrc`.
*   **Git**: For cloning the repository.
*   An **OpenRouter API key**: Get one free at [openrouter.ai/keys](https://openrouter.ai/settings/keys).

## Installation & Setup

1.  **Clone the repository:**
    ```bash
    # Make sure you have git installed!
    git clone git@github.com:KristjanPikhof/AiTermy.git
    cd AiTermy
    ```

2.  **Make the setup script executable:**
    ```bash
    chmod +x setup.sh
    ```

3.  **Run the setup script (DO NOT use sudo):**
    ```bash
    ./setup.sh
    ```
    **Important:** Run the script as your regular user, not with `sudo`, as it needs to modify your user-specific files (`~/.zshrc`, `~/.env`) and create files in the chosen directory.

    The setup script will:
    *   Check for Python 3 and pip.
    *   Ask for your preferred installation directory (defaults to the current directory).
    *   Prompt for your OpenRouter API key.
    *   Let you choose your preferred AI model from a list (or enter any valid OpenRouter model).
    *   Ask for a custom command name (e.g., `ai`, `ask`, `termy`).
    *   Ask about console output capture settings (enabled by default, with token limits).
    *   Create/update a `.env` file in the installation directory with your configuration.
    *   Ask for permission to add its configuration source line to your `~/.zshrc`.
    *   Ask to set up a Python virtual environment (`venv`) and install dependencies.
    *   Attempt to source `~/.zshrc` to make the command immediately available.

## Updating

1.  Navigate to the installation directory:
    ```bash
    cd /path/to/your/AiTermy
    ```
2.  Pull the latest changes:
    ```bash
    git pull origin main # Or the appropriate branch
    ```
3.  Re-run the setup script:
    ```bash
    ./setup.sh
    ```
    The script will detect your existing `.env` file and ask if you want to keep your current API key and model, preventing accidental configuration loss. It will also update dependencies if you choose to set up the virtual environment again.

## Usage

Replace `termy` in the examples below with the command name you chose during setup (defaults to `termy`).

```bash
# Basic question
termy "How do I list files sorted by size?"

# Include the last 20 lines of terminal history as context
termy "What does the previous error message mean?" -l 20

# Include the content of a file as context
termy "Explain the main function in this script" -f my_script.py

# Include multiple files using repeated -f flags
termy "Compare these two implementations" -f implementation1.js -f implementation2.js

# Include multiple files using a comma-separated list
termy "Find bugs in these files" -F "main.py,utils.py,config.py"

# Combine history and file context
termy "Why is this test failing?" -l 15 -f test_output.log

# Ask a follow-up question (continues previous conversation by default)
termy "Can you explain that in more detail?"

# Start a new conversation explicitly
termy -n "Let's talk about something else"

# Get help (shows options and current model)
termy -h

# Check version
termy -v
```

## Working with Multiple Files

AiTermy provides two ways to include multiple files as context:

1. **Using multiple `-f` flags**:
   ```bash
   termy "Compare these implementations" -f file1.py -f file2.py -f file3.py
   ```

2. **Using the `-F` flag with a comma-separated list**:
   ```bash
   termy "Analyze these files" -F "controller.js,model.js,view.js"
   ```

This is particularly useful for:
- Comparing different implementations
- Understanding complex projects with multiple components
- Debugging issues across multiple files
- Code reviews
- Finding patterns across files

## Conversation Functionality

AiTermy maintains conversation history between commands, making it easy to have natural back-and-forth interactions:

* **Default behavior**: `termy "question"` automatically continues the previous conversation
* **New conversation**: `termy -n "question"` explicitly starts a fresh conversation
* **Explicit continuation**: `termy -c "question"` explicitly continues a conversation (same as default)

The conversation state is stored in `~/.aitermy/conversations/` and persists between terminal sessions.
By default, up to 10 conversation turns are maintained for context.

After each response, AiTermy shows:
1. The current number of conversation turns
2. How to continue the conversation
3. How to start a new conversation

## Console Output Context

AiTermy can automatically include recent console output in the AI's context, allowing it to see the results of your recent terminal commands. This helps the AI provide more relevant and contextual responses.

**Features:**
- Automatic capture of current directory, recent commands, and system information
- Configurable token limits to avoid exceeding API constraints
- Manual capture of specific command outputs using `ai-capture`
- Intelligent context inclusion based on your configuration

**Configuration:**
Console output capture is **enabled by default** and controlled by environment variables in your `.env` file. See the Configuration section below for details.

**Usage:**
- Console output is automatically included when you run `termy` commands
- The AI will reference recent console activity in its responses

## Configuration (`.env` file)

The setup script creates a `.env` file in the installation directory. You can manually edit this file:

*   `OPENROUTER_API_KEY`: Your key (starts with `sk-or-`). **Required**.
*   `OPENROUTER_MODEL`: The model ID to use (e.g., `x-ai/grok-4.1-fast`). **Required**.
*   `COMMAND_NAME`: The command used to run the tool (set during setup).
*   `LOGGING_ENABLED`: Set to `true` to enable logging. Defaults to `false`. **Optional**.
*   `LOG_FILE`: Path for the log file if enabled (e.g., `~/.aitermy/logs/aitermy.log`). Defaults to `~/.aitermy/logs/aitermy.log`. **Optional**.
*   `CONSOLE_OUTPUT_ENABLED`: Enable/disable automatic console output capture for AI context. Defaults to `true` (enabled by default in setup). **Optional**.
*   `CONSOLE_OUTPUT_MAX_TOKENS`: Maximum tokens for console output context (rough estimation: 4 characters = 1 token). Defaults to `2000`. **Optional**.
*   `CONSOLE_OUTPUT_MAX_ITEMS`: Maximum number of recent console output items to include. Defaults to `10`. **Optional**.

Remember to restart your terminal or run `source ~/.zshrc` after manually editing `.env` or `.aitermy_config.zsh` if the changes aren't reflected immediately.

## Troubleshooting

*   **Command not found:** Ensure the `source "/path/to/your/AiTermy/.aitermy_config.zsh"` line is in your `~/.zshrc` and run `source ~/.zshrc` or restart your terminal.
*   **API Errors:** Double-check your `OPENROUTER_API_KEY` in the `.env` file and ensure it's valid and has credits/access at OpenRouter.
*   **Permission Errors during setup:** Ensure you are *not* running `./setup.sh` with `sudo`.
*   **File Not Found (during use):** Make sure the path provided with `-f` is correct relative to your current working directory.
*   **Check Logs:** If logging is enabled (`LOGGING_ENABLED=true` in `.env`), check the file specified by `LOG_FILE` for detailed error messages.
