#!/usr/bin/env python3
import argparse
import datetime
import json
import logging
import os
import pathlib
import pickle
import re
import subprocess
import sys

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Fallback for Python 3.8-3.10
    except ImportError:
        tomllib = None


# Auto-detect and use virtual environment if available
def setup_virtual_environment():
    """Automatically detect and use virtual environment if available"""
    # Check if we're already in a virtual environment
    if hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    ):
        return  # Already in venv

    # First try ~/.aitermy/venv (V3 location)
    aitermy_home = os.path.expanduser("~/.aitermy")
    venv_path = os.path.join(aitermy_home, "venv")

    # Fallback to script directory venv (V2 compatibility)
    if not os.path.exists(venv_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        venv_path = os.path.join(script_dir, "venv")

    # Check if venv directory exists
    if os.path.exists(venv_path):
        # Determine the correct Python executable path
        if os.name == "nt":  # Windows
            venv_python = os.path.join(venv_path, "Scripts", "python.exe")
        else:  # Unix-like systems
            venv_python = os.path.join(venv_path, "bin", "python")

        if os.path.exists(venv_python):
            # Restart the script with the virtual environment's Python
            os.execv(venv_python, [venv_python] + sys.argv)


# Set up virtual environment before importing dependencies
setup_virtual_environment()

import requests
from dotenv import load_dotenv
from rich.align import Align
from rich.columns import Columns
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.spinner import Spinner
from rich.text import Text

# Version information
VERSION = "3.0.0"

# AiTermy home directory
AITERMY_HOME = os.path.expanduser("~/.aitermy")


def load_config():
    """Load configuration from TOML file or fall back to .env"""
    config = {}

    # Try V3 TOML config first
    toml_config_path = os.path.join(AITERMY_HOME, "config.toml")
    if tomllib and os.path.exists(toml_config_path):
        try:
            with open(toml_config_path, "rb") as f:
                config = tomllib.load(f)
            return config
        except Exception:
            pass  # Fall through to .env

    # Fall back to V2 .env (for backward compatibility)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(script_dir, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)

    # Build config from environment variables
    config = {
        "api": {
            "key": os.environ.get("OPENROUTER_API_KEY", ""),
            "model": os.environ.get("OPENROUTER_MODEL", "x-ai/grok-4.1-fast"),
        },
        "context": {
            "include_history": True,
            "history_lines": 20,
            "include_env": True,
            "max_context_tokens": int(os.environ.get("CONSOLE_OUTPUT_MAX_TOKENS", "2000")),
        },
        "ui": {
            "command": os.environ.get("COMMAND_NAME", "ai"),
        },
        "logging": {
            "enabled": os.environ.get("LOGGING_ENABLED", "false").lower() == "true",
            "file": os.environ.get("LOG_FILE", "~/.aitermy/logs/aitermy.log"),
        },
        "conversation": {
            "max_turns": 10,
            "storage_dir": "~/.aitermy/data/conversations",
        },
    }
    return config


# Load configuration
CONFIG = load_config()

# OpenRouter info
OPENROUTER_API_KEY = CONFIG.get("api", {}).get("key", "")
OPENROUTER_MODEL = CONFIG.get("api", {}).get("model", "x-ai/grok-4.1-fast")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_LINES = CONFIG.get("context", {}).get("history_lines", 20)

# Command Name
COMMAND_NAME = CONFIG.get("ui", {}).get("command", "ai") or "ai"

# Conversation history configuration
CONVERSATION_DIR = os.path.expanduser(
    CONFIG.get("conversation", {}).get("storage_dir", "~/.aitermy/data/conversations")
)
CURRENT_CONVERSATION_FILE = os.path.join(CONVERSATION_DIR, "current_conversation.pkl")
MAX_CONVERSATION_TURNS = CONFIG.get("conversation", {}).get("max_turns", 10)

# Logging configuration
LOGGING_ENABLED = CONFIG.get("logging", {}).get("enabled", False)
LOG_FILE = os.path.expanduser(
    CONFIG.get("logging", {}).get("file", "~/.aitermy/logs/aitermy.log")
)

# Context configuration
CONTEXT_INCLUDE_HISTORY = CONFIG.get("context", {}).get("include_history", True)
CONTEXT_MAX_TOKENS = CONFIG.get("context", {}).get("max_context_tokens", 2000)

# Legacy console output configuration (for backward compatibility)
CONSOLE_OUTPUT_ENABLED = True
CONSOLE_OUTPUT_MAX_TOKENS = CONTEXT_MAX_TOKENS
CONSOLE_OUTPUT_MAX_ITEMS = 10

# Setup logging if enabled
if LOGGING_ENABLED:
    # Create log directory if it doesn't exist
    log_dir = os.path.dirname(LOG_FILE)
    pathlib.Path(log_dir).mkdir(parents=True, exist_ok=True)

    # Configure logging
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.info(f"AiTermy v{VERSION} started")
    logging.info(f"Using model: {OPENROUTER_MODEL}")

# Create conversation directory if it doesn't exist
pathlib.Path(CONVERSATION_DIR).mkdir(parents=True, exist_ok=True)


# Function to log messages if logging is enabled
def log(message, level="INFO"):
    if LOGGING_ENABLED:
        if level.upper() == "INFO":
            logging.info(message)
        elif level.upper() == "WARNING":
            logging.warning(message)
        elif level.upper() == "ERROR":
            logging.error(message)
        elif level.upper() == "DEBUG":
            logging.debug(message)


# Rich configurations
console = Console()


def build_system_message(shell_context=None):
    """Build the system message with full context"""
    if shell_context is None:
        shell_context = get_shell_context()

    os_type = "macOS" if sys.platform == "darwin" else "Linux"
    pwd = shell_context.get("pwd", os.getcwd())
    shell = shell_context.get("shell", "unknown")
    v3_mode = shell_context.get("v3_mode", False)

    # Base system message
    system_message = f"You are a helpful terminal AI assistant running on {os_type}."
    system_message += f"\nCurrent directory: {pwd}"

    if v3_mode:
        # V3 mode: we have rich context from shell integration
        if shell_context.get("oldpwd"):
            system_message += f"\nPrevious directory: {shell_context['oldpwd']}"
        if shell:
            shell_version = shell_context.get("shell_version", "")
            system_message += f"\nShell: {shell}" + (f" {shell_version}" if shell_version else "")
        if shell_context.get("user") and shell_context.get("host"):
            system_message += f"\nUser: {shell_context['user']}@{shell_context['host']}"

        # Add recent command history from shell
        history = shell_context.get("history", "")
        if history:
            system_message += f"\n\nRecent commands:\n{history}"

        # Add last command and its exit status
        last_cmd = shell_context.get("last_cmd", "")
        last_status = shell_context.get("last_status", "0")
        if last_cmd:
            status_text = "succeeded" if last_status == "0" else f"failed (exit code {last_status})"
            system_message += f"\n\nLast command: {last_cmd} ({status_text})"

    system_message += "\n\nProvide concise, direct answers suitable for terminal output. "
    system_message += "Use Markdown formatting where appropriate (like code blocks), but avoid overly long paragraphs. "
    system_message += "Focus directly on the user's question."

    return system_message


def show_welcome_screen(shell_context=None):
    """Display a welcome screen for interactive mode"""
    if shell_context is None:
        shell_context = get_shell_context()

    pwd = shell_context.get("pwd", os.getcwd())
    shell = shell_context.get("shell", "")
    v3_mode = shell_context.get("v3_mode", False)

    # Build context indicator
    context_info = f"[dim]{pwd}[/dim]"
    if v3_mode and shell:
        context_info += f" [dim]({shell})[/dim]"

    welcome_panel = Panel(
        Align.center(
            f"[bold cyan]AiTermy Terminal Assistant v{VERSION}[/bold cyan]\n\n"
            f"{context_info}\n\n"
            f"[dim]Type your questions and press Enter[/dim]\n"
            f"[dim]Commands: /h(elp), /hi(story), /c(lear), /q(uit), /m(odel)[/dim]\n"
            f"[dim]Model: {OPENROUTER_MODEL}[/dim]"
        ),
        title="[bold blue]Welcome[/bold blue]",
        border_style="blue",
        padding=(1, 2),
    )
    console.print(welcome_panel)
    console.print()


def show_interactive_help():
    """Show help for interactive mode"""
    help_text = """
# Interactive Mode Commands

* **/help** (/h) - Show this help
* **/history** (/hi) - View conversation history
* **/clear** (/c) - Clear current conversation
* **/quit** (/q) or **/exit** - Exit interactive mode
* **/model** (/m) - Show current model info

## Regular Usage
Just type your question and press Enter. The conversation continues automatically.

## Examples
```
What is the capital of France?
How do I list files in Linux?
Explain this error: permission denied
/history
/quit
```
"""
    console.print(
        Panel(Markdown(help_text), title="Interactive Help", border_style="cyan")
    )


def show_conversation_history():
    """Display recent conversation history"""
    try:
        if os.path.exists(CURRENT_CONVERSATION_FILE):
            with open(CURRENT_CONVERSATION_FILE, "rb") as f:
                history = pickle.load(f)

            if not history:
                empty_panel = Panel(
                    "[dim]No conversation history found.\nStart a conversation to see history here![/dim]",
                    title="[dim]📝 Conversation History[/dim]",
                    border_style="dim blue",
                    padding=(1, 2),
                )
                console.print(empty_panel)
                return

            # Count user messages (excluding system message)
            user_messages = [msg for msg in history if msg["role"] == "user"]

            # Create conversation summary
            history_panels = []
            for i, msg in enumerate(history):
                if msg["role"] == "system":
                    continue  # Skip system message

                role_color = "green" if msg["role"] == "user" else "blue"
                role_icon = "👤" if msg["role"] == "user" else "🤖"
                role_title = "You" if msg["role"] == "user" else "AiTermy"

                # Truncate long messages for display
                content = msg["content"]
                if len(content) > 150:
                    content = content[:150] + "..."

                msg_panel = Panel(
                    f"[{role_color}]{content}[/{role_color}]",
                    title=f"[{role_color}]{role_icon} {role_title}[/{role_color}]",
                    border_style=role_color,
                    padding=(0, 1),
                )
                history_panels.append(msg_panel)

            # Display header
            header_panel = Panel(
                f"[bold cyan]📝 Conversation History[/bold cyan]\n[dim]{len(user_messages)} turns • {len(history)} messages total[/dim]",
                border_style="cyan",
                padding=(0, 1),
            )
            console.print(header_panel)
            console.print()

            # Display conversation turns
            if history_panels:
                # Group into turns (user + assistant pairs)
                turns = []
                current_turn = []

                for panel in history_panels:
                    current_turn.append(panel)
                    if len(current_turn) == 2:  # User + Assistant = 1 turn
                        turns.append(Columns(current_turn, equal=True, expand=True))
                        current_turn = []

                # Add any remaining single message
                if current_turn:
                    turns.append(current_turn[0])

                for turn in turns:
                    console.print(turn)
                    console.print()  # Spacing between turns

        else:
            empty_panel = Panel(
                "[dim]No conversation history found.\nStart a conversation to see history here![/dim]",
                title="[dim]📝 Conversation History[/dim]",
                border_style="dim blue",
                padding=(1, 2),
            )
            console.print(empty_panel)

    except Exception as e:
        error_panel = Panel(
            f"[red]❌ Error loading history:[/red] {e}",
            title="[red]History Error[/red]",
            border_style="red",
            padding=(1, 2),
        )
        console.print(error_panel)


def show_session_summary(conversation_history, start_time):
    """Show a summary of the interactive session"""
    if not conversation_history:
        return

    user_turns = len([msg for msg in conversation_history if msg["role"] == "user"])
    assistant_turns = len(
        [msg for msg in conversation_history if msg["role"] == "assistant"]
    )

    session_duration = datetime.datetime.now() - start_time
    duration_str = f"{session_duration.seconds // 60}m {session_duration.seconds % 60}s"

    # Calculate console output statistics
    console_stats = ""
    if CONSOLE_OUTPUT_ENABLED:
        # Estimate tokens used for console output in system message
        console_context = get_console_output_context()
        if console_context:
            estimated_tokens = len(console_context) // 4  # Rough estimation
            console_stats = f"\n• Console output: ~{estimated_tokens} tokens"
        else:
            console_stats = f"\n• Console output: enabled (no recent data)"

    summary_panel = Panel(
        f"""[bold green]Session Summary[/bold green]

[dim]📊 Statistics:[/dim]
• Questions asked: {user_turns}
• Answers received: {assistant_turns}
• Session duration: {duration_str}
• Model used: {OPENROUTER_MODEL}{console_stats}

[dim]💾 Conversation saved to: ~/.aitermy/conversations/[/dim]
[dim]🔄 Continue anytime with: {COMMAND_NAME} "follow-up question"[/dim]""",
        title="[green]🎉 Session Complete[/green]",
        border_style="green",
        padding=(1, 2),
    )
    console.print(summary_panel)


def interactive_mode():
    """Run the interactive mode"""
    log("Starting interactive mode")
    session_start = datetime.datetime.now()

    # Get shell context (from V3 shell integration or fallback)
    shell_context = get_shell_context()

    # Load existing conversation
    conversation_history = load_conversation_history()
    if not conversation_history:
        # Build system message with full context
        system_message = build_system_message(shell_context)

        # Add console output context if available (for legacy compatibility)
        if CONSOLE_OUTPUT_ENABLED:
            console_context = get_console_output_context()
            if console_context:
                system_message += (
                    f"\n\nRecent console output context:\n{console_context}"
                )

        conversation_history = [{"role": "system", "content": system_message}]

    show_welcome_screen(shell_context)

    try:
        while True:
            try:
                # Get user input with better prompt
                prompt_text = f"[bold cyan]{COMMAND_NAME}[/bold cyan][dim]>[/dim]"
                user_input = Prompt.ask(prompt_text).strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.lower() in ["/quit", "/exit", "/q", "/e", "exit", "quit"]:
                    console.print()  # Add spacing
                    show_session_summary(conversation_history, session_start)
                    console.print("[bold green]👋 Goodbye![/bold green]")
                    break
                elif user_input.lower() in ["/help", "/h", "help", "?"]:
                    show_interactive_help()
                    console.print()  # Add spacing
                    continue
                elif user_input.lower() in ["/history", "/hi", "history"]:
                    show_conversation_history()
                    console.print()  # Add spacing
                    continue
                elif user_input.lower() in ["/clear", "/c", "clear"]:
                    confirm_clear = Confirm.ask(
                        "[yellow]Clear current conversation?[/yellow]"
                    )
                    if confirm_clear:
                        start_new_conversation()
                        conversation_history = [
                            {
                                "role": "system",
                                "content": conversation_history[0]["content"],
                            }
                        ]
                        success_panel = Panel(
                            "[green]✅ Conversation cleared![/green]",
                            border_style="green",
                            padding=(0, 1),
                        )
                        console.print(success_panel)
                    console.print()
                    continue
                elif user_input.lower() in ["/model", "/m", "model"]:
                    model_panel = Panel(
                        f"[dim]🤖 Current model: {OPENROUTER_MODEL}[/dim]",
                        border_style="blue",
                        padding=(0, 1),
                    )
                    console.print(model_panel)
                    console.print()
                    continue

                # Process the question
                with console.status(
                    "[bold cyan]🤔 Thinking...[/bold cyan]", spinner="dots"
                ) as status:
                    # Add user message to conversation
                    conversation_history.append({"role": "user", "content": user_input})

                    # Query OpenRouter
                    response = query_openrouter(conversation_history)
                    answer = extract_model_response(response)

                    # Only add assistant response to conversation if it's not an error
                    if not answer.startswith("Error extracting response:"):
                        conversation_history.append(
                            {"role": "assistant", "content": answer}
                        )

                    # Keep only the last MAX_CONVERSATION_TURNS turns
                    if len(conversation_history) > 2 * MAX_CONVERSATION_TURNS + 1:
                        conversation_history = [
                            conversation_history[0]
                        ] + conversation_history[-(2 * MAX_CONVERSATION_TURNS) :]

                    # Save conversation
                    save_conversation_history(conversation_history)

                # Display response
                console.print()  # Add spacing
                answer_panel = Panel(
                    Markdown(answer),
                    title="[bold blue]🤖 Answer[/bold blue]",
                    border_style="blue",
                    padding=(1, 2),
                )
                console.print(answer_panel)

                # Show conversation status
                user_turns = len(
                    [msg for msg in conversation_history if msg["role"] == "user"]
                )
                status_panel = Panel(
                    f"[dim]💬 {user_turns} turns | Type /help for commands | Ctrl+C to interrupt[/dim]",
                    border_style="dim cyan",
                    padding=(0, 1),
                )
                console.print(status_panel)
                console.print()

            except KeyboardInterrupt:
                interrupt_panel = Panel(
                    "[yellow]⚠️  Interrupted![/yellow]\n[dim]Type /quit to exit or continue asking questions.[/dim]",
                    border_style="yellow",
                    padding=(0, 1),
                )
                console.print(interrupt_panel)
                console.print()
            except EOFError:
                console.print()
                show_session_summary(conversation_history, session_start)
                console.print("[bold green]👋 Goodbye![/bold green]")
                break
            except Exception as e:
                error_panel = Panel(
                    f"[red]❌ Error:[/red] {e}",
                    title="[red]Error[/red]",
                    border_style="red",
                    padding=(1, 2),
                )
                console.print(error_panel)
                console.print()
                log(f"Interactive mode error: {e}", "ERROR")

    except KeyboardInterrupt:
        console.print()
        show_session_summary(conversation_history, session_start)
        console.print("[bold yellow]👋 Session ended![/bold yellow]")

    log("Exiting interactive mode")


def load_conversation_history():
    """Load the current conversation history if it exists"""
    try:
        if os.path.exists(CURRENT_CONVERSATION_FILE):
            with open(CURRENT_CONVERSATION_FILE, "rb") as f:
                history = pickle.load(f)
                log(f"Loaded conversation history with {len(history)} messages")
                return history
    except Exception as e:
        log(f"Error loading conversation history: {e}", "ERROR")
    return []  # Return empty history if file doesn't exist or on error


def save_conversation_history(history):
    """Save the current conversation history"""
    try:
        with open(CURRENT_CONVERSATION_FILE, "wb") as f:
            pickle.dump(history, f)
            log(f"Saved conversation history with {len(history)} messages")
    except Exception as e:
        log(f"Error saving conversation history: {e}", "ERROR")


def start_new_conversation():
    """Clear the current conversation history"""
    try:
        if os.path.exists(CURRENT_CONVERSATION_FILE):
            os.remove(CURRENT_CONVERSATION_FILE)
            log("Started new conversation (cleared history)")
    except Exception as e:
        log(f"Error clearing conversation history: {e}", "ERROR")


def get_shell_context():
    """Get context passed from shell integration (V3 approach)"""
    context = {
        "pwd": os.environ.get("AITERMY_PWD", ""),
        "oldpwd": os.environ.get("AITERMY_OLDPWD", ""),
        "shell": os.environ.get("AITERMY_SHELL", ""),
        "shell_version": os.environ.get("AITERMY_SHELL_VERSION", ""),
        "history": os.environ.get("AITERMY_HISTORY", ""),
        "last_cmd": os.environ.get("AITERMY_LAST_CMD", ""),
        "last_status": os.environ.get("AITERMY_LAST_STATUS", "0"),
        "term_cols": os.environ.get("AITERMY_TERM_COLS", "80"),
        "term_lines": os.environ.get("AITERMY_TERM_LINES", "24"),
        "tty": os.environ.get("AITERMY_TTY", ""),
        "user": os.environ.get("AITERMY_USER", os.environ.get("USER", "")),
        "host": os.environ.get("AITERMY_HOST", ""),
    }

    # Defensive: Filter out self-invocations as safety net
    # Shell should already handle this, but double-check
    command_name = CONFIG.get("ui", {}).get("command", "ai")
    if context["last_cmd"].startswith(f"{command_name} "):
        context["last_cmd"] = ""  # Clear if it's the AI command itself
        log("Filtered self-invocation from last_cmd")

    # Check if we have V3 shell integration (AITERMY_PWD is set)
    context["v3_mode"] = bool(context["pwd"])

    # If no shell integration, fall back to Python's view
    if not context["pwd"]:
        context["pwd"] = os.getcwd()

    log(f"Shell context: v3_mode={context['v3_mode']}, pwd={context['pwd']}, shell={context['shell']}")
    return context


def get_console_output_context():
    """Get recent console output context for AI"""
    if not CONSOLE_OUTPUT_ENABLED:
        log("Console output context disabled")
        return ""

    log("Getting console output context")
    output_dir = os.path.expanduser("~/.aitermy/console_outputs")

    if not os.path.exists(output_dir):
        log("Console output directory not found", "WARNING")
        return ""

    try:
        # Get all output files, sorted by modification time (newest first)
        output_files = []
        for filename in os.listdir(output_dir):
            if filename.startswith(("context_", "last_command_")):
                filepath = os.path.join(output_dir, filename)
                if os.path.isfile(filepath):
                    output_files.append((filepath, os.path.getmtime(filepath)))

        # Sort by modification time (newest first)
        output_files.sort(key=lambda x: x[1], reverse=True)

        context_parts = []
        total_tokens = 0
        max_tokens = CONSOLE_OUTPUT_MAX_TOKENS

        for filepath, _ in output_files[:CONSOLE_OUTPUT_MAX_ITEMS]:
            try:
                with open(filepath, "r") as f:
                    content = f.read()

                # Estimate tokens (rough approximation: 4 chars per token)
                content_tokens = len(content) // 4
                if total_tokens + content_tokens > max_tokens:
                    # Truncate if we would exceed limit
                    remaining_tokens = max_tokens - total_tokens
                    if remaining_tokens > 100:  # Only add if we have meaningful space
                        max_chars = remaining_tokens * 4
                        content = content[:max_chars] + "\n[...truncated...]"
                        context_parts.append(
                            f"Console Output ({os.path.basename(filepath)}):\n{content}"
                        )
                        total_tokens += remaining_tokens
                    break
                else:
                    context_parts.append(
                        f"Console Output ({os.path.basename(filepath)}):\n{content}"
                    )
                    total_tokens += content_tokens

            except Exception as e:
                log(f"Error reading console output file {filepath}: {e}", "WARNING")

        if context_parts:
            return "\n\n".join(context_parts)
        else:
            return ""

    except Exception as e:
        log(f"Error getting console output context: {e}", "ERROR")
        return ""


def get_terminal_context(lines, command_name):
    log(
        f"Getting terminal context with {lines} lines, filtering for command '{command_name}'"
    )
    # Read directly from zsh history file
    history_file = os.path.expanduser("~/.zsh_history")
    try:
        if not os.path.exists(history_file):
            log(f"History file not found: {history_file}", "WARNING")
            return "No terminal history file found."

        # Read and process the zsh history file
        with open(history_file, "r", errors="ignore") as f:
            # Read all lines and take the last 'lines' entries
            history_entries = f.readlines()

            # Take the last 'lines' entries
            history_entries = history_entries[-lines:]

            # Process the zsh history format (remove timestamps, etc.)
            processed_entries = []
            for entry in history_entries:
                # zsh history format often has timestamps like ": 1616432631:0;actual command"
                if ";" in entry and ":" in entry:
                    # Extract the command part after the last semicolon
                    command = entry.split(";", 1)[1].strip()
                    processed_entries.append(command)
                else:
                    # If the format is different, just use the raw entry
                    processed_entries.append(entry.strip())

            # Filter out the command invocation itself
            filtered_entries = [
                entry
                for entry in processed_entries
                if not entry.startswith(command_name + " ")
            ]

            log(
                f"Retrieved {len(processed_entries)} lines, filtered down to {len(filtered_entries)} lines"
            )

            if not filtered_entries:
                log("No terminal history entries found", "WARNING")
                return "No recent terminal history found."

            # Join the *filtered* entries with newlines
            terminal_output = "\n".join(filtered_entries)
            return f"Recent Terminal History:\n{terminal_output}"
    except PermissionError:
        log(f"Permission denied when accessing history file: {history_file}", "ERROR")
        return "Permission denied when accessing terminal history file."
    except UnicodeDecodeError:
        log("Unicode decode error when reading history file", "ERROR")
        return "Error decoding terminal history file."
    except Exception as e:
        log(f"Error retrieving terminal history: {e}", "ERROR")
        return f"Error retrieving terminal history: {e}"


def get_file_context(filename):
    log(f"Getting file context from {filename}")
    try:
        with open(filename, "r") as f:
            file_content = f.read()
        log(f"Read {len(file_content.splitlines())} lines from {filename}")
        return f"File Content ({filename}):\n{file_content}"
    except FileNotFoundError:
        log(f"File not found: {filename}", "ERROR")
        return f"File not found: {filename}"
    except Exception as e:
        log(f"Error reading file {filename}: {e}", "ERROR")
        return f"Error reading file {filename}: {e}"


def get_multiple_file_contexts(filenames):
    """Get context from multiple files and combine them"""
    log(f"Getting context from multiple files: {filenames}")
    all_contexts = []

    for filename in filenames:
        file_context = get_file_context(filename)
        all_contexts.append(file_context)

    return "\n\n".join(all_contexts)


def query_openrouter(messages):
    log("Sending request to OpenRouter API")
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 10000,  # Adjust as needed
    }

    try:
        response = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            data=json.dumps(data),
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log(f"API request failed: {e}", "ERROR")
        return {"error": f"API request failed: {e}"}


