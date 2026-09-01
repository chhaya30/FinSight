from collections.abc import AsyncGenerator

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


class GroqProvider(BaseLLMProvider):
    def __init__(self, config: LLMConfig | None = None):
        settings = get_settings()

        default_config = LLMConfig(
            model=config.model if config else settings.GROQ_MODEL,
            temperature=config.temperature if config else 0.1,
            max_tokens=config.max_tokens if config else 4096,
        )

        super().__init__(default_config)
        self.api_key = settings.GROQ_API_KEY
        self.client = None
        self._init_client()

    def _init_client(self):
        try:
            from groq import AsyncGroq

            self.client = AsyncGroq(api_key=self.api_key)
        except ImportError:
            logger.warning("groq_not_installed")
        except Exception as e:
            logger.error("groq_client_init_failed", error=str(e))

    async def generate(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        if not self.client:
            raise LLMProviderError("groq", "Client not initialized")

        cfg = self._build_config(config)

        formatted_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

        try:
            response = await self.client.chat.completions.create(
                model=cfg.model,
                messages=formatted_messages,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens,
                top_p=cfg.top_p,
                frequency_penalty=cfg.frequency_penalty,
                presence_penalty=cfg.presence_penalty,
                stop=cfg.stop_sequences or None,
            )

            return LLMResponse(
                content=response.choices[0].message.content,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
                if response.usage
                else {},
                metadata={"provider": "groq"},
            )
        except Exception as e:
            error_str = str(e).lower()
            if "rate limit" in error_str:
                raise LLMRateLimitError("groq", str(e)) from e
            elif "timeout" in error_str:
                raise LLMTimeoutError("groq", str(e)) from e
            elif "unauthorized" in error_str or "authentication" in error_str:
                raise LLMAuthenticationError("groq", str(e)) from e
            else:
                raise LLMProviderError("groq", str(e)) from e

    async def generate_stream(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> AsyncGenerator[str, None]:
        if not self.client:
            raise LLMProviderError("groq", "Client not initialized")

        cfg = self._build_config(config)

        formatted_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

        try:
            stream = await self.client.chat.completions.create(
                model=cfg.model,
                messages=formatted_messages,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens,
                top_p=cfg.top_p,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error("groq_stream_error", error=str(e))
            raise LLMProviderError("groq", str(e)) from e

    def get_model_name(self) -> str:
        return self.config.model

    def is_available(self) -> bool:
        return self.client is not None and self.api_key is not None
