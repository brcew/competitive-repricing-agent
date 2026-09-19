"""
Configuration settings for the competitive pricing agent system.

Rate limits are treated as runtime-fetched values with these as fallback defaults only.
Always verify current limits at console.groq.com before trusting these numbers.
"""

import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = SettingsConfigDict(env_file=".env")
    
    # Groq API Configuration
    groq_api_key: str = Field(...)
    
    # Database Configuration
    db_host: str = Field(default="localhost")
    db_port: int = Field(default=5432)
    db_name: str = Field(default="competitive_pricing")
    db_user: str = Field(default="postgres")
    db_password: str = Field(default="postgres")
    
    # Agent Configuration
    orchestrator_model: str = "openai/gpt-oss-120b"  # Updated: Large model for strategic decisions
    worker_model: str = "allam-2-7b"  # Updated: Small efficient model for frequent decisions
    
    # Business Rules
    watchlist_cap: int = Field(default=15)
    margin_floor_percent: float = Field(default=12.0)
    competitor_gap_threshold_percent: float = Field(default=5.0)
    
    # Rate Limiting & Budget (FALLBACK DEFAULTS - verify at console.groq.com)
    # These are approximate values and should be fetched from live headers
    orchestrator_rpm_limit: int = 30  # Requests per minute
    orchestrator_rpd_limit: int = 1000  # Requests per day
    orchestrator_tpm_limit: int = 12000  # Tokens per minute (approx)
    
    worker_rpm_limit: int = 30  # Requests per minute  
    worker_rpd_limit: int = 14400  # Requests per day
    worker_tpm_limit: int = 12000  # Tokens per minute (approx)
    
    call_budget_buffer: int = Field(default=50)
    
    # Timing Configuration
    demo_mode: bool = Field(default=False)
    orchestrator_interval_seconds: int = 3600  # 1 hour
    worker_interval_seconds: int = 900  # 15 minutes
    
    # Demo mode overrides (compressed timing)
    demo_orchestrator_interval_seconds: int = 60  # 1 minute
    demo_worker_interval_seconds: int = 15  # 15 seconds
    
    # Logging Configuration
    log_level: str = Field(default="INFO")
    structured_logs: bool = Field(default=True)
    
    # Cost Tracking (official Groq rates - verify current pricing)
    # These are used for cost projection only since we run on free tier
    orchestrator_cost_per_1k_tokens: float = 0.00059  # llama-3.3-70b pricing
    worker_cost_per_1k_tokens: float = 0.00018  # llama-3.1-8b pricing
    
    @property
    def database_url(self) -> str:
        """Construct database URL from components."""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def effective_orchestrator_interval(self) -> int:
        """Get orchestrator interval based on demo mode."""
        return self.demo_orchestrator_interval_seconds if self.demo_mode else self.orchestrator_interval_seconds
    
    @property
    def effective_worker_interval(self) -> int:
        """Get worker interval based on demo mode."""
        return self.demo_worker_interval_seconds if self.demo_mode else self.worker_interval_seconds


# Global settings instance
settings = Settings()