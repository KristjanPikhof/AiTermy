#!/usr/bin/env python3
import subprocess
import os
import requests
import json
import sys
import argparse
import logging
import datetime
import pathlib
import pickle
import re
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Confirm

# Version information
VERSION = "1.1.0"

# Load environment variables from .env file
load_dotenv()

# OpenRouter info
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")  # Default model
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_LINES = 10

# Command Name (set during setup)
COMMAND_NAME = os.environ.get("COMMAND_NAME", "aitermy") # Default if not set

# Conversation history configuration
CONVERSATION_DIR = os.path.expanduser("~/.aitermy/conversations")
CURRENT_CONVERSATION_FILE = os.path.join(CONVERSATION_DIR, "current_conversation.pkl")
MAX_CONVERSATION_TURNS = 10  # Maximum number of turns to keep in history

# Logging configuration
LOGGING_ENABLED = os.environ.get("LOGGING_ENABLED", "false").lower() == "true"
LOG_FILE = os.environ.get("LOG_FILE", "~/.aitermy/logs/aitermy.log")
LOG_FILE = os.path.expanduser(LOG_FILE)

# Setup logging if enabled
if LOGGING_ENABLED:
    # Create log directory if it doesn't exist
    log_dir = os.path.dirname(LOG_FILE)
    pathlib.Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
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

def load_conversation_history():
    """Load the current conversation history if it exists"""
    try:
        if os.path.exists(CURRENT_CONVERSATION_FILE):
            with open(CURRENT_CONVERSATION_FILE, 'rb') as f:
                history = pickle.load(f)
                log(f"Loaded conversation history with {len(history)} messages")
                return history
    except Exception as e:
        log(f"Error loading conversation history: {e}", "ERROR")
    return []  # Return empty history if file doesn't exist or on error

def save_conversation_history(history):
    """Save the current conversation history"""
    try:
        with open(CURRENT_CONVERSATION_FILE, 'wb') as f:
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

def get_terminal_context(lines, command_name):
    log(f"Getting terminal context with {lines} lines, filtering for command '{command_name}'")
    try:
        # Read directly from zsh history file
        history_file = os.path.expanduser("~/.zsh_history")
        
        if not os.path.exists(history_file):
            log(f"History file not found: {history_file}", "WARNING")
            return "No terminal history file found."
        
        # Read and process the zsh history file
        with open(history_file, 'r', errors='ignore') as f:
            # Read all lines and take the last 'lines' entries
            history_entries = f.readlines()
            
            # Take the last 'lines' entries
            history_entries = history_entries[-lines:]
            
            # Process the zsh history format (remove timestamps, etc.)
            processed_entries = []
            for entry in history_entries:
                # zsh history format often has timestamps like ": 1616432631:0;actual command"
                if ';' in entry and ':' in entry:
                    # Extract the command part after the last semicolon
                    command = entry.split(';', 1)[1].strip()
                    processed_entries.append(command)
                else:
                    # If the format is different, just use the raw entry
                    processed_entries.append(entry.strip())
            
            # Filter out the command invocation itself
            filtered_entries = [entry for entry in processed_entries if not entry.startswith(command_name + " ")]

            log(f"Retrieved {len(processed_entries)} lines, filtered down to {len(filtered_entries)} lines")
            
            if not filtered_entries:
                log("No terminal history entries found", "WARNING")
                return "No recent terminal history found."
            
            # Join the *filtered* entries with newlines
            terminal_output = '\n'.join(filtered_entries)
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
        with open(filename, 'r') as f:
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
        "Content-Type": "application/json"
    }

    data = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 10000 # Adjust as needed
    }

    log(f"Request data: model={OPENROUTER_MODEL}, temperature=0.7, max_tokens=1000, messages_count={len(messages)}")
    
    try:
        log("Sending POST request to OpenRouter API")
        response = requests.post(f"{OPENROUTER_BASE_URL}/chat/completions", headers=headers, data=json.dumps(data))
        response.raise_for_status()
        log("Received successful response from OpenRouter API")
        return response.json()
    except requests.exceptions.RequestException as e:
        log(f"API request failed: {e}", "ERROR")
        return {"error": f"API request failed: {e}"}

