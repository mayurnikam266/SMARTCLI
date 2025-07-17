import google.generativeai as genai

def get_response(prompt, config):
    api_key = config.get("api_key")
    model_name = config.get("model", "gemini-pro")
    temperature = config.get("temperature", 0.7)

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt, generation_config={"temperature": temperature})
        return response.text.strip()
    except Exception as e:
        return f"Gemini error: {e}"
