def get_response(prompt, config, history=None):
    api_key = config.get("api_key")
    model_name = config.get("model", "gemini-pro")
    temperature = config.get("temperature", 0.7)

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)

        # Combine history and current prompt
        if history:
            messages = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
            full_prompt = f"{messages}\nuser: {prompt}"
        else:
            full_prompt = prompt

        response = model.generate_content(full_prompt, generation_config={"temperature": temperature})
        return response.text.strip()
    except Exception as e:
        return f"Gemini error: {e}"
