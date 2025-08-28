"""Factory for creating provider-agnostic embedding models."""
# mypy: ignore-errors

import contextlib
from typing import Any

from langchain_core.embeddings import Embeddings


def get_embeddings(config: Any) -> Embeddings:
    """
    Create an embeddings model based on configuration settings.

    This factory method abstracts away provider-specific implementations
    and returns a standardized LangChain embeddings interface.

    Args:
        config: Configuration object with embedding settings

    Returns:
        Embeddings instance configured according to settings

    Raises:
        ValueError: If the embedding provider is not supported
        ImportError: If required provider package is not installed
    """
    embedding_provider = config.embedding_provider
    embedding_model = getattr(config, "embedding_model", None)

    # OpenAI embeddings
    if embedding_provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        api_key = getattr(config, "openai_api_key", None)
        base_url = getattr(config, "openai_base_url", None)

        model_name = embedding_model or "text-embedding-3-small"
        kwargs = {"model": model_name}

        if api_key:
            kwargs["openai_api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url

        return OpenAIEmbeddings(**kwargs)  # type: ignore[arg-type]

    # Anthropic embeddings
    if embedding_provider == "anthropic":
        from langchain_anthropic import AnthropicEmbeddings

        api_key = getattr(config, "anthropic_api_key", None)

        model_name = embedding_model or "claude-3-opus"
        return AnthropicEmbeddings(model=model_name, api_key=api_key)

    # Azure OpenAI embeddings
    if embedding_provider == "azure-openai":
        api_key = getattr(config, "azure_openai_api_key", None) or getattr(
            config, "openai_api_key", None
        )

        model_name = embedding_model or "text-embedding-ada-002"
        return OpenAIEmbeddings(model=model_name, openai_api_key=api_key)

    if embedding_provider == "cohere":
        try:
            from langchain_cohere import CohereEmbeddings
        except ImportError as e:
            raise ImportError(
                "Please install langchain-cohere: pip install langchain-cohere"
            ) from e

        api_key = getattr(config, "cohere_api_key", None)
        model_name = embedding_model or "embed-english-v3.0"
        return CohereEmbeddings(model=model_name, cohere_api_key=api_key)

    if embedding_provider == "huggingface":
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
        except ImportError as e:
            raise ImportError(
                "Please install langchain-huggingface: pip install langchain-huggingface"
            ) from e

        api_key = getattr(config, "huggingface_api_key", None)
        model_name = embedding_model or "sentence-transformers/all-MiniLM-L6-v2"

        # Check if using local or API-based
        if api_key:
            # Using HuggingFace Hub API
            with contextlib.suppress(ImportError):
                from langchain_huggingface import HuggingFaceEndpointEmbeddings
            return HuggingFaceEndpointEmbeddings(model=model_name, huggingfacehub_api_token=api_key)
        # Using local model
        return HuggingFaceEmbeddings(
            model_name=model_name, cache_folder=str(config.learning_db_path / "models")
        )

    if embedding_provider == "ollama":
        try:
            from langchain_ollama import OllamaEmbeddings
        except ImportError as e:
            raise ImportError(
                "Please install langchain-ollama: pip install langchain-ollama"
            ) from e

        model_name = embedding_model or "llama2"
        base_url = getattr(config, "ollama_base_url", "http://localhost:11434")

        return OllamaEmbeddings(model=model_name, base_url=base_url)

    if embedding_provider == "google-genai":
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
        except ImportError as e:
            raise ImportError(
                "Please install langchain-google-genai: pip install langchain-google-genai"
            ) from e

        api_key = getattr(config, "google_api_key", None)
        model_name = embedding_model or "models/embedding-001"
        return GoogleGenerativeAIEmbeddings(model=model_name, google_api_key=api_key)

    if embedding_provider == "mistralai":
        try:
            from langchain_mistralai import MistralAIEmbeddings
        except ImportError as e:
            raise ImportError(
                "Please install langchain-mistralai: pip install langchain-mistralai"
            ) from e

        api_key = getattr(config, "mistral_api_key", None)
        model_name = embedding_model or "mistral-embed"
        return MistralAIEmbeddings(model=model_name, api_key=api_key)

    if embedding_provider == "voyage":
        try:
            from langchain_voyageai import VoyageEmbeddings
        except ImportError as e:
            raise ImportError(
                "Please install langchain-voyageai: pip install langchain-voyageai"
            ) from e

        api_key = getattr(config, "voyage_api_key", None)
        model_name = embedding_model or "voyage-2"
        return VoyageEmbeddings(model=model_name, api_key=api_key)

    # Default to OpenAI if no provider specified
    if not embedding_provider:
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model="text-embedding-3-small")

    raise ValueError(f"Unsupported embedding provider: {embedding_provider}")
