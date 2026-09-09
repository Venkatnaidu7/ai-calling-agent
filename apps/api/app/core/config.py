from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = 'ai-voice-platform'
    app_env: str = 'development'
    api_host: str = '0.0.0.0'
    api_port: int = 8000
    secret_key: str = 'change-me'
    database_url: str = 'postgresql+asyncpg://voice:voice@localhost:5432/voice'
    redis_url: str = 'redis://localhost:6379/0'
    public_base_url: str = 'http://localhost:8000'
    frontend_url: str = 'http://localhost:3000'
    cors_origins: str = 'http://localhost:3000'
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_region: str = 'us1'
    openai_api_key: str | None = None
    openai_realtime_model: str = 'gpt-realtime-2.1'
    openai_realtime_url: str = 'wss://api.openai.com/v1/realtime'
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    aws_region: str = 'ap-south-1'
    s3_bucket: str | None = None
    aws_secrets_manager_name: str | None = None
    max_call_duration_seconds: int = 3600
    outbound_enabled: bool = False
    recording_mode: str = 'DISABLED'

    model_config = SettingsConfigDict(env_file='.env', extra='ignore', case_sensitive=False)


@lru_cache
def get_settings():
    return Settings()
