"""Parse PDF using liteparse CLI — extracts text via OCR and generates page screenshots."""

import json
import logging
import subprocess
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def find_lit_binary() -> str:
    """Find the liteparse 'lit' binary."""
    lit = shutil.which("lit")
    if lit:
        return lit
    home_lit = Path.home() / ".local" / "bin" / "lit"
    if home_lit.exists():
        return str(home_lit)
    raise FileNotFoundError(
        "'lit' binary not found. Install liteparse:\n"
        "  npm i -g @llamaindex/liteparse"
    )


def parse_pdf(
    input_pdf: Path,
    output_dir: Path,
    image_dir: Path,
    ocr_lang: str = "deu",
) -> dict:
    """Parse PDF with liteparse, generate screenshots, return parsed data.

    Args:
        input_pdf: Path to the input PDF.
        output_dir: Directory for output files.
        image_dir: Directory for page screenshots.
        ocr_lang: OCR language code (e.g. 'deu', 'fra', 'spa', 'eng').

    Returns:
        Parsed JSON data with pages and text items.
    """
    lit = find_lit_binary()
    output_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)

    json_output = output_dir / "parsed.json"
    text_output = output_dir / "parsed.txt"

    # Parse to JSON
    if not json_output.exists():
        logger.info(f"Parsing PDF to JSON (OCR language: {ocr_lang})...")
        subprocess.run(
            [lit, "parse", str(input_pdf), "--format", "json",
             "--ocr-language", ocr_lang, "-o", str(json_output)],
            check=True,
        )
    else:
        logger.info("Using existing parsed JSON")

    # Parse to text
    if not text_output.exists():
        logger.info("Parsing PDF to text...")
        subprocess.run(
            [lit, "parse", str(input_pdf), "--format", "text",
             "--ocr-language", ocr_lang, "-o", str(text_output)],
            check=True,
        )
    else:
        logger.info("Using existing parsed text")

    # Generate page screenshots
    if not any(image_dir.glob("page_*.png")):
        logger.info("Generating page screenshots...")
        subprocess.run(
            [lit, "screenshot", str(input_pdf), "-o", str(image_dir), "--dpi", "150"],
            check=True,
        )
    else:
        logger.info("Using existing page screenshots")

    with open(json_output, "r", encoding="utf-8") as f:
        data = json.load(f)

    logger.info(f"Parsed {len(data['pages'])} pages")
    return data
