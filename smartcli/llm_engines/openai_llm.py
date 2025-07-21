import openai
def get_response(prompt, config, history=None):
    openai.api_key = config.get("api_key")
    model = config.get("model", "gpt-3.5-turbo")
    temperature = config.get("temperature", 0.7)

    try:
        messages = history if history else []
        messages.append({"role": "user", "content": prompt})

        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"OpenAI error: {e}"
