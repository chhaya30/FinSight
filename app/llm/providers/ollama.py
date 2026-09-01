from collections.abc import AsyncGenerator

import aiohttp

from app.config.logging import get_logger
from app.config.settings import get_settings
from app.llm.base import (
    BaseLLMProvider,
    LLMAuthenticationError,
    LLMConfig,
    LLMMessage,
    LLMProviderError,
    LLMRateLimitError,
    LLMResponse,
    LLMTimeoutError,
)

logger = get_logger(__name__)


class OllamaProvider(BaseLLMProvider):
    def __init__(self, config: LLMConfig | None = None):
        settings = get_settings()

        default_config = LLMConfig(
            model=config.model if config else settings.OLLAMA_MODEL,
            temperature=config.temperature if config else 0.1,
            max_tokens=config.max_tokens if config else 4096,
        )

        super().__init__(default_config)
        self.base_url = settings.OLLAMA_BASE_URL
        self.session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def generate(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        cfg = self._build_config(config)

        formatted_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

        payload = {
            "model": cfg.model,
            "messages": formatted_messages,
            "options": {
                "temperature": cfg.temperature,
                "num_predict": cfg.max_tokens,
                "top_p": cfg.top_p,
            },
            "stream": False,
        }

        session = await self._get_session()

        try:
            async with session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as response:
                if response.status == 401:
                    raise LLMAuthenticationError("ollama", "Unauthorized")
                elif response.status == 429:
                    raise LLMRateLimitError("ollama", "Rate limited")
                elif response.status >= 500:
                    raise LLMTimeoutError("ollama", "Server error")

                data = await response.json()

                return LLMResponse(
                    content=data.get("message", {}).get("content", ""),
                    model=data.get("model", cfg.model),
                    usage={
                        "prompt_tokens": data.get("prompt_eval_count", 0),
                        "completion_tokens": data.get("eval_count", 0),
                        "total_tokens": (
                            data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                        ),
                    },
                    metadata={"provider": "ollama"},
                )
        except aiohttp.ClientError as e:
            logger.error("ollama_connection_error", error=str(e))
            raise LLMProviderError("ollama", f"Connection error: {e}") from e
        except Exception as e:
            logger.error("ollama_generate_error", error=str(e))
            raise LLMProviderError("ollama", str(e)) from e

    async def generate_stream(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> AsyncGenerator[str, None]:
        cfg = self._build_config(config)

        formatted_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

        payload = {
            "model": cfg.model,
            "messages": formatted_messages,
            "options": {
                "temperature": cfg.temperature,
                "num_predict": cfg.max_tokens,
                "top_p": cfg.top_p,
            },
            "stream": True,
        }

        session = await self._get_session()

        try:
            async with session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as response:
                if response.status != 200:
                    raise LLMProviderError("ollama", f"HTTP {response.status}")

                async for line in response.content:
                    line = line.decode("utf-8").strip()
                    if not line:
                        continue

                    try:
                        import json

                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            yield data["message"]["content"]
                    except json.JSONDecodeError:
                        continue
        except aiohttp.ClientError as e:
            logger.error("ollama_stream_connection_error", error=str(e))
            raise LLMProviderError("ollama", f"Connection error: {e}") from e
        except Exception as e:
            logger.error("ollama_stream_error", error=str(e))
            raise LLMProviderError("ollama", str(e)) from e

    def get_model_name(self) -> str:
        return self.config.model

    def is_available(self) -> bool:
        return True

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def pull_model(self, model: str) -> bool:
        session = await self._get_session()
        try:
            async with session.post(
                f"{self.base_url}/api/pull",
                json={"name": model},
                timeout=aiohttp.ClientTimeout(total=300),
            ) as response:
                return response.status == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        session = await self._get_session()
        try:
            async with session.get(
                f"{self.base_url}/api/tags",
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return [m["name"] for m in data.get("models", [])]
        except Exception:
            pass
        return []
