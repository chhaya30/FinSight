from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

from app.config.logging import get_logger
from app.config.settings import get_settings

logger = get_logger(__name__)


@dataclass
class LLMMessage:
    role: str
    content: str


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: dict[str, int] = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.usage is None:
            self.usage = {}
        if self.metadata is None:
            self.metadata = {}


@dataclass
class LLMConfig:
    model: str
    temperature: float = 0.1
    max_tokens: int = 4096
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: list[str] = None

    def __post_init__(self):
        if self.stop_sequences is None:
            self.stop_sequences = []


class BaseLLMProvider(ABC):
    def __init__(self, config: LLMConfig):
        self.config = config
        self.settings = get_settings()

    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        pass

    @abstractmethod
    async def generate_stream(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> AsyncGenerator[str, None]:
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    def _build_config(self, config: LLMConfig | None = None) -> LLMConfig:
        if config is None:
            return self.config
        return config


class LLMError(Exception):
    pass


class LLMProviderError(LLMError):
    def __init__(self, provider: str, message: str):
        self.provider = provider
        super().__init__(f"{provider}: {message}")


class LLMRateLimitError(LLMError):
    pass


class LLMTimeoutError(LLMError):
    pass


class LLMAuthenticationError(LLMError):
    pass


def create_system_message(content: str) -> LLMMessage:
    return LLMMessage(role="system", content=content)


def create_user_message(content: str) -> LLMMessage:
    return LLMMessage(role="user", content=content)


def create_assistant_message(content: str) -> LLMMessage:
    return LLMMessage(role="assistant", content=content)
