"""Configuration for PDF Book Converter."""

from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
IMAGE_DIR = OUTPUT_DIR / "images"
TEMPLATE_DIR = BASE_DIR / "templates"
PARSED_JSON = OUTPUT_DIR / "parsed.json"

# Default input PDF (override with --input flag)
INPUT_PDF = BASE_DIR / "input.pdf"

# LM Studio endpoint (optional, for local LLM usage)
LM_STUDIO_BASE_URL = "http://127.0.0.1:1234/v1"
LM_STUDIO_MODEL = "gemma-4-26b"

# Translation settings
TRANSLATION_TEMPERATURE = 0.1
