from pydantic import Field
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Setting(BaseSettings):
    mongo_url: str = Field(..., alias="MONGO_URL")
    mongo_database: str = Field(..., alias="MONGO_DATABASE")
    jwt_secret_key: str = Field(..., alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALG")
    acces_token_expire_minutes: int = Field(default=60 * 24, alias="JWT_EXPIRES_MIN")
    PROJECT_NAME: str = "Examen 1"
    
    model_config = SettingsConfigDict(
    env_file=Path(__file__).resolve().parent / ".env"
)



setting = Setting()
