from enum import Enum
from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvironmentEnum(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION ="production"
    TESTING = "testing"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", frozen=True
    )
    
    frontend_url: str = "http://127.0.0.1:8000"
    environment: EnvironmentEnum = EnvironmentEnum.DEVELOPMENT
    
    database_uri: str

    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15

    reset_token_expire_minutes: int = 60

    mail_server: str = "localhost"
    mail_port: int = 587
    mail_username: str
    mail_password: SecretStr = SecretStr("")
    mail_from: str = "noreply@fastpai.com"
    mail_use_tls: bool = False

    max_upload_size_bytes: int = 5 * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
