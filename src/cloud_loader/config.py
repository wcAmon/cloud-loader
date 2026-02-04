"""Application configuration."""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server
    host: str = "0.0.0.0"
    port: int = 8080
    base_url: str = "http://localhost:8080"

    # Storage
    upload_dir: Path = Path("./uploads")
    data_dir: Path = Path("./data")
    snapshots_dir: Path = Path("./data/snapshots")

    # Cloud Mover settings
    max_file_size_mb: int = 59
    expiry_hours: int = 24
    template_expiry_days: int = 7
    max_template_size_kb: int = 100

    # Loader Tracker API keys
    tavily_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def max_file_size_bytes(self) -> int:
        """Return max file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024

    @property
    def max_template_size_bytes(self) -> int:
        """Return max template size in bytes."""
        return self.max_template_size_kb * 1024

    @property
    def database_url(self) -> str:
        """Return SQLite database URL."""
        return f"sqlite:///{self.data_dir}/cloud_loader.db"


settings = Settings()