def extract_model_response(response):
    log("Extracting model response")
    try:
        content = response["choices"][0]["message"]["content"]
        log(f"Successfully extracted response ({len(content)} characters)")
        return content
    except (KeyError, TypeError):
        log(f"Error extracting response: {response}", "ERROR")
        return f"Error extracting response: {response}"

def show_help():
    """Display detailed help information"""
    help_text = f"""
# AiTermy Terminal Assistant v{VERSION}

## Basic Usage
```
termy "Your question here"
```

## Options
* `-l, --lines <number>` - Include recent terminal output as context (default: {DEFAULT_LINES} lines)
* `-f, --file <filename>` - Include file content as context
  * For a single file: `-f filename.py`
  * For multiple files: `-f file1.py -f file2.py -f file3.py`
* `-F, --files <list>` - Alternative way to include multiple files using a comma-separated list
  * Example: `-F "main.js,utils.js,config.js"`

## File Usage Examples
```
# Single file
termy "Explain this code" -f app.js

# Multiple files using repeated -f
termy "Compare these implementations" -f file1.py -f file2.py

# Multiple files using comma-separated list
termy "Find bugs in these components" -F "header.jsx,sidebar.jsx,footer.jsx"
```

## Conversation Behavior
* By default, `termy "question"` continues your previous conversation
* Use `-n` to start a new conversation when needed
* Use `-c` when you want to explicitly mark a question as continuing the conversation
* Conversation history is stored in `~/.aitermy/conversations/`

## More Examples
```
termy "What does this error mean?" -l 20
termy "How to fix this bug?" -l 10 -f error.log
termy -n "Let's discuss a new topic"
termy "Can you tell me more about that?" # Continues conversation by default
```

## Current Configuration
* Model: {OPENROUTER_MODEL}
* API: OpenRouter

## Tips
* For code-related questions, include the relevant file with -f
* For error analysis, include terminal output with -l
* For code comparison or complex projects, use multiple files
* Conversations are maintained automatically between commands
"""
    console.print(Panel(Markdown(help_text), title="AiTermy Help", border_style="cyan"))

