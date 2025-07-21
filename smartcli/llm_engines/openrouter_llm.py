import openai

def get_response(prompt, config, history=None):
    openai.api_key = config.get("api_key")
    openai.base_url = "https://openrouter.ai/api/v1"
    model = config.get("model", "mistralai/mixtral-8x7b")
    temperature = config.get("temperature", 0.7)

    messages = history if history else []
    messages.append({"role": "user", "content": prompt})

    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"OpenRouter error: {e}"
