import os
from pathlib import Path
from dotenv import load_dotenv

# Search for .env in root or backend
root_dir = Path(__file__).resolve().parent.parent
env_path = root_dir / ".env"
load_dotenv(dotenv_path=env_path, override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
_env_model = os.getenv("GEMINI_MODEL", "")
GEMINI_MODEL = "gemini-3.6-flash" if not _env_model or "1.5" in _env_model else _env_model

LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID", "")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
LINKEDIN_ORGANIZATION_ID = os.getenv("LINKEDIN_ORGANIZATION_ID", "https://www.linkedin.com/company/aramata/")
PORT = int(os.getenv("PORT", 8000))

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
