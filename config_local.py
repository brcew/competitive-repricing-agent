"""
Local development configuration using SQLite instead of PostgreSQL.
Useful for testing without Docker.
"""

import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LocalSettings(BaseSettings):
    """Local development settings with SQLite."""
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
    # Groq API Configuration
    groq_api_key: str = Field(default="your_groq_api_key_here")
    
    # SQLite Database (local file)
    db_file: str = Field(default="competitive_pricing.db")
    
    # Agent Configuration
    orchestrator_model: str = "openai/gpt-oss-120b"  # Updated: Large model for strategic decisions
    worker_model: str = "allam-2-7b"  # Updated: Small efficient model for frequent decisions
    
    # Business Rules
    watchlist_cap: int = Field(default=15)
    margin_floor_percent: float = Field(default=12.0)
    competitor_gap_threshold_percent: float = Field(default=5.0)
    
    # Rate Limiting & Budget (FALLBACK DEFAULTS)
    orchestrator_rpm_limit: int = 30
    orchestrator_rpd_limit: int = 1000
    orchestrator_tpm_limit: int = 12000
    
    worker_rpm_limit: int = 30
    worker_rpd_limit: int = 14400
    worker_tpm_limit: int = 12000
    
    call_budget_buffer: int = Field(default=50)
    
    # Timing Configuration
    demo_mode: bool = Field(default=False)
    orchestrator_interval_seconds: int = 3600
    worker_interval_seconds: int = 900
    
    demo_orchestrator_interval_seconds: int = 60
    demo_worker_interval_seconds: int = 15
    
    # Logging Configuration
    log_level: str = Field(default="INFO")
    structured_logs: bool = Field(default=True)
    
    # Cost Tracking
    orchestrator_cost_per_1k_tokens: float = 0.00059
    worker_cost_per_1k_tokens: float = 0.00018
    
    @property
    def database_url(self) -> str:
        """Construct SQLite database URL."""
        db_path = Path(self.db_file).absolute()
        return f"sqlite:///{db_path}"
    
    @property
    def effective_orchestrator_interval(self) -> int:
        return self.demo_orchestrator_interval_seconds if self.demo_mode else self.orchestrator_interval_seconds
    
    @property
    def effective_worker_interval(self) -> int:
        return self.demo_worker_interval_seconds if self.demo_mode else self.worker_interval_seconds


# Export as settings for drop-in replacement
settings = LocalSettings()