import requests

def get_response(prompt, config, history=None):
    model = config.get("model", "llama3")
    url = "http://localhost:11434/api/chat"

    messages = history if history else []
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "stream": False
    }

    try:
        response = requests.post(url, json=payload)
        return response.json()["message"]["content"].strip()
    except Exception as e:
        return f"Ollama error: {e}"
