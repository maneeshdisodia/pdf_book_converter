#!/usr/bin/env python3
"""
PDF Book Converter — Convert scanned PDF books to English with preserved formatting.

Usage:
    python pipeline.py book.pdf
    python pipeline.py book.pdf -o ./my_output
    python pipeline.py book.pdf --source-lang French --ocr-lang fra
    python pipeline.py book.pdf --skip-parse --skip-translate
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional

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


def main():
    parser = argparse.ArgumentParser(
        prog="pdf-book-converter",
        description="Convert scanned PDF books to English HTML + PDF with preserved formatting.",
        epilog="Set ANTHROPIC_API_KEY in your environment or .env file.",
    )
    parser.add_argument(
        "input", type=Path,
        help="Path to the input PDF file",
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("./output"),
        help="Output directory (default: ./output)",
    )
    parser.add_argument(
        "--source-lang", default=os.environ.get("SOURCE_LANG", "German"),
        help="Source language of the PDF (default: German)",
    )
    parser.add_argument(
        "--ocr-lang", default=os.environ.get("OCR_LANG", "deu"),
        help="OCR language code for liteparse, e.g. deu, fra, spa (default: deu)",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
        help="Anthropic model ID (default: claude-haiku-4-5-20251001)",
    )
    parser.add_argument(
        "--title", default=None,
        help="Book title for the output HTML (default: auto-generated from filename)",
    )
    parser.add_argument(
        "--temperature", type=float,
        default=float(os.environ.get("TRANSLATION_TEMPERATURE", "0.1")),
        help="LLM temperature for translation (default: 0.1)",
    )
    parser.add_argument(
        "--skip-parse", action="store_true",
        help="Skip PDF parsing, reuse existing screenshots and OCR data",
    )
    parser.add_argument(
        "--skip-translate", action="store_true",
        help="Skip translation, rebuild HTML/PDF from existing translations",
    )
    args = parser.parse_args()

    # Validate input
    if not args.input.exists():
        logger.error(f"Input file not found: {args.input}")
        sys.exit(1)

    # API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key and not args.skip_translate:
        logger.error(
            "ANTHROPIC_API_KEY not set. "
            "Export it or add it to a .env file. "
            "See .env.example for reference."
        )
        sys.exit(1)

    # Setup directories
    output_dir = args.output.resolve()
    image_dir = output_dir / "images"
    template_dir = Path(__file__).parent / "templates"
    parsed_json = output_dir / "parsed.json"
    translations_path = output_dir / "translations.json"

    output_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)

    # Auto-generate title from filename if not provided
    title = args.title or args.input.stem.replace("-", " ").replace("_", " ").title()

    start = time.time()

    # --- Step 1: Parse PDF ---
    logger.info("=" * 50)
    logger.info("STEP 1: Parse PDF with liteparse")
    logger.info("=" * 50)
    if args.skip_parse and parsed_json.exists():
        logger.info("Loading existing parsed data...")
        with open(parsed_json, "r", encoding="utf-8") as f:
            parsed_data = json.load(f)
    else:
        parsed_data = parse_pdf(
            args.input.resolve(), output_dir, image_dir, ocr_lang=args.ocr_lang,
        )

    total_pages = len(parsed_data["pages"])
    logger.info(f"Total pages: {total_pages}")

    # --- Step 2: Extract figures + Translate ---
    logger.info("=" * 50)
    logger.info("STEP 2: Translate via Anthropic vision")
    logger.info(f"  Model: {args.model}")
    logger.info(f"  Source language: {args.source_lang}")
    logger.info("=" * 50)

    if args.skip_translate and translations_path.exists():
        logger.info("Loading existing translations...")
        with open(translations_path, "r", encoding="utf-8") as f:
            translated_pages = json.load(f)
    else:
        translated_pages = translate_pages(
            image_dir=image_dir,
            total_pages=total_pages,
            api_key=api_key,
            output_image_dir=image_dir,
            model=args.model,
            temperature=args.temperature,
            source_lang=args.source_lang,
        )
        with open(translations_path, "w", encoding="utf-8") as f:
            json.dump(translated_pages, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved translations to {translations_path}")

    # --- Step 3: Build HTML ---
    logger.info("=" * 50)
    logger.info("STEP 3: Build styled HTML")
    logger.info("=" * 50)
    html_path = build_html(translated_pages, template_dir, output_dir, title=title)

    # --- Step 4: Generate PDF ---
    logger.info("=" * 50)
    logger.info("STEP 4: Generate PDF")
    logger.info("=" * 50)
    pdf_path = output_dir / "book_english.pdf"
    generate_pdf(Path(html_path), pdf_path)

    elapsed = time.time() - start
    logger.info("=" * 50)
    logger.info(f"DONE in {elapsed:.1f}s")
    logger.info(f"  HTML: {output_dir / 'book_english.html'}")
    logger.info(f"  PDF:  {pdf_path}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
