from abc import ABC, abstractmethod

import httpx

from src.llm.errors import ErrorKind, LLMError


class LLMProvider(ABC):
    name: str
    model: str
    context_window_tokens: int
    max_output_tokens: int

    @abstractmethod
    async def extract(self, prompt: str, timeout_seconds: float) -> str:
        """Return provider response text containing JSON."""

    def classify_http_error(
        self,
        status_code: int,
        body: str,
        retry_after: str | None = None,
    ) -> LLMError:
        if status_code == 429:
            retry_after_seconds = (
                float(retry_after) if retry_after and retry_after.isdigit() else None
            )
            return LLMError(
                self.name,
                ErrorKind.RATE_LIMIT,
                "Provider rate limit exceeded",
                retry_after_seconds,
            )
        if status_code == 413:
            return LLMError(
                self.name,
                ErrorKind.PAYLOAD_TOO_LARGE,
                "Provider payload exceeded its limit",
            )
        if status_code in (401, 403):
            return LLMError(self.name, ErrorKind.AUTHENTICATION, body)
        if status_code == 400:
            return LLMError(self.name, ErrorKind.INVALID_REQUEST, body)
        if status_code in (408, 409) or status_code >= 500:
            return LLMError(self.name, ErrorKind.TRANSIENT, body)
        return LLMError(self.name, ErrorKind.PERMANENT, body)


class GeminiProvider(LLMProvider):
    name = "gemini"
    context_window_tokens = 100000
    max_output_tokens = 8192

    def __init__(self, api_key: str | None, model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model = model

    async def extract(self, prompt: str, timeout_seconds: float) -> str:
        if not self.api_key:
            raise LLMError(
                self.name, ErrorKind.AUTHENTICATION, "GEMINI_API_KEY is missing"
            )
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(
                url,
                params={"key": self.api_key},
                json=payload,
            )
        if response.status_code >= 400:
            raise self.classify_http_error(
                response.status_code,
                response.text,
                response.headers.get("Retry-After"),
            )
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


class OpenAICompatibleProvider(LLMProvider):
    def __init__(
        self,
        *,
        name: str,
        api_key: str | None,
        model: str,
        endpoint: str,
        context_window_tokens: int,
        max_output_tokens: int,
    ):
        self.name = name
        self.api_key = api_key
        self.model = model
        self.endpoint = endpoint
        self.context_window_tokens = context_window_tokens
        self.max_output_tokens = max_output_tokens

    async def extract(self, prompt: str, timeout_seconds: float) -> str:
        if not self.api_key:
            raise LLMError(
                self.name,
                ErrorKind.AUTHENTICATION,
                f"{self.name.upper()} API key is missing",
            )
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                    "temperature": 0,
                },
            )
        if response.status_code >= 400:
            raise self.classify_http_error(
                response.status_code,
                response.text,
                response.headers.get("Retry-After"),
            )
        data = response.json()
        return data["choices"][0]["message"]["content"]


class GroqProvider(OpenAICompatibleProvider):
    def __init__(self, api_key: str | None, model: str = "llama-3.3-70b-versatile"):
        super().__init__(
            name="groq",
            api_key=api_key,
            model=model,
            endpoint="https://api.groq.com/openai/v1/chat/completions",
            context_window_tokens=32000,
            max_output_tokens=8192,
        )


class DeepSeekProvider(OpenAICompatibleProvider):
    def __init__(self, api_key: str | None, model: str = "deepseek-chat"):
        super().__init__(
            name="deepseek",
            api_key=api_key,
            model=model,
            endpoint="https://api.deepseek.com/chat/completions",
            context_window_tokens=64000,
            max_output_tokens=8192,
        )
