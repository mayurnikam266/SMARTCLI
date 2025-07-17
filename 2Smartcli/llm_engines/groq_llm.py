from openai import OpenAI

def get_response(prompt, config):
    try:
        client = OpenAI(
            api_key=config.get("api_key"),
            base_url="https://api.groq.com/openai/v1"
        )
        model = config.get("model", "llama3-8b")
        temperature = config.get("temperature", 0.7)

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Groq error: {e}"
