
import os
import yaml
import subprocess
import re
import importlib
import json
from pathlib import Path
try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    print("⚠️ Please install 'colorama' with: pip install colorama")
    exit(1)
try:
    import readline
except ImportError:
    readline = None

# Load configuration
def load_config():
    config_file = Path("config.yaml")
    if not config_file.exists():
        print(Fore.RED + "❌ Config file not found. Please run setup.py first.")
        exit(1)
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)

# Chat memory
chat_history = []

def get_total_tokens():
    return sum(len(m["content"].split()) for m in chat_history)

def clear_memory():
    global chat_history
    chat_history = []
    print(Fore.GREEN + "🧠 Chat memory cleared.\n")

# Execute command with feedback
def execute_with_feedback(cmd):
    print(Fore.BLUE + f"📤 Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    output = result.stdout.strip() or result.stderr.strip()
    print(Fore.BLUE + f"📥 Output:\n{output}")
    return output, result.returncode

# Check if a command is installed
def check_command_installed(command):
    cmd = f"which {command}"
    output, returncode = execute_with_feedback(cmd)
    return returncode == 0

# Request permission for operations
def request_permission(action, target):
    print(Fore.YELLOW + f"⚠️ Permission required to {action}: {target}")
    confirm = input("Allow? (y/N): ").lower()
    return confirm == "y"

# Extract *** prompt ***
def extract_prompt(user_input):
    pattern = r"\*{3}\s*(.*?)\s*\*{3}"
    match = re.search(pattern, user_input)
    return match.group(1).strip() if match else None

# Prompt Engineering
def format_prompt(query, context=""):
    return f"""
You are a DevOps assistant. Respond in this exact JSON format:

{{
  "response": "Brief explanation of what the command will do or next question to ask.",
  "command": "ONLY the exact shell command without explanation, or empty string if asking a question",
  "next_question": "Follow-up question to gather more info, or empty string if no question needed"
}}

⚠️ RULES:
- Respond only in JSON.
- No markdown or text outside JSON.
- If more info is needed (e.g., file permissions, system state), set 'command' to empty and provide 'next_question'.
- Use context to inform responses: {context}
- Only one shell command, one line.
- For tasks like creating a Dockerfile, ask for permissions or details step-by-step.

Query: "{query}"
""".strip()

# Extract JSON response
def extract_command_and_response(llm_output):
    try:
        json_match = re.search(r"\{.*\"next_question\"\s*:\s*.*\}", llm_output, re.DOTALL)
        if not json_match:
            return None, None, None

        json_text = json_match.group(0)
        parsed = json.loads(json_text)
        command = parsed.get("command", "").strip()
        explanation = parsed.get("response", "").strip()
        next_question = parsed.get("next_question", "").strip()
        return command, explanation, next_question

    except Exception as e:
        print(Fore.RED + f"❌ JSON parse failed: {e}")
        return None, None, None

def get_llm_response(prompt, config):
    provider = config.get("llm_provider")
    try:
        engine_module = importlib.import_module(f"llm_engines.{provider}_llm")
        return engine_module.get_response(prompt, config)
    except Exception as e:
        return f"LLM error: {e}"

# Pre-fill terminal input with editable default
def input_with_prefill(prompt_text, default_text):
    if readline:
        readline.set_startup_hook(lambda: readline.insert_text(default_text))
        try:
            return input(Fore.YELLOW + prompt_text)
        finally:
            readline.set_startup_hook(None)
    else:
        print(Fore.YELLOW + "⚠️ Pre-filled editing not supported on this OS.")
        return input(Fore.YELLOW + f"{prompt_text} (type manually): ")

# Process task-specific logic
def process_task(query, config):
    context = " ".join([m["content"] for m in chat_history[-5:]])  # Last 5 messages for context
    raw_prompt = format_prompt(query, context)
    response = get_llm_response(raw_prompt, config)
    chat_history.append({"role": "assistant", "content": response})
    return extract_command_and_response(response)

# Main Loop
def main():
    config = load_config()
    print(Fore.GREEN + "🤖 Smart Terminal Assistant Ready (type 'exit' to quit)\n")

    global chat_history
    pending_task = None

    while True:
        if pending_task:
            user_input = input_with_prefill(f"❓ {pending_task}: ", "")
        else:
            user_input = input(Fore.WHITE + ">>> ").strip()

        if user_input.lower() == "exit":
            break

        if user_input.lower() == "[%clear%]":
            clear_memory()
            pending_task = None
            continue

        query = extract_prompt(user_input) or user_input
        chat_history.append({"role": "user", "content": query})

        if get_total_tokens() > 3500:
            print(Fore.YELLOW + "⚠️ Context memory full. Use [%clear%] to reset.\n")
            continue

        print(Fore.YELLOW + f"🧠 Querying: {query}\n")

        # Task-specific checks
        if "docker" in query.lower():
            if not check_command_installed("docker"):
                print(Fore.RED + "⚠️ Docker is not installed.")
                confirm = input("Install Docker? (y/N): ").lower()
                if confirm == "y":
                    command = "sudo apt-get update && sudo apt-get install -y docker.io"
                    execute_with_feedback(command)
                else:
                    print(Fore.RED + "❌ Docker not installed. Skipping task.\n")
                    continue

        if "create dockerfile" in query.lower():
            if not request_permission("list files in current directory", os.getcwd()):
                print(Fore.RED + "❌ Permission denied. Cannot proceed.\n")
                continue
            output, _ = execute_with_feedback("ls")
            files = output.split("\n")
            print(Fore.CYAN + f"📂 Found files: {', '.join(files)}")
            if not request_permission("read contents of files", os.getcwd()):
                print(Fore.RED + "❌ Permission denied. Cannot proceed.\n")
                continue

        command, explanation, next_question = process_task(query, config)

        if next_question:
            print(Fore.CYAN + f"🤖 {explanation}")
            print(Fore.YELLOW + f"❓ {next_question}")
            pending_task = next_question
            continue

        if command:
            print(Fore.CYAN + f"💡 Explanation: {explanation}")
            print(Fore.MAGENTA + Style.BRIGHT + f"💡 Suggested Command: {command}\n")
            confirm = input(Fore.YELLOW + "⚠️ Run this command? (y/N/c for custom): ").lower()

            if confirm == "y":
                execute_with_feedback(command)
            elif confirm == "c":
                edited_cmd = input_with_prefill("✍️ Edit command: ", command).strip()
                if edited_cmd:
                    execute_with_feedback(edited_cmd)
                else:
                    print(Fore.RED + "❌ No command entered. Skipped.\n")
            else:
                print(Fore.RED + "❌ Skipped.\n")
        else:
            print(Fore.RED + "⚠️ Could not extract a valid command from LLM response.\n")

        pending_task = None

# Run Main
if __name__ == "__main__":
    main()