def extract_model_response(response):
    try:
        content = response["choices"][0]["message"]["content"]
        return content
    except (KeyError, TypeError):
        return f"Error extracting response: {response}"


def show_help():
    """Display detailed help information"""
    shell_context = get_shell_context()
    cmd = COMMAND_NAME

    help_text = f"""
# AiTermy Terminal Assistant v{VERSION}

## Quick Start
```
{cmd} "Your question here"    # Ask anything
{cmd}                         # Interactive mode
```

## Features
* **Automatic context** - AiTermy knows your current directory, recent commands, and shell
* **Conversation memory** - Follow-up questions remember previous context
* **File context** - Include files for code analysis

## Options
* `-n, --new` - Start a fresh conversation
* `-c, --continue` - Explicitly continue previous conversation
* `-f, --file <path>` - Include file content (can use multiple times)
* `-F, --files <list>` - Comma-separated list of files
* `-l, --lines <n>` - Include N lines of terminal history (legacy mode)

## Examples
```
{cmd} "What's in this directory?"           # Uses current context
{cmd} "Explain this code" -f main.py        # With file
{cmd} "Compare these" -f a.py -f b.py       # Multiple files
{cmd} -n "New topic"                        # Start fresh
{cmd} "Tell me more"                        # Follow-up
```

## Interactive Mode
Just run `{cmd}` without arguments for an interactive session with commands:
* `/help` - Show help
* `/history` - View conversation
* `/clear` - Clear conversation
* `/model` - Show current model
* `/quit` - Exit

## Configuration
* Config file: `~/.aitermy/config.toml`
* Model: {OPENROUTER_MODEL}
* Context: {'V3 shell integration active' if shell_context.get('v3_mode') else 'Legacy mode'}
"""
    console.print(Panel(Markdown(help_text), title="AiTermy Help", border_style="cyan"))


