from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str = "postgresql+asyncpg://ems:ems@localhost:5432/ems"

    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    mqtt_topic_prefix: str = "ems"

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    poll_interval: int = 5
    acquisition_mode: str = "simulator"  # simulator | modbus
    modbus_timeout: float = 2.0

    offline_warning_seconds: int = 30
    offline_critical_seconds: int = 180

    @field_validator("mqtt_username", "mqtt_password", mode="before")
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        if value == "":
            return None
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
