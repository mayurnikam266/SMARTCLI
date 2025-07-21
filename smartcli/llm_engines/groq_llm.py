from openai import OpenAI

def get_response(prompt, config, history=None):
    try:
        client = OpenAI(
            api_key=config.get("api_key"),
            base_url="https://api.groq.com/openai/v1"
        )
        model = config.get("model", "llama3-8b")
        temperature = config.get("temperature", 0.7)

        messages = history if history else []
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Groq error: {e}"
