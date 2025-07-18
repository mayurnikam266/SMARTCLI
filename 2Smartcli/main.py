import os
import yaml
import subprocess
import re
import importlib
import json
import logging
from pathlib import Path
from typing import Dict, Optional, List

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class CLIAssistant:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config = self.load_config()
        self.chat_history: List[Dict[str, str]] = []
        self.max_tokens = 3500

    def load_config(self) -> Dict:
        """Load configuration from file or environment variables."""
        try:
            if not self.config_path.exists():
                logger.warning("Config file not found, using default settings.")
                return {"llm_provider": os.getenv("LLM_PROVIDER", "default")}
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {"llm_provider": "default"}

    def get_total_tokens(self) -> int:
        """Estimate total tokens in chat history (simplified word count)."""
        return sum(len(m["content"].split()) for m in self.chat_history)

    def clear_memory(self) -> None:
        """Clear chat history."""
        self.chat_history = []
        logger.info("Chat memory cleared.")

    def extract_prompt(self, user_input: str) -> Optional[str]:
        """Extract prompt between *** markers."""
        pattern = r"\*{3}\s*(.*?)\s*\*{3}"
        match = re.search(pattern, user_input, re.DOTALL)
        return match.group(1).strip() if match else None

    def format_prompt(self, query: str, output: Optional[str] = None) -> str:
        """Format prompt for LLM with JSON response requirement."""
        base_prompt = """
You are a DevOps CLI assistant. Respond in valid JSON only:
{{
  "response": "What the command will do.",
  "command": "Shell command to run (empty if more input needed).",
  "needs_output": false,
  "pre_command": "Command to run for more info (if needed).",
  "next_question": "Ask for missing info (e.g., AMI ID), or empty."
}}

Rules:
1. Ask for missing info step-by-step via next_question.
2. Set needs_output: true and provide pre_command if system output is needed.
3. Only provide command when all inputs are collected.
4. Do not assume values; ask clearly.

Query: "{0}"
{1}"""
        output_section = f"Output:\n{output}" if output else ""
        return base_prompt.format(query, output_section).strip()

    def parse_llm_json(self, output: str) -> Optional[Dict]:
        """Parse JSON from LLM response."""
        try:
            match = re.search(r'\{.*\}', output, re.DOTALL)
            if not match:
                logger.error("No JSON found in LLM response.")
                return None
            return json.loads(match.group(0))
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return None

    def get_llm_response(self, prompt: str) -> Dict:
        """Get response from LLM engine."""
        provider = self.config.get("llm_provider", "default")
        try:
            engine_module = importlib.import_module(f"llm_engines.{provider}_llm")
            response = engine_module.get_response(prompt, self.config)
            return {"response": response, "error": None}
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return {"response": None, "error": str(e)}

    def run_shell_command(self, cmd: str) -> Optional[str]:
        """Run shell command safely and return output."""
        try:
            result = subprocess.run(
                cmd, shell=False, capture_output=True, text=True, check=True
            )
            output = result.stdout.strip()
            if output:
                logger.info(f"Command output: {output}")
            if result.stderr:
                logger.warning(f"Command stderr: {result.stderr.strip()}")
            return output
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {e.stderr}")
            return None
        except Exception as e:
            logger.error(f"Exception during command execution: {e}")
            return None

    def validate_command(self, cmd: str) -> bool:
        """Validate shell command (basic whitelist example)."""
        allowed_commands = ["aws", "kubectl", "docker", "ls", "cat"]
        return any(cmd.startswith(allowed) for allowed in allowed_commands)

    def run(self) -> None:
        """Main execution loop."""
        logger.info("Smart Terminal Assistant Ready (type 'exit' to quit)")
        try:
            while True:
                user_input = input(">>> ").strip()

                if user_input.lower() == "exit":
                    logger.info("Exiting CLI assistant.")
                    break

                if user_input.lower() == "[%clear%]":
                    self.clear_memory()
                    continue

                query = self.extract_prompt(user_input)
                if query:
                    if self.get_total_tokens() > self.max_tokens:
                        logger.warning("Context memory full. Use [%clear%] to reset.")
                        continue

                    self.chat_history.append({"role": "user", "content": query})
                    prompt = self.format_prompt(query)
                    llm_result = self.get_llm_response(prompt)

                    if llm_result["error"]:
                        print(json.dumps({"error": llm_result["error"]}))
                        continue

                    parsed = self.parse_llm_json(llm_result["response"])
                    if not parsed:
                        print(json.dumps({"error": "Invalid LLM response format"}))
                        continue

                    print(json.dumps(parsed, indent=2))
                    if parsed.get("needs_output"):
                        pre_cmd = parsed.get("pre_command")
                        if not self.validate_command(pre_cmd):
                            print(json.dumps({"error": "Invalid pre_command"}))
                            continue
                        confirm = input(f"Run `{pre_cmd}` to gather info? [y/N]: ").lower()
                        if confirm == "y":
                            pre_output = self.run_shell_command(pre_cmd)
                            if pre_output is None:
                                print(json.dumps({"error": "Failed to run pre_command"}))
                                continue
                            follow_up_prompt = self.format_prompt(query, pre_output)
                            follow_up_result = self.get_llm_response(follow_up_prompt)
                            if follow_up_result["error"]:
                                print(json.dumps({"error": follow_up_result["error"]}))
                                continue
                            follow_parsed = self.parse_llm_json(follow_up_result["response"])
                            if follow_parsed and follow_parsed.get("command"):
                                print(json.dumps(follow_parsed, indent=2))
                                if self.validate_command(follow_parsed["command"]):
                                    confirm = input(f"Run `{follow_parsed['command']}`? [y/N]: ").lower()
                                    if confirm == "y":
                                        self.run_shell_command(follow_parsed["command"])
                                else:
                                    print(json.dumps({"error": "Invalid command"}))
                            else:
                                print(json.dumps({"error": "No valid command in follow-up response"}))
                    elif parsed.get("command"):
                        if self.validate_command(parsed["command"]):
                            confirm = input(f"Run `{parsed['command']}`? [y/N]: ").lower()
                            if confirm == "y":
                                self.run_shell_command(parsed["command"])
                        else:
                            print(json.dumps({"error": "Invalid command"}))
                    else:
                        print(json.dumps({"info": "No command to run"}))
                else:
                    print(json.dumps({"error": "Invalid prompt format. Use *** prompt ***"}))
        except KeyboardInterrupt:
            logger.info("Received interrupt, exiting gracefully.")
            print(json.dumps({"info": "Exiting due to user interrupt"}))

if __name__ == "__main__":
    assistant = CLIAssistant()
    assistant.run()