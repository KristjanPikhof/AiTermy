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
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

# Version information
VERSION = "1.0.2"

# Load environment variables from .env file
load_dotenv()

# OpenRouter info
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")  # Default model
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_LINES = 10

# Command Name (set during setup)
COMMAND_NAME = os.environ.get("COMMAND_NAME", "aitermy") # Default if not set

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

def query_openrouter(prompt):
    log("Sending request to OpenRouter API")
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 1000 # Adjust as needed
    }

    log(f"Request data: model={OPENROUTER_MODEL}, temperature=0.7, max_tokens=1000")
    
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
* `-h, --help` - Show this help message
* `-v, --version` - Show version information

## Examples
```
termy "What does this error mean?" -l 20
termy "Explain this code" -f app.js
termy "How to fix this bug?" -l 10 -f error.log
```

## Current Configuration
* Model: {OPENROUTER_MODEL}
* API: OpenRouter

## Tips
* For code-related questions, include the relevant file with -f
* For error analysis, include terminal output with -l
* You can combine both -l and -f for more context
"""
    console.print(Panel(Markdown(help_text), title="AiTermy Help", border_style="cyan"))

def main():
    log("Starting AiTermy main function")
    
    # Create argument parser
    parser = argparse.ArgumentParser(description="Terminal AI Assistant with Context")
    parser.add_argument("question", nargs='?', help="The question to ask the assistant")
    parser.add_argument("-l", "--lines", type=int, default=DEFAULT_LINES, 
                        help=f"Number of lines of terminal output to include as context (default: {DEFAULT_LINES})")
    parser.add_argument("-f", "--file", type=str, help="Path to a file to include as context")
    parser.add_argument("-v", "--version", action='version', 
                        version=f'AiTermy v{VERSION} using {OPENROUTER_MODEL}')
    
    args = parser.parse_args()
    log(f"Parsed arguments: question={args.question}, lines={args.lines}, file={args.file}")

    # Show detailed help if no arguments or with -h
    if args.question is None and not (args.lines or args.file):
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
    
    # File existence check
    if args.file and not os.path.exists(args.file):
        log(f"File not found: {args.file}", "ERROR")
        console.print(Panel(
            Text.from_markup(f"[red]File not found:[/red] {args.file}"),
            title="File Error",
            border_style="red"
        ))
        return

    # Build the prompt
    os_type = "macOS" if sys.platform == "darwin" else "Linux"
    prompt = f"You are a helpful terminal assistant. You are running on {os_type}. Current location is {os.getcwd()}. " 
    log(f"Building prompt with OS type: {os_type}, current directory: {os.getcwd()}")
    
    # Add context information
    context_added = False
    
    if args.lines is not None:
        # Pass the loaded COMMAND_NAME here
        terminal_context = get_terminal_context(args.lines, COMMAND_NAME)
        if "Recent Terminal History" in terminal_context:
            prompt += f"\n\n{terminal_context}"
            context_added = True
    
    if args.file:
        file_context = get_file_context(args.file)
        if "File Content" in file_context:
            prompt += f"\n\n{file_context}"
            context_added = True
    
    # Add the user's question
    prompt += f"\n\nQuestion: {args.question}"
    log(f"Final prompt built with question: {args.question}")
    
    # Show a loading message
    with console.status("[bold cyan]Thinking...[/bold cyan]", spinner="dots"):
        log("Displaying 'Thinking...' status and querying OpenRouter")
        # Query OpenRouter
        response = query_openrouter(prompt)
        answer = extract_model_response(response)

    # Display response with rich
    log("Displaying answer to user")
    console.print("\n[bold cyan]Answer:[/bold cyan]\n")
    console.print(Markdown(answer))  # Use Markdown for formatted output
    
    # Show context information that was used
    if context_added:
        context_info = []
        if args.lines is not None:
            context_info.append(f"{args.lines} lines of terminal output")
        if args.file:
            context_info.append(f"content from {args.file}")
        
        context_str = " and ".join(context_info)
        log(f"Context used: {context_str}")
        console.print(f"\n[dim]Context used: {context_str}[/dim]")
    
    log("AiTermy execution completed successfully")

if __name__ == "__main__":
    main()
