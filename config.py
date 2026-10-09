from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="AGENT_",
        extra="ignore",
    )

    server_url: AnyHttpUrl
    request_timeout_seconds: float = Field(default=1.0, gt=0)
    send_interval_seconds: float = Field(default=1.0, gt=0)
    cpu_sample_interval_seconds: float = Field(default=0.5, ge=0)
    disk_path: str = "/"


class ServerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SERVER_",
        extra="ignore",
    )

    allowed_ips: list[str] = Field(default_factory=list)
    database_path: str = "metrics.db"
    offline_threshold_seconds: float = Field(default=30.0, gt=0)
