"""ReviveAI Configuration — loaded from environment variables."""

from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_URL = f"sqlite+aiosqlite:///{(BASE_DIR / 'reviveai.db').as_posix()}"
DEFAULT_MODEL_PATH = str(BASE_DIR / "ml_artifacts" / "recovery_model.joblib")


class Settings(BaseSettings):
    # Application
    app_mode: str = Field(default="demo", description="'demo' or 'live'")
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    database_url: str = Field(default=DEFAULT_DB_URL)

    # LLM
    llm_provider: str = "openai"
    llm_api_key: Optional[str] = None
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"

    # Razorpay
    razorpay_key_id: Optional[str] = None
    razorpay_key_secret: Optional[str] = None
    razorpay_webhook_secret: Optional[str] = None

    # ML
    ml_model_path: str = Field(default=DEFAULT_MODEL_PATH)
    ml_random_seed: int = 42

    # Recovery Policy Limits
    max_automated_amount: float = 10000.0
    automated_retry_limit: int = 2
    min_auto_recovery_probability: float = 0.80
    min_nudge_probability: float = 0.55
    min_confidence: float = 0.60
    max_escalation_amount: float = 50000.0

    @property
    def has_llm(self) -> bool:
        return bool(self.llm_api_key)

    @property
    def has_razorpay(self) -> bool:
        return bool(self.razorpay_key_id and self.razorpay_key_secret)

    @property
    def is_demo_mode(self) -> bool:
        return self.app_mode == "demo" or not self.has_razorpay

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
