import os
import sys
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PORT: int = 8000
    DB_PATH: str = "backend/db/assetvault.sqlite"
    SYSTEM_PASSWORD: str = "jd"
    
    @property
    def database_url(self) -> str:
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
            db_path = os.path.abspath(os.path.join(exe_dir, "db", "assetvault.sqlite"))
        else:
            db_path = os.path.abspath(self.DB_PATH)
            
        # Ensure parent directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        return f"sqlite:///{db_path}"

    class Config:
        env_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
        extra = "ignore"

settings = Settings()
