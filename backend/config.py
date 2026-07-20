import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
GENERATED_APPS_DIR = BASE_DIR / "generated-apps"
LOGS_DIR = BASE_DIR / "logs"

GENERATED_APPS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", os.getenv("GEMINI_API_KEY", ""))
GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY", "")
GOOGLE_SEARCH_CX = os.getenv("GOOGLE_SEARCH_CX", "")

# Strategic Model Routing Architecture
FAST_MODEL = os.getenv("FAST_MODEL", "gemini-2.5-flash")
REASONING_MODEL = os.getenv("REASONING_MODEL", "gemini-2.5-pro")

def get_model_for_agent(agent_name: str) -> str:
    """
    Strategic model routing: Uses lightweight fast model for search query generation & discovery,
    and high-reasoning model for complex product ideation and code generation.
    """
    if agent_name in ["Discovery", "Search"]:
        return FAST_MODEL
    elif agent_name in ["MarketResearch", "Ideation", "Implementation"]:
        return REASONING_MODEL
    return FAST_MODEL
