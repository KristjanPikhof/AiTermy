# AiTermy - Terminal AI Assistant

A powerful terminal AI assistant powered by OpenRouter, providing contextual assistance directly in your terminal. AiTermy can analyze your terminal output, file contents, or both to provide relevant and helpful responses.

## Features

* **Multiple AI Models**: Choose from various models like Google Gemini, Claude, Mistral, and more
* **Contextual Awareness**: Includes terminal context (recent lines) and/or file contents
* **Cross-Platform**: Works on both macOS and Linux
* **Rich Formatting**: Provides beautifully formatted output with syntax highlighting
* **Easy Setup**: Simple installation process with guided configuration

## Requirements

* Python 3.7+
* Zsh shell
* An OpenRouter API key (get one at [openrouter.ai](https://openrouter.ai/settings/keys))

## Setup

1. **Clone the repository:**
   ```bash
   git clone git@github.com:KristjanPikhof/AiTermy.git
   cd AiTermy
   ```

2. **Make the setup script executable:**
   ```bash
   chmod +x setup.sh
   ```

3. **Run the setup script:**
   ```bash
   ./setup.sh
   ```
   
   The setup script will:
   * Ask for your preferred installation directory
   * Prompt for your OpenRouter API key
   * Let you choose your preferred AI model
   * Create a custom command name of your choice
   * Configure your `~/.zshrc` file (with your permission)
   * Set up a virtual environment and install dependencies
   * Make the command immediately available in your terminal

## Usage

```bash
# Basic usage (replace 'termy' with your chosen command name)
termy "Your question here"

# Include recent terminal output as context
termy "What does this error mean?" -l 20

# Include file content as context
termy "Explain this code" -f app.js

# Combine both contexts
termy "How to fix this bug?" -l 10 -f error.log

# Get help
termy -h
```

## Advanced Usage

* **Customize the number of context lines**: Use `-l` or `--lines` followed by a number
* **Include file content**: Use `-f` or `--file` followed by a filename
* **Check version**: Use `-v` or `--version` to see the current version and model

## Troubleshooting

If you encounter any issues:

1. Ensure your API key is correctly set in the `.env` file
2. Make sure you've sourced your `.zshrc` file after installation
3. Check that the virtual environment is properly set up
4. Verify your internet connection for API access

## Customization

You can edit the `.env` file to change your API key or preferred model at any time.
