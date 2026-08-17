import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///wallet_analytics.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    TON_API_BASE_URL = os.environ.get("TON_API_BASE_URL", "https://toncenter.com/api/v2")

    PRICE_API_BASE_URL = "https://api.coingecko.com/api/v3"

    TON_API_TIMEOUT = int(os.environ.get("TON_API_TIMEOUT", "30"))
    TON_API_RETRIES = int(os.environ.get("TON_API_RETRIES", "3"))
    SYNC_STALE_SECONDS = int(os.environ.get("SYNC_STALE_SECONDS", "300"))

    NANO_TON = 1_000_000_000


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
