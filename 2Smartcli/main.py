import os
import yaml
import subprocess
import re
import importlib
import json
from pathlib import Path

# Load configuration
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

# Match `*** prompt ***`
def extract_prompt(user_input):
    pattern = r"\*{3}\s*(.*?)\s*\*{3}"
    match = re.search(pattern, user_input)
    return match.group(1).strip() if match else None

# Prompt Engineering with dynamic output support
def format_prompt(query, output=None):
    base_prompt = """
You are a DevOps assistant. Respond in this exact JSON format:

{{
  "response": "Brief explanation of what the command will do.",
  "command": "ONLY the exact shell command without any explanation or extra output.",
  "needs_output": false,
  "pre_command": ""
}}

⚠️ RULES:
- Only reply in JSON.
- If you need system output to generate final command, set 'needs_output': true and give the needed 'pre_command'.
- If 'Output:' is provided, generate final command directly from it.

Query: "{}"
{}""".strip()

    output_section = 'Output:\n{}'.format(output) if output else ''
    return base_prompt.format(query, output_section)

# Extract JSON parts from LLM response
def parse_llm_json(output):
    try:
        match = re.search(r'\{.*\}', output, re.DOTALL)
        return json.loads(match.group(0)) if match else None
    except Exception as e:
        print(f"❌ Failed to parse JSON: {e}")
        return None

def get_llm_response(prompt, config):
    provider = config.get("llm_provider")
    try:
        engine_module = importlib.import_module(f"llm_engines.{provider}_llm")
        return engine_module.get_response(prompt, config)
    except Exception as e:
        return f"LLM error: {e}"

# Safely run command and return output
def run_shell_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

# Main Execution Loop
def main():
    config = load_config()
    print("🤖 Smart Terminal Assistant Ready (type 'exit' to quit)\n")
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

            prompt = format_prompt(query)
            raw_response = get_llm_response(prompt, config)
            chat_history.append({"role": "assistant", "content": raw_response})
            print(f"\n🤖 LLM Response:\n{raw_response}\n")

            parsed = parse_llm_json(raw_response)
            if not parsed:
                print("⚠️ Could not extract valid JSON.\n")
                continue

            if parsed.get("needs_output"):
                pre_cmd = parsed.get("pre_command")
                print(f"⚠️ This task needs to run: `{pre_cmd}` to gather info.")
                confirm = input("Can I run this and use its output? [y/N]: ").lower()
                if confirm == "y":
                    pre_output = run_shell_command(pre_cmd)
                    print(f"\n📥 Output:\n{pre_output}")
                    follow_up_prompt = format_prompt(query, output=pre_output)
                    follow_up_response = get_llm_response(follow_up_prompt, config)
                    print(f"\n🤖 LLM Final Response:\n{follow_up_response}\n")

                    follow_parsed = parse_llm_json(follow_up_response)
                    if follow_parsed and follow_parsed.get("command"):
                        print(f"💡 {follow_parsed['response']}")
                        print(f"💻 Command to run: {follow_parsed['command']}")
                        final_confirm = input("⚠️ Run this command? (y/N): ").lower()
                        if final_confirm == "y":
                            print(run_shell_command(follow_parsed["command"]))
                    else:
                        print("❌ Could not extract final command.")
                else:
                    print("❌ Skipped fetching output.\n")

            else:
                print(f"💡 {parsed['response']}")
                print(f"💻 Command to run: {parsed['command']}")
                final_confirm = input("⚠️ Run this command? (y/N): ").lower()
                if final_confirm == "y":
                    print(run_shell_command(parsed["command"]))

        else:
            subprocess.run(user_input, shell=True)

# 🔁 Run
if __name__ == "__main__":
    main()
