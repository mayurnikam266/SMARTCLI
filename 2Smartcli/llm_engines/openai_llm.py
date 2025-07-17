import openai

def get_response(prompt, config):
    openai.api_key = config.get("api_key")
    model = config.get("model", "gpt-3.5-turbo")
    temperature = config.get("temperature", 0.7)

    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"OpenAI error: {e}"
