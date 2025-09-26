"""Factory for creating provider-agnostic embedding models."""

from typing import Any, cast

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

        model_name = embedding_model or "text-embedding-3-small"

        if api_key:
            return OpenAIEmbeddings(model=model_name, openai_api_key=api_key)
        return OpenAIEmbeddings(model=model_name)

    # Anthropic embeddings
    if embedding_provider == "anthropic":
        # Anthropic does not provide embeddings; surface a clear error.
        raise ValueError("Anthropic embeddings are not supported.")

    # Azure OpenAI embeddings
    if embedding_provider == "azure-openai":
        api_key = getattr(config, "azure_openai_api_key", None) or getattr(
            config, "openai_api_key", None
        )

        model_name = embedding_model or "text-embedding-ada-002"
        if api_key:
            return OpenAIEmbeddings(model=model_name, openai_api_key=api_key)
        return OpenAIEmbeddings(model=model_name)

    if embedding_provider == "cohere":
        try:
            from langchain_cohere import CohereEmbeddings
        except ImportError as e:
            raise ImportError(
                "Please install langchain-cohere: pip install langchain-cohere"
            ) from e

        api_key = getattr(config, "cohere_api_key", None)
        model_name = embedding_model or "embed-english-v3.0"
        return cast("Embeddings", CohereEmbeddings(model=model_name, cohere_api_key=api_key))

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
            try:
                from langchain_huggingface import HuggingFaceEndpointEmbeddings
            except ImportError as e:  # pragma: no cover - optional dependency
                raise ImportError(
                    "Please install langchain-huggingface: pip install langchain-huggingface"
                ) from e
            return cast(
                "Embeddings",
                HuggingFaceEndpointEmbeddings(model=model_name, huggingfacehub_api_token=api_key),
            )
        # Using local model
        return cast(
            "Embeddings",
            HuggingFaceEmbeddings(
                model_name=model_name, cache_folder=str(config.learning_db_path / "models")
            ),
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

        return cast("Embeddings", OllamaEmbeddings(model=model_name, base_url=base_url))

    if embedding_provider == "google-genai":
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
        except ImportError as e:
            raise ImportError(
                "Please install langchain-google-genai: pip install langchain-google-genai"
            ) from e

        api_key = getattr(config, "google_api_key", None)
        model_name = embedding_model or "models/embedding-001"
        return cast(
            "Embeddings", GoogleGenerativeAIEmbeddings(model=model_name, google_api_key=api_key)
        )

    if embedding_provider == "mistralai":
        try:
            from langchain_mistralai import MistralAIEmbeddings
        except ImportError as e:
            raise ImportError(
                "Please install langchain-mistralai: pip install langchain-mistralai"
            ) from e

        api_key = getattr(config, "mistral_api_key", None)
        model_name = embedding_model or "mistral-embed"
        return cast("Embeddings", MistralAIEmbeddings(model=model_name, api_key=api_key))

    if embedding_provider == "voyage":
        try:
            from langchain_voyageai import VoyageEmbeddings
        except ImportError as e:
            raise ImportError(
                "Please install langchain-voyageai: pip install langchain-voyageai"
            ) from e

        api_key = getattr(config, "voyage_api_key", None)
        model_name = embedding_model or "voyage-2"
        return cast("Embeddings", VoyageEmbeddings(model=model_name, api_key=api_key))

    # Default to OpenAI if no provider specified
    if not embedding_provider:
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model="text-embedding-3-small")

    raise ValueError(f"Unsupported embedding provider: {embedding_provider}")
