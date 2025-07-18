import os
import yaml
import subprocess
import re
import importlib
import json
from pathlib import Path

# Try to import readline for pre-filled editable input
try:
    import readline
except ImportError:
    readline = None

# Terminal colors
try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    print("⚠️ Please install 'colorama' with: pip install colorama")
    exit(1)

#  Load configuration
def load_config():
    config_file = Path("config.yaml")
    if not config_file.exists():
        print("❌ Config file not found. Please run setup.py first.")
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
    print("🧠 Chat memory cleared.\n")

#  Execute command with feedback
def execute_with_feedback(cmd):
    print(f"📤 Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(f"📥 Output:\n{result.stdout.strip()}")
    return result.stdout.strip()

#  Match `*** prompt ***`
def extract_prompt(user_input):
    pattern = r"\*{3}\s*(.*?)\s*\*{3}"
    match = re.search(pattern, user_input)
    return match.group(1).strip() if match else None

#  Prompt Engineering
def format_prompt(query):
    return f"""
You are a DevOps assistant. Respond in this exact JSON format:

{{
  "response": "Brief explanation of what the command will do.",
  "command": "ONLY the exact shell command without any explanation or extra output."
}}

⚠️ RULES:
- write response and suggestion in short only in JSON.
- No markdown, no text outside.
- Only one shell command, one line.
- nothing write outside JSON.

Query: "{query}"
""".strip()

# 🧾 Extract JSON response
def extract_command_and_response(llm_output):
    try:
        json_match = re.search(r"\{.*\"command\"\s*:\s*.*\}", llm_output, re.DOTALL)
        if not json_match:
            return None, None

        json_text = json_match.group(0)
        parsed = json.loads(json_text)
        command = parsed.get("command", "").strip()
        explanation = parsed.get("response", "").strip()
        return command, explanation

    except Exception as e:
        print(f"❌ JSON parse failed: {e}")
        return None, None

def get_llm_response(prompt, config):
    provider = config.get("llm_provider")
    try:
        engine_module = importlib.import_module(f"llm_engines.{provider}_llm")
        return engine_module.get_response(prompt, config)
    except Exception as e:
        return f"LLM error: {e}"

# 🧠 Pre-fill terminal input with editable default
def input_with_prefill(prompt_text, default_text):
    if readline:
        readline.set_startup_hook(lambda: readline.insert_text(default_text))
        try:
            return input(prompt_text)
        finally:
            readline.set_startup_hook(None)
    else:
        print("⚠️ Pre-filled editing not supported on this OS.")
        return input(f"{prompt_text} (type manually): ")

#  Main Loop
def main():
    config = load_config()
    print(Fore.GREEN + "🤖 Smart Terminal Assistant Ready (type 'exit' to quit)\n")

    global chat_history

    while True:
        user_input = input(">>> ").strip()

        if user_input.lower() == "exit":
            break

        if user_input.lower() == "[%clear%]":
            clear_memory()
            continue

        query = extract_prompt(user_input)
        if query:
            chat_history.append({"role": "user", "content": query})

            if get_total_tokens() > 3500:
                print("⚠️ Context memory full. Use [%clear%] to reset.\n")
                continue

            print(Fore.YELLOW + f"🧠 Querying: {query}\n")
            raw_prompt = format_prompt(query)
            response = get_llm_response(raw_prompt, config)
            chat_history.append({"role": "assistant", "content": response})

            print(f"\n🤖 LLM Response:\n{response}\n")

            command, explanation = extract_command_and_response(response)

            if command:
                print(Fore.CYAN + f"💡 Explanation: {explanation}")
                print(Fore.MAGENTA + Style.BRIGHT + f"💡 Suggested Command: {command}\n")

                confirm = input("⚠️ Run this command? (y/N/c for custom): ").lower()

                if confirm == "y":
                    subprocess.run(command, shell=True)

                elif confirm == "c":
                    edited_cmd = input_with_prefill("✍️ Edit command: ", command).strip()
                    if edited_cmd:
                        subprocess.run(edited_cmd, shell=True)
                    else:
                        print("❌ No command entered. Skipped.\n")
                else:
                    print("❌ Skipped.\n")
            else:
                print("⚠️ Could not extract a valid command from LLM response.\n")
        else:
            subprocess.run(user_input, shell=True)

# 🔁 Run Main
if __name__ == "__main__":
    main()
