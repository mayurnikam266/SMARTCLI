import sys
import os
import yaml
import subprocess
import re
import importlib
import json
from pathlib import Path
import platform
import shutil

# --- Constants & Setup ---
# Attempt to import readline for better input experience on Unix-like systems
try:
    import readline
except ImportError:
    readline = None # This will be None on Windows

# Attempt to import colorama for colored terminal output
try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    print("⚠️  Please install 'colorama' for a better experience: pip install colorama")
    class Fore:
        GREEN = RED = YELLOW = CYAN = MAGENTA = BLUE = ""
    class Style:
        BRIGHT = ""

# Attempt to import questionary for interactive prompts
try:
    import questionary
except ImportError:
    print("⚠️  Please install 'questionary': pip install questionary")
    questionary = None

# --- Global Variables ---
file_session_data = {}
main_history_log = []
SETUP_SCRIPT_PATH = Path(__file__).parent / "setup_llm.py"
LLM_ENGINES_DIR = Path(__file__).parent / "llm_engines"


def is_valid_config(config):
    """Checks if the loaded configuration has all the required keys."""
    if not isinstance(config, dict):
        return False
    required_keys = ["llm_provider", "api_key", "model"]
    return all(config.get(key) for key in required_keys)

def load_config():
    """Loads the config.yaml file, running setup if it's missing or invalid."""
    config_file = Path("config.yaml")

    if not config_file.exists():
        print(Fore.RED + "❌ Config file not found. Launching setup...")
        subprocess.run([sys.executable, str(SETUP_SCRIPT_PATH)], check=True)
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        if not is_valid_config(config):
            print(Fore.RED + "❌ Incomplete or invalid config file. Launching setup...")
            subprocess.run([sys.executable, str(SETUP_SCRIPT_PATH)], check=True)

    # Reload the config after a potential setup run
    with open(config_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_total_tokens(history):
    """Calculates the total number of tokens in a conversation history."""
    return sum(len(str(m.get("content", "")).split()) for m in history)

def clear_memory():
    """Clears the main history log and file session data."""
    global main_history_log, file_session_data
    main_history_log = []
    file_session_data = {}
    print(Fore.YELLOW + "🧠 Memory and file context have been cleared.")

def select_and_load_files():
    """Uses questionary to let the user select files to load into context."""
    if not questionary:
        print(Fore.RED + "❌ 'questionary' is not installed. File selection is disabled.")
        return {}
    
    files = [str(p) for p in Path('.').rglob("*") if p.is_file() and not p.name.startswith('.')]
    if not files:
        print(Fore.YELLOW + "No files were found in the current directory.")
        return {}
        
    selected = questionary.checkbox("📂 Select files to include in the context:", choices=files).ask()
    
    data = {}
    for f in selected or []:
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                data[f] = fp.read()
        except Exception as e:
            data[f] = f"⚠️ Could not read file: {f}. Error: {e}"
    return data

def get_llm_response(prompt, config, history=None):
    """Sends a prompt to the configured LLM and returns the response."""
    provider = config.get("llm_provider")
    if not provider:
        return "LLM provider is not configured in config.yaml."

    if not LLM_ENGINES_DIR.exists() or not LLM_ENGINES_DIR.is_dir():
        return f"Error: The 'llm_engines' directory is missing."
    
    engine_file = LLM_ENGINES_DIR / f"{provider}_llm.py"
    if not engine_file.exists():
        return f"Error: The engine file '{engine_file.name}' was not found in the 'llm_engines' directory."

    try:
        # Dynamically import the correct engine module based on config
        engine_module = importlib.import_module(f"llm_engines.{provider}_llm")

        # --- CONTEXT ADAPTER LOGIC ---
        # This section adapts the call to fit your engines' expected signature.
        # It constructs the full context, including the system prompt and history.
        os_name = platform.system()
        system_prompt_content = (
            f"You are a helpful CLI assistant running on a {os_name} operating system. "
            "Always answer clearly and concisely. Provide commands compatible with this OS. "
            "If file context is needed for a task, respond with: 'Please provide the files required for this task.'"
        )
        
        # The 'history' now includes the system prompt plus the conversational history.
        full_history = [{"role": "system", "content": system_prompt_content}]
        if history:
            full_history.extend(history)
        
        # The 'prompt' is the current user input.
        current_prompt = prompt
        
        # Call the engine with the arguments it expects: (prompt, config, history)
        return engine_module.get_response(prompt=current_prompt, config=config, history=full_history)

    except ImportError as e:
        return f"Import Error: Failed to import '{provider}_llm'. Please check the file for syntax errors. Details: {e}"
    except AttributeError:
        return f"Attribute Error: The engine file '{engine_file.name}' must contain a function named 'get_response'."
    except TypeError as e:
        # This error message is now less likely to occur, but is kept for safety.
        return f"Type Error in engine '{engine_file.name}': The 'get_response' function was called with the wrong arguments. Details: {e}"
    except Exception as e:
        return f"An unexpected error occurred with the LLM engine: {e}"

def format_command_prompt(query):
    """Formats the user's query into a detailed prompt for the LLM."""
    os_name = platform.system()
    prompt = f"""
You are an expert DevOps assistant. Your task is to convert a user's request into a precise shell command.
The user is running on a {os_name} operating system. All commands MUST be compatible with {os_name}.
If the command requires project files (e.g., for building a Docker image), ask the user for them.
Respond ONLY in the following strict JSON format. Do not add any other text, comments, or markdown.
The command must be a single-line string with proper escaping for complex operations like file creation.

{{
  "response": "A brief, one-sentence explanation of what the command does.",
  "command": "The single, exact shell command to execute."
}}

User Query: "{query}"
""".strip()
    
    if file_session_data:
        prompt += "\n\n# Project Files Context:\n"
        for name, content in file_session_data.items():
            prompt += f"\n## File: {name}\n{content[:1000]}\n"
    return prompt

def extract_command_and_response(llm_output):
    """Extracts the command and explanation from the LLM's JSON response."""
    try:
        json_match = re.search(r"\{.*\}", llm_output, re.DOTALL)
        if not json_match:
            return None, None
        
        parsed = json.loads(json_match.group(0))
        return parsed.get("command", "").strip(), parsed.get("response", "").strip()
    except Exception as e:
        print(Fore.RED + f"❌ Error: Failed to parse command from LLM response. Details: {e}")
        return None, None

def execute_command(cmd):
    """Executes a shell command using the OS's default interpreter and prints the output."""
    print(Fore.CYAN + f"📤 Executing: {cmd}")
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            check=False, encoding='utf-8', errors='replace'
        )
        if result.stdout:
            print(Fore.GREEN + f"🖥️  Output:\n{result.stdout.strip()}")
        if result.stderr:
            print(Fore.RED + f"❗ Error Output:\n{result.stderr.strip()}")
        return result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        err_msg = f"💥 Critical error executing command: {e}"
        print(Fore.RED + err_msg)
        return "", str(e)

