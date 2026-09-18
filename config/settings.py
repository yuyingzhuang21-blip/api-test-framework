from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    api_base_url: str = "https://reqres.in/api"
    api_timeout: int = 10
    api_retry_count: int = 3
    log_level: str = "INFO"
    performance_threshold_ms: int = 5000
    game_api_base_url: str = "http://127.0.0.1:8000"
    reqres_api_key: str = ""
  


settings = Settings()