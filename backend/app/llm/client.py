import requests
import json
import asyncio

OLLAMA_URL = "http://localhost:11434/api/generate"
# OLLAMA_URL = "http://localhost:8080/v1/chat/completions" # Example for a different local LLM API (e.g., LM Studio)
DEFAULT_MODEL = "tinyllama" # Or "tinyllama", "llama3", etc.

async def ask_llm(prompt: str, model: str = DEFAULT_MODEL, temperature: float = 0.7, max_tokens: int = 500) -> str:
    """
    Asynchronously sends a prompt to the local Ollama LLM and returns its response.
    """
    try:
        # Use asyncio.to_thread for synchronous requests library calls in an async context
        def _sync_request():
            # For Ollama's /api/generate endpoint
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            # For OpenAI-compatible endpoints (e.g., LM Studio's /v1/chat/completions)
            # payload = {
            #     "model": model,
            #     "messages": [{"role": "user", "content": prompt}],
            #     "temperature": temperature,
            #     "max_tokens": max_tokens,
            #     "stream": False
            # }

            response = requests.post(OLLAMA_URL, json=payload, timeout=120)
            response.raise_for_status() # Raise an exception for HTTP errors
            return response.json()

        data = await asyncio.to_thread(_sync_request)

        # For Ollama's /api/generate endpoint
        if "response" in data:
            return data["response"].strip()
        
        # For OpenAI-compatible /v1/chat/completions endpoint
        # if "choices" in data and data["choices"]:
        #     return data["choices"][0]["message"]["content"].strip()

        return "⚠️ LLM returned an unexpected response format."

    except requests.exceptions.Timeout:
        return "❌ LLM error: Request to LLM timed out."
    except requests.exceptions.ConnectionError:
        return f"❌ LLM error: Could not connect to Ollama server at {OLLAMA_URL}. Is it running?"
    except requests.exceptions.RequestException as e:
        return f"❌ LLM request error: {str(e)}"
    except json.JSONDecodeError:
        return "❌ LLM error: Failed to decode JSON response from Ollama."
    except Exception as e:
        return f"❌ An unexpected error occurred with LLM client: {str(e)}"