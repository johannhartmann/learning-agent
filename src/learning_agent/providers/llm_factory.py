"""Factory for creating provider-agnostic chat models."""

from typing import Any, cast

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel


def get_chat_model(config: Any) -> BaseChatModel:
    """
    Create a chat model based on configuration settings.

    This factory method abstracts away provider-specific implementations
    and returns a standardized LangChain chat model interface.

    Args:
        config: Settings object containing LLM configuration

    Returns:
        BaseChatModel: Provider-agnostic chat model instance

    Supported providers:
        - openai: Uses OpenAI's GPT models
        - anthropic: Uses Anthropic's Claude models
        - ollama: Uses local Ollama models
        - google-genai: Uses Google's Gemini models
        - mistralai: Uses Mistral AI models
        - groq: Uses Groq's inference API
        - together: Uses Together AI's API
        - fireworks: Uses Fireworks AI's API
        - cohere: Uses Cohere's models
    """
    # Map provider names to their expected API key field names
    api_key_mapping = {
        "openai": config.openai_api_key,
        "anthropic": config.anthropic_api_key,
        "google-genai": getattr(config, "google_api_key", None),
        "mistralai": getattr(config, "mistral_api_key", None),
        "groq": getattr(config, "groq_api_key", None),
        "together": getattr(config, "together_api_key", None),
        "fireworks": getattr(config, "fireworks_api_key", None),
        "cohere": getattr(config, "cohere_api_key", None),
        "ollama": None,  # Ollama doesn't need an API key
    }

    # Get the appropriate API key for the provider
    api_key = api_key_mapping.get(config.llm_provider)

    # Handle generic api_key field as fallback
    if api_key is None and config.llm_provider != "ollama":
        api_key = getattr(config, "api_key", None)

    # Prepare model kwargs
    model_kwargs = {
        "temperature": config.llm_temperature,
        "max_tokens": config.llm_max_tokens,
    }

    # Add API key if available
    if api_key:
        model_kwargs["api_key"] = api_key

    # Special handling for Ollama (local models)
    if config.llm_provider == "ollama":
        # Ollama uses base_url instead of api_key
        ollama_base_url = getattr(config, "ollama_base_url", "http://localhost:11434")
        model_kwargs["base_url"] = ollama_base_url
        # Remove api_key from kwargs if present
        model_kwargs.pop("api_key", None)

    # Initialize the chat model using LangChain's factory
    try:
        model = cast(
            "BaseChatModel",
            init_chat_model(
                model=config.llm_model,
                model_provider=config.llm_provider,
                **model_kwargs,
            ),
        )
    except Exception as e:
        # Fallback to OpenAI if provider fails
        print(f"Warning: Failed to initialize {config.llm_provider}: {e}")
        print("Falling back to OpenAI provider")

        # Try with OpenAI as fallback
        if config.openai_api_key:
            return init_chat_model(
                model="gpt-3.5-turbo",
                model_provider="openai",
                api_key=config.openai_api_key,
                temperature=config.llm_temperature,
                max_tokens=config.llm_max_tokens,
            )
        raise ValueError(
            f"Failed to initialize {config.llm_provider} and no OpenAI API key available for fallback"
        ) from e
    else:
        return model
