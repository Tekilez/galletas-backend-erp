"""
Infrastructure - Config adapter (hexagonal).
Fuente única de Settings. app/config.py re-exporta para compatibilidad.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    app_name: str = "Kardex IA Microservice"
    app_version: str = "1.0.0"
    env: str = Field(default="development", description="development | production")

    # Proveedor LLM: "google" | "ollama" | "mock"
    llm_provider: str = Field(default="mock", alias="LLM_PROVIDER")
    google_api_key: str | None = Field(default=None, alias="GOOGLE_API_KEY")
    google_model: str = Field(default="gemini-2.0-flash", alias="GOOGLE_MODEL")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.1:8b", alias="OLLAMA_MODEL")

    # OCR provider: "mock" | "google" | "huggingface"
    ocr_provider: str = Field(default="mock", alias="OCR_PROVIDER")
    hf_token: str | None = Field(default=None, alias="HF_TOKEN")

    # Supabase
    supabase_url: str | None = Field(default=None, alias="SUPABASE_URL")
    supabase_service_key: str | None = Field(default=None, alias="SUPABASE_SERVICE_KEY")

    # CORS
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")

    # Límites upload
    max_upload_mb: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
