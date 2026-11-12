import os

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("API_KEY", "dev-key")
DB_URL = os.environ.get("DATABASE_URL", "sqlite:///./clinic.db")
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)
RATE_LIMIT = int(os.environ.get("RATE_LIMIT", "10"))
RATE_WINDOW = int(os.environ.get("RATE_WINDOW", "60"))
PING_URL = os.environ.get("RENDER_EXTERNAL_URL")
PING_EVERY = 600
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
