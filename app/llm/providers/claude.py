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


class ClaudeProvider(BaseLLMProvider):
    def __init__(self, config: LLMConfig | None = None):
        settings = get_settings()

        default_config = LLMConfig(
            model=config.model if config else settings.CLAUDE_MODEL,
            temperature=config.temperature if config else 0.1,
            max_tokens=config.max_tokens if config else 4096,
        )

        super().__init__(default_config)
        self.api_key = settings.CLAUDE_API_KEY
        self.client = None
        self._init_client()

    def _init_client(self):
        try:
            import anthropic

            self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
        except ImportError:
            logger.warning("anthropic_not_installed")
        except Exception as e:
            logger.error("claude_client_init_failed", error=str(e))

    async def generate(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        if not self.client:
            raise LLMProviderError("claude", "Client not initialized")

        cfg = self._build_config(config)

        system_message = None
        formatted_messages = []

        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                formatted_messages.append(
                    {
                        "role": msg.role,
                        "content": msg.content,
                    }
                )

        try:
            response = await self.client.messages.create(
                model=cfg.model,
                messages=formatted_messages,
                system=system_message,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens,
                top_p=cfg.top_p,
                stop_sequences=cfg.stop_sequences or None,
            )

            content = ""
            for block in response.content:
                if block.type == "text":
                    content += block.text

            return LLMResponse(
                content=content,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                },
                metadata={"provider": "claude"},
            )
        except Exception as e:
            error_str = str(e).lower()
            if "rate limit" in error_str:
                raise LLMRateLimitError("claude", str(e)) from e
            elif "timeout" in error_str:
                raise LLMTimeoutError("claude", str(e)) from e
            elif "unauthorized" in error_str or "authentication" in error_str:
                raise LLMAuthenticationError("claude", str(e)) from e
            else:
                raise LLMProviderError("claude", str(e)) from e

    async def generate_stream(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> AsyncGenerator[str, None]:
        if not self.client:
            raise LLMProviderError("claude", "Client not initialized")

        cfg = self._build_config(config)

        system_message = None
        formatted_messages = []

        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                formatted_messages.append(
                    {
                        "role": msg.role,
                        "content": msg.content,
                    }
                )

        try:
            stream = await self.client.messages.create(
                model=cfg.model,
                messages=formatted_messages,
                system=system_message,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens,
                top_p=cfg.top_p,
                stop_sequences=cfg.stop_sequences or None,
                stream=True,
            )

            async for chunk in stream:
                if chunk.type == "content_block_delta" and chunk.delta.type == "text_delta":
                    yield chunk.delta.text
        except Exception as e:
            logger.error("claude_stream_error", error=str(e))
            raise LLMProviderError("claude", str(e)) from e

    def get_model_name(self) -> str:
        return self.config.model

    def is_available(self) -> bool:
        return self.client is not None and self.api_key is not None
