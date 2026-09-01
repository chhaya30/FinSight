from app.config.constants import LLMProvider
from app.config.logging import get_logger
from app.config.settings import get_settings
from app.llm.base import BaseLLMProvider, LLMConfig
from app.llm.providers.claude import ClaudeProvider
from app.llm.providers.groq import GroqProvider
from app.llm.providers.ollama import OllamaProvider

logger = get_logger(__name__)


class ProviderFactory:
    _providers: dict[LLMProvider, type[BaseLLMProvider]] = {
        LLMProvider.GROQ: GroqProvider,
        LLMProvider.OLLAMA: OllamaProvider,
        LLMProvider.CLAUDE: ClaudeProvider,
    }

    _instances: dict[LLMProvider, BaseLLMProvider] = {}

    @classmethod
    def register(cls, provider: LLMProvider, provider_class: type[BaseLLMProvider]):
        cls._providers[provider] = provider_class

    @classmethod
    def create(
        cls,
        provider: LLMProvider | None = None,
        config: LLMConfig | None = None,
    ) -> BaseLLMProvider:
        settings = get_settings()

        if provider is None:
            provider = LLMProvider(settings.LLM_PROVIDER)

        if provider not in cls._providers:
            raise ValueError(f"Unknown provider: {provider}")

        provider_class = cls._providers[provider]
        instance = provider_class(config)

        if not instance.is_available():
            logger.warning("provider_not_available", provider=provider.value)

        cls._instances[provider] = instance
        return instance

    @classmethod
    def get_instance(cls, provider: LLMProvider | None = None) -> BaseLLMProvider | None:
        settings = get_settings()

        if provider is None:
            provider = LLMProvider(settings.LLM_PROVIDER)

        if provider in cls._instances:
            return cls._instances[provider]

        return cls.create(provider)

    @classmethod
    def get_all_instances(cls) -> dict[LLMProvider, BaseLLMProvider]:
        return cls._instances.copy()

    @classmethod
    def clear_instances(cls):
        cls._instances.clear()


def get_llm_provider(
    provider: LLMProvider | None = None,
    config: LLMConfig | None = None,
) -> BaseLLMProvider:
    return ProviderFactory.create(provider, config)


def get_default_llm() -> BaseLLMProvider:
    return ProviderFactory.get_instance()
