from pydantic import PostgresDsn, AmqpDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.constants import Environment, Business

class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: PostgresDsn
    AMQP_URL: AmqpDsn
    REDIS_URL: RedisDsn
    OPENAI_API_KEY: str

    META_API_TOKEN: str
    META_API_VERSION: str
    META_VERIFY_TOKEN: str

    ENVIRONMENT:Environment = Environment.STAGING

    BUSINESS: Business = "HOTEL"

    BUSINESS_PHONE_ID: str

config = Config()