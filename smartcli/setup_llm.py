# setup.py

import yaml
import os

def setup():
    print("\n📦 LLM Terminal Assistant Setup")
    print("Select LLM provider:")
    print("1. Ollama (local)")
    print("2. OpenAI (via API key)")
    print("3. Groq (free tier or premium)")
    print("4. Gemini AI API")
    print("5. OpenRouter (free API keys or paid)")

    choice = input("Enter the number of the provider you want to use: ").strip()

    providers = {
        "1": "ollama",
        "2": "openai",
        "3": "groq",
        "4": "gemini",
        "5": "openrouter"
    }

    llm_provider = providers.get(choice)
    if not llm_provider:
        print("❌ Invalid choice. Exiting setup.")
        return

    api_key = input(f"🔑 Enter your API key for {llm_provider} (leave blank if not needed): ").strip()
    model = input(f"🧠 Enter the default model name for {llm_provider} (e.g., gpt-4, llama3): ").strip()

    config = {
        "llm_provider": llm_provider,
        "api_key": api_key,
        "model": model
    }

    os.makedirs(".", exist_ok=True)
    with open("config.yaml", "w") as f:
        yaml.dump(config, f)

    print("✅ Configuration saved to config.yaml")

if __name__ == "__main__":
    setup()
