"""Configuration and settings for the Learning Agent."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Ensure .env file exists
def ensure_env_file() -> None:
    """Ensure .env file exists, create from .env.example if needed."""
    env_file = Path(".env")
    if not env_file.exists():
        env_example = Path(".env.example")
        if env_example.exists():
            import shutil

            shutil.copy(env_example, env_file)
            print("Created .env file from .env.example. Please update it with your API keys.")


# Create .env if needed and load it
ensure_env_file()
load_dotenv()


class Settings(BaseSettings):  # type: ignore[misc]
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM Configuration
    openai_api_key: str | None = Field(None, description="OpenAI API key")
    anthropic_api_key: str | None = Field(None, description="Anthropic API key")
    api_key: str | None = Field(None, description="Generic API key for current provider")
    llm_provider: str = Field("openai", description="LLM provider to use")
    llm_model: str = Field("gpt-4-turbo-preview", description="LLM model to use")
    llm_temperature: float = Field(0.7, description="LLM temperature")
    llm_max_tokens: int = Field(4096, description="Maximum tokens for LLM response")

    # Embedding Configuration
    embedding_provider: str | None = Field(
        None, description="Embedding provider (defaults to llm_provider)"
    )
    embedding_model: str | None = Field(None, description="Embedding model to use")

    # Additional Provider API Keys
    google_api_key: str | None = Field(None, description="Google API key for Gemini")
    mistral_api_key: str | None = Field(None, description="Mistral AI API key")
    cohere_api_key: str | None = Field(None, description="Cohere API key")
    groq_api_key: str | None = Field(None, description="Groq API key")
    together_api_key: str | None = Field(None, description="Together AI API key")
    fireworks_api_key: str | None = Field(None, description="Fireworks AI API key")
    voyage_api_key: str | None = Field(None, description="Voyage AI API key")
    huggingface_api_key: str | None = Field(None, description="HuggingFace API key")

    # Local Model Configuration
    ollama_base_url: str = Field("http://localhost:11434", description="Ollama base URL")

    # Agent Configuration
    max_parallel_agents: int = Field(10, description="Maximum parallel sub-agents")
    enable_learning: bool = Field(True, description="Enable learning system")

    # Performance Configuration
    task_timeout_seconds: int = Field(300, description="Task execution timeout")
    checkpoint_interval_seconds: int = Field(60, description="Checkpoint interval")
    max_retries: int = Field(3, description="Maximum retry attempts")
    retry_delay_seconds: int = Field(5, description="Delay between retries")
    learning_search_timeout: float = Field(2.0, description="Learning search timeout")

    # Storage Configuration
    learning_db_path: Path = Field(Path(".agent"), description="Path to learning database")
    max_db_size_mb: int = Field(1024, description="Maximum database size in MB")
    enable_compression: bool = Field(True, description="Enable data compression")

    # UI Configuration
    terminal_width: int = Field(120, description="Terminal width for display")
    show_progress_bars: bool = Field(True, description="Show progress bars")
    use_colors: bool = Field(True, description="Use colored output")
    debug_mode: bool = Field(False, description="Enable debug mode")

    # Logging Configuration
    log_level: str = Field("INFO", description="Logging level")
    log_file: Path | None = Field(Path("learning_agent.log"), description="Log file path")
    log_format: str = Field("json", description="Log format (json or text)")

    def get_learning_paths(self) -> dict[str, Path]:
        """Get all learning storage paths."""
        base = self.learning_db_path
        return {
            "vectors": base / "vectors",
            "metadata": base / "metadata",
            "traces": base / "traces",
            "checkpoints": base / "checkpoints",
        }

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        for path in self.get_learning_paths().values():
            path.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
