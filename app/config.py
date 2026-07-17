import os
from pathlib import Path

from dotenv import load_dotenv


_ENV_LOADED = False


class Settings:
    """Meshy Text-to-3D 应用配置，从 .env 文件加载。"""

    MESHY_API_KEY: str = ""
    MESHY_API_BASE: str = "https://api.meshy.ai"
    MESHY_MODEL: str = "latest"  # meshy-4/meshy-5/meshy-6/latest

    def __init__(self):
        global _ENV_LOADED
        if not _ENV_LOADED:
            env_path = Path(__file__).resolve().parent.parent / ".env"
            load_dotenv(dotenv_path=env_path, override=True)
            _ENV_LOADED = True

        self.MESHY_API_KEY = os.getenv("MESHY_API_KEY", "")
        self.MESHY_API_BASE = os.getenv("MESHY_API_BASE", "https://api.meshy.ai")
        self.MESHY_MODEL = os.getenv("MESHY_MODEL", "latest")

        if not self.MESHY_API_KEY:
            print("ERROR: MESHY_API_KEY is required. Please set it in .env file.", flush=True)
            raise SystemExit(1)

    @property
    def masked_key(self) -> str:
        """脱敏后的 API key，用于日志。"""
        key = self.MESHY_API_KEY
        if len(key) <= 12:
            return key[:4] + "****"
        return key[:8] + "****" + key[-4:]


settings = Settings()
