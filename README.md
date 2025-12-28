# AiTermy - Terminal AI Assistant

A powerful terminal AI assistant powered by OpenRouter, providing contextual assistance directly in your terminal. AiTermy knows your current directory, recent commands, and shell environment - it sees what you see.

<p align="center">  <img width="827" height="970" alt="SCR-20251210-tsge-2-modified" src="https://github.com/user-attachments/assets/17a0e3e6-0b31-4f3f-86ee-a5d06092f0dd" /> </p>


## Features

*   **Automatic Context Awareness**: AiTermy knows your current directory, recent commands, and shell environment automatically - no manual flags needed.
*   **Multiple Shell Support**: Works with Zsh and Bash on macOS and Linux.
*   **Multiple AI Models**: Choose from various models available through OpenRouter.
*   **Persistent Conversations**: Maintains conversation history between commands for natural follow-up questions.
*   **Multi-File Analysis**: Process and analyze multiple files at once for code comparison or debugging.
*   **Rich Formatting**: Provides formatted output using Markdown.
*   **Easy Setup**: One-command installation with guided configuration.
*   **Custom Command Name**: Choose your own command to invoke the assistant (default: `ai`).

## Requirements

*   **Python 3.11+**: The installer automatically sets up a virtual environment.
*   **Zsh or Bash shell**: Automatic shell integration.
*   **Git**: For cloning the repository.
*   An **OpenRouter API key**: Get one free at [openrouter.ai/keys](https://openrouter.ai/settings/keys).

## Installation (V3)

1.  **Clone the repository:**
    ```bash
    git clone git@github.com:KristjanPikhof/AiTermy.git
    cd AiTermy
    ```

2.  **Run the installer:**
    ```bash
    ./install.sh
    ```

    The installer will:
    *   Detect your shell (Zsh or Bash)
    *   Prompt for your OpenRouter API key
    *   Let you choose your preferred AI model
    *   Set up a Python virtual environment
    *   Add shell integration to your rc file

3.  **Start using AiTermy:**
    ```bash
    source ~/.zshrc  # or ~/.bashrc
    ai "Hello!"
    ```

## Quick Upgrade from V2

If you have an existing V2 installation, the V3 installer will:
*   Detect your existing configuration
*   Migrate your API key and model settings
*   Replace the old shell integration with the new one

Just run `./install.sh` and follow the prompts.

## Updating

1.  Pull the latest changes:
    ```bash
    cd /path/to/your/AiTermy
    git pull origin main
    ```
2.  Re-run the installer:
    ```bash
    ./install.sh
    ```
    The installer will detect your existing configuration and preserve your settings.

## Usage

Replace `ai` in the examples below with your custom command name if you changed it during setup.

```bash
# Basic question - AiTermy automatically knows your context
ai "How do I list files sorted by size?"

# AiTermy knows your recent commands, so just ask about them
ai "What does that error mean?"

# Include a file for code analysis
ai "Explain this code" -f my_script.py

# Compare multiple files
ai "Compare these implementations" -f file1.py -f file2.py

# Or use comma-separated list
ai "Find bugs in these" -F "main.py,utils.py"

# Follow-up questions remember context
ai "Can you explain that in more detail?"

# Start a fresh conversation
ai -n "New topic"

# Interactive mode for extended sessions
ai

# Get help
ai --help
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

## How Context Works (V3)

AiTermy V3 uses shell integration to capture real-time context:

*   **Current directory**: Your actual shell's working directory (not where AiTermy is installed)
*   **Recent commands**: The last 20 commands from your shell session
*   **Last command status**: Whether your last command succeeded or failed
*   **Shell info**: Your shell type (zsh/bash) and version

This context is passed to the AI automatically - you don't need to specify `-l` flags anymore.

## Configuration

V3 uses a TOML configuration file at `~/.aitermy/config.toml`:

```toml
[api]
key = "sk-or-your-key"
model = "x-ai/grok-4.1-fast"

[context]
include_history = true
history_lines = 20
max_context_tokens = 2000

[ui]
command = "ai"

[logging]
enabled = false
file = "~/.aitermy/logs/aitermy.log"

[conversation]
max_turns = 10
```

### Key Settings

*   `api.key`: Your OpenRouter API key (required)
*   `api.model`: The model to use (browse at [openrouter.ai/models](https://openrouter.ai/models))
*   `ui.command`: The command name to invoke AiTermy
*   `context.history_lines`: Number of recent commands to include
*   `logging.enabled`: Enable debug logging

After editing the config, open a new terminal for changes to take effect.

## Troubleshooting

*   **Command not found:** Run `source ~/.zshrc` (or `~/.bashrc`) or open a new terminal. Check that the source line is in your rc file.
*   **API Errors:** Check your API key in `~/.aitermy/config.toml`. Ensure it starts with `sk-or-` and is valid.
*   **Context not working:** Ensure you're using the shell integration (the `ai` function, not calling the Python script directly).
*   **File Not Found:** Make sure the path with `-f` is correct relative to your current directory.
*   **Check Logs:** Enable logging in config.toml and check `~/.aitermy/logs/aitermy.log`.

## Directory Structure (V3)

```
~/.aitermy/
├── bin/aitermy.py          # Main script
├── config.toml             # Configuration
├── shell/
│   ├── ai.zsh              # Zsh integration
│   └── ai.bash             # Bash integration
├── venv/                   # Python virtual environment
├── data/
│   ├── conversations/      # Conversation history
│   └── sessions/           # Terminal session data
└── logs/                   # Log files (if enabled)
```
