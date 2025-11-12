from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "YOUR_DB_NAME"
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "YOUR_DB_PASSWORD"
    
    class Config:
        env_file = ".env"

settings = Settings()