def input_with_prefill(prompt_text, default_text):
    """Provides an input prompt with pre-filled text for editing."""
    if readline:
        def hook():
            readline.insert_text(default_text)
            readline.redisplay()
        
        readline.set_startup_hook(hook)
        try:
            return input(prompt_text)
        finally:
            readline.set_startup_hook(None)
    else:
        print(f"\nSuggested command: {default_text}")
        return input(f"{prompt_text} (Edit and press Enter): ")

def enter_chat_mode(config):
    """Enters a conversational chat mode with the LLM."""
    print(Fore.CYAN + "\n🤖 Entering Interactive Chat Mode.")
    print(Fore.CYAN + "Type 'exit' or 'back' to return to the main terminal.\n")
    chat_history = []
    
    while True:
        try:
            chat_input = input(Fore.GREEN + "You: ").strip()
            if not chat_input:
                continue
            if chat_input.lower() in ["exit", "back"]:
                print(Fore.YELLOW + "Exiting Chat Mode...\n")
                break
            
            if get_total_tokens(chat_history) > 3500:
                print(Fore.YELLOW + "⚠️  Conversation history is long. For best results, consider clearing memory.")
            
            print(Fore.YELLOW + "🧠 Thinking...")
            response = get_llm_response(chat_input, config, history=chat_history)
            
            chat_history.append({"role": "user", "content": chat_input})
            chat_history.append({"role": "assistant", "content": response})
            
            print(Fore.BLUE + f"LLM: {response}\n")
        except Exception as e:
            print(Fore.RED + f"An error occurred during the chat session: {e}")

def print_help():
    """Prints the help message with all available commands."""
    print(Fore.GREEN + "\n🤖 SmartCLI Help & Commands 🤖")
    print("--------------------------------")
    print(f"{Style.BRIGHT}`scli-command <query>`{Style.NORMAL} - Request a shell command from the LLM.")
    print(f"{Style.BRIGHT}`scli-chat`{Style.NORMAL}            - Start an interactive chat session with the LLM.")
    print(f"{Style.BRIGHT}`scli-files`{Style.NORMAL}           - Select project files to add to the LLM's context.")
    print(f"{Style.BRIGHT}`scli-clear`{Style.NORMAL}           - Clear the conversation history and all file context.")
    print(f"{Style.BRIGHT}`scli-configure`{Style.NORMAL}       - Re-run the initial setup to change LLM providers.")
    print(f"{Style.BRIGHT}`help` or `scli`{Style.NORMAL}         - Display this help message.")
    print(f"{Style.BRIGHT}`exit` or `scli-exit`{Style.NORMAL}    - Exit the SmartCLI application.")
    print("\nAny other input is executed as a direct shell command.")

