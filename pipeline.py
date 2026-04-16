#!/usr/bin/env python3
"""PDF Book Converter: German to English with formatting preservation.

Pipeline: liteparse (screenshots) -> Haiku 4.5 vision (structured HTML + translate) -> WeasyPrint (PDF)

Usage:
    python pipeline.py
    python pipeline.py --skip-parse         # Reuse existing screenshots
    python pipeline.py --skip-translate      # Reuse existing translations
    python pipeline.py --model MODEL_ID      # Override model (default: claude-haiku-4-5-20251001)
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

from config import (
    INPUT_PDF, OUTPUT_DIR, IMAGE_DIR, TEMPLATE_DIR, PARSED_JSON,
    TRANSLATION_TEMPERATURE,
)
from steps.parse_pdf import parse_pdf
from steps.translate import translate_pages
from steps.build_html import build_html
from steps.generate_pdf import generate_pdf

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-haiku-4-5-20251001"


def main():
    parser = argparse.ArgumentParser(description="Convert German PDF to English HTML+PDF")
    parser.add_argument("--skip-parse", action="store_true", help="Reuse existing parsed data/screenshots")
    parser.add_argument("--skip-translate", action="store_true", help="Reuse existing translations")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Anthropic model ID (default: {DEFAULT_MODEL})")
    parser.add_argument("--input", type=Path, default=INPUT_PDF, help="Input PDF path")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key and not args.skip_translate:
        logger.error("ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    start = time.time()

    # Step 1: Parse PDF with liteparse
    logger.info("=" * 50)
    logger.info("STEP 1: Parse PDF with liteparse")
    logger.info("=" * 50)
    if args.skip_parse and PARSED_JSON.exists():
        logger.info("Loading existing parsed data...")
        with open(PARSED_JSON, "r", encoding="utf-8") as f:
            parsed_data = json.load(f)
    else:
        parsed_data = parse_pdf(args.input, OUTPUT_DIR, IMAGE_DIR)

    total_pages = len(parsed_data["pages"])
    logger.info(f"Total pages: {total_pages}")

    # Step 2: Translate using Haiku 4.5 vision
    translations_path = OUTPUT_DIR / "translations.json"
    logger.info("=" * 50)
    logger.info("STEP 2: Translate pages via Anthropic Haiku 4.5")
    logger.info(f"  Model: {args.model}")
    logger.info("=" * 50)

    if args.skip_translate and translations_path.exists():
        logger.info("Loading existing translations...")
        with open(translations_path, "r", encoding="utf-8") as f:
            translated_pages = json.load(f)
    else:
        translated_pages = translate_pages(
            IMAGE_DIR, total_pages, api_key, IMAGE_DIR, args.model, TRANSLATION_TEMPERATURE,
        )
        with open(translations_path, "w", encoding="utf-8") as f:
            json.dump(translated_pages, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved translations to {translations_path}")

    # Step 3: Build styled HTML
    logger.info("=" * 50)
    logger.info("STEP 3: Build styled HTML")
    logger.info("=" * 50)
    html_path = build_html(translated_pages, TEMPLATE_DIR, OUTPUT_DIR)

    # Step 4: Generate PDF
    logger.info("=" * 50)
    logger.info("STEP 4: Generate PDF")
    logger.info("=" * 50)
    pdf_path = OUTPUT_DIR / "book_english.pdf"
    generate_pdf(Path(html_path), pdf_path)

    elapsed = time.time() - start
    logger.info("=" * 50)
    logger.info(f"DONE in {elapsed:.1f}s")
    logger.info(f"  HTML: {OUTPUT_DIR / 'book_english.html'}")
    logger.info(f"  PDF:  {pdf_path}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
