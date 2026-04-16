"""Step 2: Extract figures and translate PDF pages using Anthropic Haiku 4.5 vision."""

import base64
import io
import json
import logging
import re
from pathlib import Path
from typing import List

import anthropic
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# --- Pass 1: Figure extraction prompt ---

FIGURE_EXTRACTION_PROMPT = """This image is {W}x{H} pixels. It shows a scanned book page (possibly a two-page spread).

Find ALL screenshots, dialog windows, application UI, diagrams, flowcharts, and illustrations embedded within the text. These are visual elements that look distinct from body text — they may have toolbars, borders, input fields, charts, etc.

Return TIGHT pixel coordinates for each visual element. The crop should contain ONLY the visual element — no surrounding body text, no figure captions below.

JSON format:
[{{"id": "fig1", "type": "screenshot"|"diagram", "desc_en": "brief English description for tooltip", "caption_en": "Figure X.X English Caption", "x1": int, "y1": int, "x2": int, "y2": int}}]

Coordinates in pixels of the {W}x{H} image. If no figures found, return [].
Return ONLY valid JSON."""

# --- Pass 2: Translation prompt ---

TRANSLATION_PROMPT_TEMPLATE = """You are a professional translator converting a {source_lang} book page into structured English HTML.

You will receive:
1. An image of the book page
2. A list of figures already extracted as separate images from this page

Your job:
1. Translate ALL {source_lang} text to English
2. Output clean, semantic HTML preserving the document structure
3. For each figure, insert the provided <img> tag at the correct position in the text flow

HTML rules:
- Chapter titles: <h1>
- Section headings (e.g. "11.1 ..."): <h2>
- Sub-section headings: <h3>
- Body paragraphs: <p>
- Bullet lists: <ul><li>
- Numbered lists: <ol><li>
- Tables (text-based only): <table> with <thead>/<tbody>/<tr>/<th>/<td>
- Margin notes / side annotations: <aside class="margin-note">
- Bold text: <strong>, Italic: <em>
- Page numbers: SKIP
- Running headers/footers: SKIP

FIGURES — CRITICAL:
- For each figure in the list below, output EXACTLY:
  <figure>
    <img src="SRC" title="TITLE">
    <figcaption>CAPTION</figcaption>
  </figure>
- Place the <figure> where the image appears in the page flow
- NEVER describe a screenshot in text — ALWAYS use the <img> tag
- Use the EXACT src, title, and caption provided below
{glossary}
Output ONLY HTML content (no fences, no wrappers)."""

# Domain-specific glossaries (added to the translation prompt when source_lang matches)
GLOSSARIES = {
    "German": """
SAP terminology (use these English terms):
- Vertrieb = Sales and Distribution
- Fakturierung/Faktura = Billing/Invoice
- Fakturierungsplan = Billing Plan
- Anzahlung = Down Payment
- Endrechnung = Final Invoice
- Kundenauftrag = Sales Order
- Stammdaten = Master Data
- Buchungssatz = Posting Entry
- Debitorenkonto = Customer Account
- Forderungen = Receivables
- Mehrwertsteuer = VAT
- Sonderhauptbuch = Special G/L
- Anzahlungsanforderung = Down Payment Request
- Anzahlungsabwicklung = Down Payment Processing
- Teilfakturierung = Partial Billing
- Periodische Fakturierung = Periodic Billing
- Keep SAP product names as-is: SAP S/4HANA, Fiori, etc.
- Keep transaction codes as-is: VA01, VF01, VL01N, SPRO, etc.""",
}


def _build_translation_prompt(source_lang: str) -> str:
    """Build the translation system prompt for the given source language."""
    glossary = GLOSSARIES.get(source_lang, "")
    return TRANSLATION_PROMPT_TEMPLATE.format(
        source_lang=source_lang,
        glossary=glossary,
    )


def _encode_image(img: Image.Image, max_width: int = 1500) -> tuple[str, str, float]:
    """Resize and encode image, return (base64, media_type, scale_factor)."""
    scale = 1.0
    if img.width > max_width:
        scale = max_width / img.width
        img = img.resize((max_width, int(img.height * scale)))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode(), "image/jpeg", scale