def main():
    log("Starting AiTermy main function")

    # Create argument parser
    parser = argparse.ArgumentParser(description="Terminal AI Assistant with Context")
    parser.add_argument("question", nargs="?", help="The question to ask the assistant")
    parser.add_argument(
        "-l",
        "--lines",
        type=int,
        default=argparse.SUPPRESS,
        help=f"Number of lines of terminal output to include as context (default: {DEFAULT_LINES})",
    )
    parser.add_argument(
        "-f",
        "--file",
        action="append",
        dest="files",
        help="Path to a file to include as context. Use multiple times for multiple files (e.g., -f file1.py -f file2.py)",
    )
    parser.add_argument(
        "-F",
        "--files",
        dest="files_list",
        help='Comma-separated list of files to include as context (e.g., -F "file1.py,file2.py,file3.py")',
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"AiTermy v{VERSION} using {OPENROUTER_MODEL}",
    )
    parser.add_argument(
        "-n", "--new", action="store_true", help="Start a new conversation"
    )
    parser.add_argument(
        "-c",
        "--continue",
        dest="continue_convo",
        action="store_true",
        help="Continue the previous conversation",
    )

    args = parser.parse_args()
    # Enter interactive mode if no question provided
    has_lines = hasattr(args, "lines")
    if args.question is None and not (
        has_lines or args.files or args.files_list or args.new or args.continue_convo
    ):
        log("No question provided, entering interactive mode")
        interactive_mode()
        return

    # API key validation with enhanced UI
    if not OPENROUTER_API_KEY:
        log("API key not configured", "ERROR")
        error_panel = Panel(
            f"""[red]🚫 API key not configured![/red]

[dim]To fix this:[/dim]
1. Edit [cyan]{os.path.join(os.getcwd(), ".env")}[/cyan]
2. Add: [green]OPENROUTER_API_KEY=your_api_key_here[/green]
3. Run: [yellow]source ~/.zshrc[/yellow]

[dim]Get your API key at: https://openrouter.ai/keys[/dim]""",
            title="[red]Configuration Error[/red]",
            border_style="red",
            padding=(1, 2),
        )
        console.print(error_panel)
        return

    # Validate API key format
    if not OPENROUTER_API_KEY.startswith("sk-or-"):
        log("Invalid API key format", "ERROR")
        error_panel = Panel(
            f"""[red]🚫 Invalid API key format detected.[/red]

[dim]Key must start with 'sk-or-'[/dim]

[dim]Please check your .env file at:[/dim]
[cyan]{os.path.join(os.getcwd(), ".env")}[/cyan]

[dim]Get a valid key at: https://openrouter.ai/keys[/dim]""",
            title="[red]API Key Error[/red]",
            border_style="red",
            padding=(1, 2),
        )
        console.print(error_panel)
        return

    # Combine file sources
    all_files = []
    if args.files:
        all_files.extend(args.files)

    if args.files_list:
        # Split the comma-separated list and strip whitespace
        files_from_list = [f.strip() for f in args.files_list.split(",")]
        all_files.extend(files_from_list)

    # Validate all files exist before proceeding
    missing_files = [f for f in all_files if not os.path.exists(f)]
    if missing_files:
        log(f"Files not found: {missing_files}", "ERROR")
        error_panel = Panel(
            f"""[red]📁 Files not found:[/red]
[yellow]{chr(10).join(f"• {f}" for f in missing_files)}[/yellow]

[dim]Please check the file paths and try again.[/dim]""",
            title="[red]File Error[/red]",
            border_style="red",
            padding=(1, 2),
        )
        console.print(error_panel)
        return

    # Handle conversation history
    if args.new:
        start_new_conversation()
        log("Starting new conversation as requested")

    conversation_history = (
        load_conversation_history() if (args.continue_convo or not args.new) else []
    )

    # Get shell context and build system message
    shell_context = get_shell_context()
    system_message = build_system_message(shell_context)
    log(
        f"Built system message: v3_mode={shell_context.get('v3_mode')}, pwd={shell_context.get('pwd')}"
    )

    # Initialize messages with system message if no history
    messages = []
    if not conversation_history:
        messages.append({"role": "system", "content": system_message})
    else:
        messages = conversation_history.copy()

    # Add context information to the user's question
    user_prompt = ""
    context_added = False
    console_context = ""

    # V3 mode: shell history is already in system message from shell integration
    # V2 fallback: read from history file
    if not shell_context.get("v3_mode"):
        if (hasattr(args, "lines") or not args.continue_convo) and not args.question:
            # Only add terminal context for new questions, not continuations
            lines_to_use = getattr(args, "lines", DEFAULT_LINES)
            terminal_context = get_terminal_context(lines_to_use, COMMAND_NAME)
            if "Recent Terminal History" in terminal_context:
                user_prompt += f"\n\n{terminal_context}"
                context_added = True

        # Add console output context automatically (legacy V2 mechanism)
        if CONSOLE_OUTPUT_ENABLED:
            console_context = get_console_output_context()
            if console_context:
                user_prompt += f"\n\n{console_context}"
                context_added = True
                log("Added console output context")
    else:
        # V3 mode: context is already in system message
        context_added = True
        log("Using V3 shell context (already in system message)")

    # Handle multiple files
    if all_files:
        if len(all_files) == 1:
            # Single file case, use the existing function
            file_context = get_file_context(all_files[0])
            if "File Content" in file_context:
                user_prompt += f"\n\n{file_context}"
                context_added = True
        else:
            # Multiple files case, use the new function
            file_contexts = get_multiple_file_contexts(all_files)
            if file_contexts:
                user_prompt += f"\n\n{file_contexts}"
                context_added = True
                log(f"Added context from {len(all_files)} files")

    # Add the user's question
    if args.question:
        user_prompt += f"\n\n{args.question}"
        log(f"User prompt built with question: {args.question}")

        # Add the user message to the conversation
        messages.append({"role": "user", "content": user_prompt})

        # Show a loading message
        with console.status("[bold cyan]Thinking...[/bold cyan]", spinner="dots"):
            log("Displaying 'Thinking...' status and querying OpenRouter")
            # Query OpenRouter with full conversation history
            response = query_openrouter(messages)
            answer = extract_model_response(response)

        # Only add the assistant's response to the conversation if it's not an error
        if not answer.startswith("Error extracting response:"):
            messages.append({"role": "assistant", "content": answer})

        # Keep only the last MAX_CONVERSATION_TURNS turns
        if len(messages) > 2 * MAX_CONVERSATION_TURNS + 1:  # +1 for the system message
            # Keep system message and last MAX_CONVERSATION_TURNS exchanges
            messages = [messages[0]] + messages[-(2 * MAX_CONVERSATION_TURNS) :]
            log(f"Trimmed conversation history to {len(messages)} messages")

        # Save updated conversation
        save_conversation_history(messages)

        # Display response with enhanced rich formatting
        log("Displaying answer to user")

        # Create a nice panel for the answer
        answer_panel = Panel(
            Markdown(answer),
            title="[bold blue]🤖 Answer[/bold blue]",
            border_style="blue",
            padding=(1, 2),
        )
        console.print(answer_panel)

        # Show context information that was used
        if context_added:
            context_info = []

            # V3 mode indicator
            if shell_context.get("v3_mode"):
                context_info.append(f"shell context from {shell_context.get('shell', 'shell')}")
            else:
                if hasattr(args, "lines"):
                    context_info.append(f"{args.lines} lines of terminal output")
                if CONSOLE_OUTPUT_ENABLED and console_context:
                    context_info.append("recent console outputs")

            if all_files:
                if len(all_files) == 1:
                    context_info.append(f"content from {all_files[0]}")
                else:
                    context_info.append(
                        f"content from {len(all_files)} files: {', '.join(all_files)}"
                    )

            if context_info:
                context_str = " and ".join(context_info)
                log(f"Context used: {context_str}")

                context_panel = Panel(
                    f"[dim]{context_str}[/dim]",
                    title="[dim]Context Used[/dim]",
                    border_style="dim blue",
                    padding=(0, 1),
                )
                console.print(context_panel)

        # Show conversation status
        conversation_turns = (
            len(messages) - 1
        ) // 2  # Subtract system message, divide by 2 (user+assistant)

        status_info = f"💬 {conversation_turns} turns"
        if conversation_turns > 0:
            status_info += f' | 🔄 Continue: `{COMMAND_NAME} "follow-up"`'
            status_info += f' | 🆕 New: `{COMMAND_NAME} -n "question"`'

        status_panel = Panel(
            f"[dim]{status_info}[/dim]", border_style="dim cyan", padding=(0, 1)
        )
        console.print(status_panel)

    log("AiTermy execution completed successfully")


if __name__ == "__main__":
    main()
