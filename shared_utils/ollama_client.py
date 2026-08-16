import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3.2"


def ask_ollama(system_prompt: str, user_message: str, model: str = None) -> str:
    """
    Calls a locally running Ollama model. Requires Ollama to be installed
    and running (ollama serve, or the app running in the background),
    with the model already pulled (e.g. `ollama pull llama3.2`).
    """
    model_name = model or DEFAULT_MODEL
    full_prompt = f"{system_prompt}\n\n{user_message}"

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": model_name,
                "prompt": full_prompt,
                "stream": False
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()["response"].strip()
    except requests.exceptions.ConnectionError:
        raise Exception(
            "Could not connect to Ollama. Make sure Ollama is installed and running "
            "(try running 'ollama serve' or opening the Ollama app), and that you've "
            "pulled a model with 'ollama pull llama3.2'."
        )