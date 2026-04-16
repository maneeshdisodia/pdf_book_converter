"""Step 3: Build styled HTML from translated pages."""

import logging
from pathlib import Path
from typing import List

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)


def build_html(translated_pages: List[dict], template_dir: Path,
               output_dir: Path) -> str:
    """Build styled HTML document from translated page HTML fragments.

    Args:
        translated_pages: List of dicts with page number and html content.
        template_dir: Jinja2 templates directory.
        output_dir: Output directory.

    Returns:
        Path to the generated HTML file.
    """
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("book.html")

    styled_html = template.render(
        title="Sales with SAP S/4HANA &ndash; The Practice Handbook",
        pages=translated_pages,
    )

    output_path = output_dir / "book_english.html"
    output_path.write_text(styled_html, encoding="utf-8")
    logger.info(f"Saved English HTML: {output_path}")

    return str(output_path)
