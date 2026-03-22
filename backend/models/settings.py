"""App settings models."""

from __future__ import annotations

from pydantic import BaseModel


class AppSettings(BaseModel):
    # API Provider
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model_default: str = "gpt-4o"
    openai_embed_model: str = "text-embedding-3-small"

    # Learning
    default_model: str = "gpt-4o"
    default_learning_intent: str = "build_system"
    default_mode: str = "full_system"
    max_graph_depth: int = 3
    auto_start_practice: bool = False
    auto_generate_summary: bool = True

    # Ollama
    ollama_enabled: bool = False

    # Infrastructure (read from config.py Settings)
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    lancedb_path: str = "./data/lancedb"
    sqlite_path: str = "./data/sqlite/axon_clone.db"
    ollama_base_url: str = "http://localhost:11434"
    app_env: str = "development"
    log_level: str = "INFO"


class LearningIntent(str):
    FIX_GAP = "fix_gap"
    BUILD_SYSTEM = "build_system"
    SOLVE_TASK = "solve_task"
    PREPARE_EXPRESSION = "prepare_expression"
    PREPARE_INTERVIEW = "prepare_interview"
