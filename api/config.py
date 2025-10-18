from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "paper_rec_db"
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "your_password"
    
    class Config:
        env_file = ".env"

settings = Settings()