def main():
    log("Starting AiTermy main function")
    
    # Create argument parser
    parser = argparse.ArgumentParser(description="Terminal AI Assistant with Context")
    parser.add_argument("question", nargs='?', help="The question to ask the assistant")
    parser.add_argument("-l", "--lines", type=int, default=DEFAULT_LINES, 
                        help=f"Number of lines of terminal output to include as context (default: {DEFAULT_LINES})")
    parser.add_argument("-f", "--file", action='append', dest='files',
                        help="Path to a file to include as context. Use multiple times for multiple files (e.g., -f file1.py -f file2.py)")
    parser.add_argument("-F", "--files", dest='files_list', 
                        help="Comma-separated list of files to include as context (e.g., -F \"file1.py,file2.py,file3.py\")")
    parser.add_argument("-v", "--version", action='version', 
                        version=f'AiTermy v{VERSION} using {OPENROUTER_MODEL}')
    parser.add_argument("-n", "--new", action='store_true', help="Start a new conversation")
    parser.add_argument("-c", "--continue", dest='continue_convo', action='store_true', 
                        help="Continue the previous conversation")
    
    args = parser.parse_args()
    log(f"Parsed arguments: question={args.question}, lines={args.lines}, files={args.files}, files_list={args.files_list}, new={args.new}, continue={args.continue_convo}")

    # Show detailed help if no arguments or with -h
    if args.question is None and not (args.lines or args.files or args.files_list or args.new or args.continue_convo):
        log("No question provided, showing help")
        show_help()
        return
    
    # API key validation
    if not OPENROUTER_API_KEY:
        log("API key not configured", "ERROR")
        console.print(Panel(
            Text.from_markup(f"""[red]Error: API key not configured![/red]

1. Edit {os.path.join(os.getcwd(), '.env')}
2. Add: OPENROUTER_API_KEY=your_api_key_here
3. Run: source ~/.zshrc"""),
            title="Configuration Error",
            border_style="red"
        ))
        return

    # Validate API key format
    if not OPENROUTER_API_KEY.startswith("sk-or-"):
        log("Invalid API key format", "ERROR")
        console.print(Panel(
            Text.from_markup(f"""[red]Invalid API key format detected.[/red]
Key must start with 'sk-or-'

Please check your .env file at:
{os.path.join(os.getcwd(), '.env')}"""),
            title="API Key Error",
            border_style="red"
        ))
        return
    
    # Combine file sources
    all_files = []
    if args.files:
        all_files.extend(args.files)
    
    if args.files_list:
        # Split the comma-separated list and strip whitespace
        files_from_list = [f.strip() for f in args.files_list.split(',')]
        all_files.extend(files_from_list)
    
    # Validate all files exist before proceeding
    missing_files = [f for f in all_files if not os.path.exists(f)]
    if missing_files:
        log(f"Files not found: {missing_files}", "ERROR")
        console.print(Panel(
            Text.from_markup(f"[red]Files not found:[/red] {', '.join(missing_files)}"),
            title="File Error",
            border_style="red"
        ))
        return

    # Handle conversation history
    if args.new:
        start_new_conversation()
        log("Starting new conversation as requested")
    
    conversation_history = load_conversation_history() if (args.continue_convo or not args.new) else []
    
    # Build the system message
    os_type = "macOS" if sys.platform == "darwin" else "Linux"
    system_message = f"You are a helpful terminal assistant. You are running on {os_type}. Current location is {os.getcwd()}. "
    system_message += "Provide concise, direct answers suitable for terminal output. Use Markdown formatting where appropriate (like code blocks), but avoid overly long paragraphs. Focus directly on the user's question."
    log(f"Building system message with OS type: {os_type}, current directory: {os.getcwd()}, and conciseness instructions")
    
    # Initialize messages with system message if no history
    messages = []
    if not conversation_history:
        messages.append({"role": "system", "content": system_message})
    else:
        messages = conversation_history.copy()
    
    # Add context information to the user's question
    user_prompt = ""
    context_added = False
    
    if args.lines is not None and not args.continue_convo:
        # Only add terminal context for new questions, not continuations
        terminal_context = get_terminal_context(args.lines, COMMAND_NAME)
        if "Recent Terminal History" in terminal_context:
            user_prompt += f"\n\n{terminal_context}"
            context_added = True
    
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

        # Add the assistant's response to the conversation
        messages.append({"role": "assistant", "content": answer})
        
        # Keep only the last MAX_CONVERSATION_TURNS turns
        if len(messages) > 2 * MAX_CONVERSATION_TURNS + 1:  # +1 for the system message
            # Keep system message and last MAX_CONVERSATION_TURNS exchanges
            messages = [messages[0]] + messages[-(2 * MAX_CONVERSATION_TURNS):]
            log(f"Trimmed conversation history to {len(messages)} messages")
        
        # Save updated conversation
        save_conversation_history(messages)

        # Display response with rich
        log("Displaying answer to user")
        console.print("\n[bold cyan]Answer:[/bold cyan]\n")
        console.print(Markdown(answer))  # Use Markdown for formatted output
        
        # Show context information that was used
        if context_added:
            context_info = []
            if args.lines is not None:
                context_info.append(f"{args.lines} lines of terminal output")
            if all_files:
                if len(all_files) == 1:
                    context_info.append(f"content from {all_files[0]}")
                else:
                    context_info.append(f"content from {len(all_files)} files: {', '.join(all_files)}")
            
            context_str = " and ".join(context_info)
            log(f"Context used: {context_str}")
            console.print(f"\n[dim]Context used: {context_str}[/dim]")
        
        # Ask if user wants to continue the conversation
        conversation_turns = (len(messages) - 1) // 2  # Subtract system message, divide by 2 (user+assistant)
        console.print(f"\n[dim]Conversation active: {conversation_turns} turns so far[/dim]")
        console.print(f"[dim]Type `{COMMAND_NAME} \"your follow-up question\"` to continue this conversation (default behavior)[/dim]")
        console.print(f"[dim]Type `{COMMAND_NAME} -n \"new question\"` to start a new conversation[/dim]")
        
    log("AiTermy execution completed successfully")

if __name__ == "__main__":
    main()
