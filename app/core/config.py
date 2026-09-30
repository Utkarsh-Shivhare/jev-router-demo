"""Application configuration."""
import os
from typing import List, Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # API Keys
    TYPESAFE_API_KEY: Optional[str] = Field(default=None, description="Direct TypeSafe AI API key")
    AI_GATEWAY_API_KEY: Optional[str] = Field(default=None, description="Vercel AI Gateway API key")
    OPENROUTER_API_KEY: Optional[str] = Field(default=None, description="OpenRouter API key")
    
    # LLM Configuration
    LLM_API_KEY: Optional[str] = Field(default=None, description="LLM API key (OpenAI-compatible)")
    LLM_MODEL: str = Field(default="gpt-4o-mini", description="LLM model to use")
    LLM_BASE_URL: str = Field(default="https://api.openai.com/v1", description="LLM API base URL")
    
    # Jev Configuration
    JEV_PROVIDER: str = Field(
        default="auto",
        description="Jev provider: 'auto', 'typesafe', 'vercel', or 'openrouter'"
    )
    JEV_MODEL: str = Field(default="typesafe/jev-router", description="Jev model name")
    
    # Application
    APP_NAME: str = "AI Support Router"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = Field(default=False)
    
    # Routing
    SUPPORT_CATEGORIES: List[str] = Field(
        default=[
            "refund",
            "order_status",
            "billing",
            "technical_support",
            "general_support",
        ]
    )


settings = Settings()
