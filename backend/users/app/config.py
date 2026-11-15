from pydantic import Field
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Setting(BaseSettings):
    mongo_url: str = Field(..., alias="MONGO_URL")
    mongo_database: str = Field(..., alias="MONGO_DATABASE")
    PROJECT_NAME: str = "Examen 1"

    # Authentication
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    
    model_config = SettingsConfigDict(
    env_file=Path(__file__).resolve().parent / ".env"
)



setting = Setting()
