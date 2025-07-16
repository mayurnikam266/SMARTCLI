import yaml
from pathlib import Path

def main():
    print("\n📦 LLM Terminal Assistant Setup")
    print("Select LLM provider:")
    print("1. Ollama (local)")
    print("2. OpenAI (via API key)")
    print("3. Groq (free tier or premium)")
    print("4. Gemini AI API")
    print("5. OpenRouter (free API keys or paid)")
    print("6. Custom (add your own engine manually)")

    provider_map = {
        "1": "ollama",
        "2": "openai",
        "3": "groq",
        "4": "gemini",
        "5": "openrouter",
        "6": "custom"
    }

    choice = input("Enter your choice (1-6): ").strip()
    provider = provider_map.get(choice)

    if not provider:
        print("❌ Invalid choice. Exiting.")
        return

    # Use a new name to avoid module conflict
    config_data = {
        "llm_provider": provider,
        "model": "",
        "api_key": ""
    }

    if provider == "ollama":
        config_data["model"] = input("Enter Ollama model name (e.g. llama3, codellama): ").strip()

    elif provider == "openai":
        config_data["api_key"] = input("Enter your OpenAI API key: ").strip()
        config_data["model"] = input("Enter OpenAI model name (e.g. gpt-4, gpt-3.5-turbo): ").strip()

    elif provider == "groq":
        config_data["api_key"] = input("Enter your Groq API key: ").strip()
        config_data["model"] = input("Enter Groq model name (e.g. groq-llama-3): ").strip()

    elif provider == "gemini":
        config_data["api_key"] = input("Enter your Gemini API key: ").strip()
        config_data["model"] = input("Enter Gemini model name (e.g. gemini-pro): ").strip()

    elif provider == "openrouter":
        config_data["api_key"] = input("Enter your OpenRouter API key: ").strip()
        config_data["model"] = input("Enter OpenRouter model name (e.g. mistralai/mixtral-8x7b): ").strip()

    elif provider == "custom":
        config_data["custom_engine"] = input("Enter custom engine module name (e.g. my_custom_llm): ").strip()
        config_data["model"] = input("Enter model name for custom engine: ").strip()

    temperature = input("Set temperature (0.0 - 1.0, default 0.7): ").strip()
    if temperature:
        config_data["temperature"] = float(temperature)

    # Save the config
    with open("config.yaml", "w") as f:
        yaml.dump(config_data, f)

    print("\n Config saved to config.yaml\nYou can now run: python main.py")

if __name__ == "__main__":
    main()
