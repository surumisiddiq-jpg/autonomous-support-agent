import os
from pathlib import Path


def load_dotenv(path: Path) -> None:
    """Load basic .env values without requiring the optional python-dotenv package."""
    if not path.is_file():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)

# Locate project root and load env
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# filepath: C:\New folder\autonomous-support-agent\config\settings.py
class Settings:
    API_TOKEN: str = os.getenv("API_TOKEN", "")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    OLLAMA_BASE_URL: str = os.getenv(
        "OLLAMA_BASE_URL",
        "http://localhost:11434",
    )
    MAX_AUTO_REFUND_LIMIT: float = float(
        os.getenv("MAX_AUTO_REFUND_LIMIT", "100")
    )

    MOCK_DB_PATH: Path = BASE_DIR / "src" / "mock_db.json"
    AUDIT_LOG_PATH: Path = BASE_DIR / "src" / "audit.log"


settings = Settings()
