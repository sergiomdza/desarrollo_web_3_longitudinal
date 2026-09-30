
from pydantic_settings import BaseSettings,SettingsConfigDict

class Setting(BaseSettings):
    mongo_url : str 
    mongo_database : str 
    jwt_secret_key: str 
    jwt_algorithm: str = "HS256"
    acces_token_expire_minutes : int = 60 * 24
        
    model_config = SettingsConfigDict(env_file=".env")
    

setting = Setting()
