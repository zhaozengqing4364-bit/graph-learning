"""Application configuration via pydantic-settings."""

from pathlib import Path
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve_project_path(path_value: str) -> str:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    return str(path)


class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model_default: str = "gpt-4o"
    openai_embed_model: str = "text-embedding-3-small"
    embed_dimension: int = 1536

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "your_password"
    neo4j_max_connection_pool_size: int = 50
    neo4j_connection_acquisition_timeout: float = 60.0

    # LanceDB
    lancedb_path: str = "./data/lancedb"

    # SQLite
    sqlite_path: str = "./data/sqlite/axon_clone.db"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_enabled: bool = False

    # App
    app_env: str = "development"
    log_level: str = "INFO"

    model_config = {"env_file": str(PROJECT_ROOT / ".env"), "env_file_encoding": "utf-8"}


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        settings = Settings()
        settings.sqlite_path = resolve_project_path(settings.sqlite_path)
        settings.lancedb_path = resolve_project_path(settings.lancedb_path)
        _settings = settings
    return _settings


def reload_settings():
    """Re-read settings from .env file.

    Called after user saves settings via the UI.
    Database values are read separately by get_effective_settings()
    in the API layer, and AIClient reads from config + DB overlay
    on each instantiation.
    """
    global _settings
    settings = Settings()
    settings.sqlite_path = resolve_project_path(settings.sqlite_path)
    settings.lancedb_path = resolve_project_path(settings.lancedb_path)
    _settings = settings