def _trim_to_sap_window(img: Image.Image) -> Image.Image:
    """Trim text above a SAP screenshot by finding the SAP title bar.

    Looks for the SAP logo (dark blue/green pixels in the left portion)
    and trims everything above it.
    """
    arr = np.array(img.convert("RGB"))
    h, w = arr.shape[:2]

    # Scan from top to find first row with SAP logo colors
    for y in range(min(h, h // 2)):  # Only check top half
        left = arr[y, : min(300, w // 3)]
        # SAP logo: dark pixels with blue component (R<120, B>60)
        dark_blue = ((left[:, 0] < 120) & (left[:, 2] > 60)).sum()
        if dark_blue > 10:
            trim_y = max(0, y - 2)
            return img.crop((0, trim_y, w, h))

    # For diagrams: try finding the top border line (dark horizontal line)
    for y in range(min(h, h // 3)):
        row = arr[y]
        dark_pixels = (row.mean(axis=1) < 100).sum()
        if dark_pixels > w * 0.3:  # 30% of row is dark = likely a border
            trim_y = max(0, y - 2)
            return img.crop((0, trim_y, w, h))

    return img  # No trimming needed


def _trim_bottom_caption(img: Image.Image) -> Image.Image:
    """Trim caption text below a SAP screenshot by finding the window bottom edge."""
    arr = np.array(img.convert("RGB"))
    h, w = arr.shape[:2]

    # Scan from bottom up: find where the white/light background of the SAP window ends
    for y in range(h - 1, max(h // 2, 0), -1):
        row = arr[y]
        # SAP window interior is mostly white/light gray
        light_ratio = (row.mean(axis=1) > 200).sum() / w
        if light_ratio > 0.6:
            # Found the bottom of the window content
            return img.crop((0, 0, w, min(h, y + 5)))

    return img


def extract_figures(
    page_num: int,
    image_path: Path,
    output_image_dir: Path,
    client: anthropic.Anthropic,
    model: str,
) -> List[dict]:
    """Extract figure bounding boxes and crop clean screenshots."""
    full_img = Image.open(image_path).convert("RGB")
    W, H = full_img.size

    # Encode for API
    b64, media_type, scale = _encode_image(full_img)
    prompt = FIGURE_EXTRACTION_PROMPT.format(W=int(W * scale), H=int(H * scale))

    response = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        temperature=0,
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```\w*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

    try:
        figures = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(f"Page {page_num}: could not parse figure JSON")
        return []

    if not figures:
        return []

    results = []
    for i, fig in enumerate(figures):
        # Scale pixel coordinates back to full resolution
        x1 = int(fig["x1"] / scale)
        y1 = int(fig["y1"] / scale)
        x2 = int(fig["x2"] / scale)
        y2 = int(fig["y2"] / scale)

        # Validate
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(W, x2), min(H, y2)
        if x2 <= x1 or y2 <= y1 or (x2 - x1) < 50 or (y2 - y1) < 50:
            logger.warning(f"Page {page_num}, fig {i}: invalid bbox, skipping")
            continue

        # Rough crop
        cropped = full_img.crop((x1, y1, x2, y2))

        # Smart trim: remove text above SAP window
        fig_type = fig.get("type", "sap_screenshot")
        if fig_type == "sap_screenshot":
            cropped = _trim_to_sap_window(cropped)
            cropped = _trim_bottom_caption(cropped)

        fig_filename = f"page_{page_num}_fig_{i + 1}.png"
        fig_path = output_image_dir / fig_filename
        cropped.save(str(fig_path))

        results.append({
            "src": f"images/{fig_filename}",
            "caption": fig.get("caption_en", ""),
            "description": fig.get("desc_en", ""),
        })

    logger.info(f"Page {page_num}: extracted {len(results)} figures")
    return results


def translate_page_with_vision(
    page_num: int,
    image_path: Path,
    figures: List[dict],
    client: anthropic.Anthropic,
    model: str,
    temperature: float = 0.1,
    source_lang: str = "German",
) -> str:
    """Translate a page, embedding extracted figure references."""
    full_img = Image.open(image_path).convert("RGB")
    b64, media_type, _ = _encode_image(full_img, max_width=1200)

    if figures:
        fig_lines = ["EXTRACTED FIGURES (use these exact values in your HTML):"]
        for i, fig in enumerate(figures, 1):
            fig_lines.append(
                f'{i}. <figure><img src="{fig["src"]}" title="{fig["description"]}"><figcaption>{fig["caption"]}</figcaption></figure>'
            )
        fig_info = "\n".join(fig_lines)
    else:
        fig_info = "NO FIGURES on this page — only text content."

    system_prompt = _build_translation_prompt(source_lang)

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                    {"type": "text", "text": f"Page {page_num}. Translate to English HTML.\n\n{fig_info}"},
                ],
            }
        ],
        temperature=temperature,
    )

    html = response.content[0].text
    if html.startswith("```"):
        lines = html.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        html = "\n".join(lines)

    return html


def translate_pages(
    image_dir: Path,
    total_pages: int,
    api_key: str,
    output_image_dir: Path,
    model: str = "claude-haiku-4-5-20251001",
    temperature: float = 0.1,
    source_lang: str = "German",
) -> List[dict]:
    """Two-pass: extract figures, then translate with image references."""
    client = anthropic.Anthropic(api_key=api_key)
    results = []

    for page_num in range(1, total_pages + 1):
        image_path = image_dir / f"page_{page_num}.png"
        if not image_path.exists():
            logger.warning(f"Page {page_num}: image not found, skipping")
            results.append({"page": page_num, "html": ""})
            continue

        # Pass 1: Extract figures
        logger.info(f"Page {page_num}/{total_pages}: extracting figures...")
        try:
            figures = extract_figures(page_num, image_path, output_image_dir, client, model)
        except Exception as e:
            logger.error(f"Page {page_num}: figure extraction failed - {e}")
            figures = []

        # Pass 2: Translate with figure references
        logger.info(f"Page {page_num}/{total_pages}: translating ({len(figures)} figures)...")
        try:
            html = translate_page_with_vision(
                page_num, image_path, figures, client, model, temperature, source_lang
            )
            logger.info(f"Page {page_num}: got {len(html)} chars of HTML")
            results.append({"page": page_num, "html": html, "figures": figures})
        except Exception as e:
            logger.error(f"Page {page_num}: translation failed - {e}")
            results.append({
                "page": page_num,
                "html": f"<p><em>Translation failed for page {page_num}: {e}</em></p>",
                "figures": figures,
            })

    return results
