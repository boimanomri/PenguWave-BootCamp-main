from urllib.parse import quote_plus

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mongo_user: str
    mongo_password: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 8
    api_key: str
    cors_origin: str = "http://localhost:5173"

    @computed_field
    @property
    def mongo_uri(self) -> str:
        user = quote_plus(self.mongo_user)
        pwd = quote_plus(self.mongo_password)
        return f"mongodb://{user}:{pwd}@127.0.0.1:27017/penguwave?authSource=admin"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
