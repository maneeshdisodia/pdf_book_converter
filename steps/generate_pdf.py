"""Step 4: Generate PDF from HTML using WeasyPrint."""

import logging
from pathlib import Path

import weasyprint

logger = logging.getLogger(__name__)


def generate_pdf(html_path: Path, output_pdf_path: Path) -> None:
    """Convert styled HTML to PDF.

    Args:
        html_path: Path to the styled HTML file.
        output_pdf_path: Path for the output PDF.
    """
    logger.info("Generating PDF from HTML...")
    html = weasyprint.HTML(
        filename=str(html_path),
        base_url=str(html_path.parent),
    )
    html.write_pdf(str(output_pdf_path))
    logger.info(f"Saved English PDF: {output_pdf_path}")
