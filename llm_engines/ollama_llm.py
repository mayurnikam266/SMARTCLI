import requests

def get_response(prompt, config):
    model = config.get("model", "llama3")
    url = f"http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(url, json=payload)
        return response.json()["response"].strip()
    except Exception as e:
        return f"Ollama error: {e}"
