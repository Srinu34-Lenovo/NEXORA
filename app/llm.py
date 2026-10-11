import requests
from app.config import OLLAMA_URL, OLLAMA_MODEL


class LLM:

    def __init__(
        self,
        url=OLLAMA_URL,
        model=OLLAMA_MODEL
    ):

        self.url = url.rstrip("/")
        self.model = model

    def available(self):

        try:

            response = requests.get(
                f"{self.url}/api/tags",
                timeout=3
            )

            return response.ok

        except requests.RequestException:

            return False

    def generate(self, prompt):

        try:

            response = requests.post(
                f"{self.url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120
            )

            response.raise_for_status()

            return response.json().get(
                "response",
                ""
            )

        except requests.RequestException as error:

            return (
                "Local LLM is unavailable. "
                f"Error: {error}"
            )


llm = LLM()