def process_llm_query(query, config):
    """Processes a user's query to the LLM to get a shell command."""
    global main_history_log, file_session_data
    print(Fore.YELLOW + f"🧠 Querying LLM with: \"{query}\"\n")

    if not file_session_data:
        ask = input("📁 No files are loaded in context. Select files now? (y/N): ").strip().lower()
        if ask == 'y':
            file_session_data.update(select_and_load_files())
            
    formatted_prompt = format_command_prompt(query)
    llm_response = get_llm_response(formatted_prompt, config)
    main_history_log.append({"role": "assistant", "content": llm_response})
    
    command, explanation = extract_command_and_response(llm_response)
    
    if not command:
        print(Fore.RED + "⚠️ LLM did not return a valid command.")
        print(f"Raw response: {llm_response}")
        return

    print(Fore.CYAN + f"💡 LLM Explanation: {explanation}")
    print(Fore.MAGENTA + Style.BRIGHT + f"✨ Suggested Command: {command}\n")
    
    prompt_text = (
        "❓ Select an action:\n"
        "   y  - (yes) Run the command as is.\n"
        "   yy - (analyze) Run, then send output to LLM for analysis.\n"
        "   c  - (custom) Edit the command before running.\n"
        "   n  - (no) Skip this command.\n"
        ">>> "
    )
    action = input(prompt_text).lower().strip()

    if action == 'y':
        execute_command(command)
    elif action == 'yy':
        output, error = execute_command(command)
        analysis_prompt = f"""
As an expert DevOps and programming troubleshooter, please analyze the following execution on {platform.system()}.
If there are errors, provide a concise analysis and suggest solutions. If successful, briefly confirm it.

Command: `{command}`
Standard Output:\n{output}
Standard Error:\n{error}
""".strip()
        print(Fore.YELLOW + "\n🧠 Sending execution output to LLM for analysis...")
        analysis_response = get_llm_response(analysis_prompt, config)
        print(Fore.BLUE + "\n🕵️ LLM Analysis:\n" + analysis_response)
    elif action == 'c':
        edited_cmd = input_with_prefill("✍️ Edit command: ", command).strip()
        if edited_cmd:
            execute_command(edited_cmd)
        else:
            print(Fore.YELLOW + "❌ Command edit cancelled.")
    else:
        print(Fore.YELLOW + "❌ Command skipped by user.\n")

def main():
    """The main entry point and command loop for the SmartCLI application."""
    try:
        config = load_config()
    except Exception as e:
        print(Fore.RED + f"CRITICAL ERROR: Could not load configuration. Please check your setup. Details: {e}")
        sys.exit(1)

    print_help()
    
    global main_history_log
    
    while True:
        try:
            user_input = input("scli> ").strip()
            if not user_input:
                continue

            if user_input.lower() in ["exit", "scli-exit"]:
                print("👋 Exiting SmartCLI.")
                break
            elif user_input.lower() in ["help", "scli"]:
                print_help()
            elif user_input == "scli-clear":
                clear_memory()
            elif user_input.startswith("scli-chat"):
                enter_chat_mode(config)
            elif user_input == "scli-configure":
                subprocess.run([sys.executable, str(SETUP_SCRIPT_PATH)], check=True)
                config = load_config()
            elif user_input == "scli-files":
                file_session_data.clear()
                file_session_data.update(select_and_load_files())
                print(Fore.GREEN + f"📁 Context updated. {len(file_session_data)} files are now loaded.\n")
            elif user_input.startswith("scli-command"):
                query = user_input[len("scli-command"):].strip()
                if not query:
                    print(Fore.RED + "⚠️ Please provide a query. Example: scli-command list all docker containers")
                else:
                    main_history_log.append({"role": "user", "content": query})
                    process_llm_query(query, config)
            else:
                execute_command(user_input)
                
        except KeyboardInterrupt:
            print("\n👋 Exiting SmartCLI.")
            break
        except Exception as e:
            print(Fore.RED + f"An unexpected error occurred in the main loop: {e}")

if __name__ == "__main__":
    main()
