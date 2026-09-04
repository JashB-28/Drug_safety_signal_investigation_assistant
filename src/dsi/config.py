"""Runtime configuration, read from environment (.env) with safe defaults.

No secrets live in source. The system uses only local/open resources, so an
openFDA key is optional (dev-time rate limits only) and absent by default.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

# Load .env if present; real secrets are never committed (see .gitignore).
load_dotenv()

# Repository root = two levels up from this file (src/dsi/config.py -> repo root).
REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseModel):
    """Immutable settings snapshot for a process."""

    model_config = {"frozen": True}

    ollama_host: str = "http://localhost:11434"
    model_tag: str = "mistral:7b-instruct"

    openfda_base_url: str = "https://api.fda.gov"
    openfda_api_key: str | None = None  # optional; dev-time rate limits only
    pubmed_base_url: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    db_path: Path = REPO_ROOT / "data" / "db" / "dsi.sqlite"
    cache_dir: Path = REPO_ROOT / "data" / "cache"


def get_settings() -> Settings:
    """Build settings from the current environment."""
    return Settings(
        ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        model_tag=os.getenv("DSI_MODEL_TAG", "mistral:7b-instruct"),
        openfda_base_url=os.getenv("OPENFDA_BASE_URL", "https://api.fda.gov"),
        openfda_api_key=os.getenv("OPENFDA_API_KEY") or None,
        pubmed_base_url=os.getenv("PUBMED_BASE_URL", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"),
        db_path=Path(os.getenv("DSI_DB_PATH", str(REPO_ROOT / "data" / "db" / "dsi.sqlite"))),
        cache_dir=Path(os.getenv("DSI_CACHE_DIR", str(REPO_ROOT / "data" / "cache"))),
    )
