# PDF Book Converter

Convert scanned PDF books from any language to English while preserving the original formatting, layout, and embedded images.

Built for technical books with complex layouts — tables, margin notes, SAP screenshots, diagrams, numbered lists, and multi-column spreads.

## How It Works

```
PDF ──> liteparse (OCR + screenshots) ──> Haiku 4.5 vision (translate + structure) ──> HTML + PDF
```

**4-step pipeline:**

1. **Parse** — [liteparse](https://github.com/run-llama/liteparse) extracts text (with OCR) and generates page screenshots
2. **Extract figures** — Anthropic Haiku 4.5 vision identifies SAP screenshots/diagrams on each page and crops them from the page scan
3. **Translate** — Same vision model reads each page image and produces structured English HTML, embedding the cropped figures as `<img>` tags with hover tooltips
4. **Generate** — Jinja2 assembles styled HTML, WeasyPrint renders to PDF

## Features

- Preserves document structure: headings, paragraphs, lists, tables, margin notes
- Extracts screenshots/figures as actual images (not text descriptions)
- Hover tooltips on images with English descriptions
- Book-like CSS layout with margin notes in a right gutter
- SAP-specific terminology glossary built into the translation prompt
- Supports any source language (configured via the translation prompt)
- Skip flags to resume interrupted runs (`--skip-parse`, `--skip-translate`)

## Quickstart

### Prerequisites

- **Node.js** (for liteparse)
- **Python 3.10+**
- **Anthropic API key** ([get one here](https://console.anthropic.com/))

### Install

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/pdf-book-converter.git
cd pdf-book-converter

# Install liteparse (PDF parser + OCR)
npm i -g @llamaindex/liteparse

# Create Python virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install Python dependencies
pip install -r requirements.txt
```

### Run

```bash
# Set your Anthropic API key
export ANTHROPIC_API_KEY=sk-ant-...

# Convert a PDF
python pipeline.py --input /path/to/your/book.pdf
```

Output appears in `output/`:
- `book_english.html` — styled HTML with embedded images
- `book_english.pdf` — PDF version
- `images/` — page screenshots and cropped figures

### Options

```
python pipeline.py --help

Options:
  --input PATH          Input PDF file path
  --skip-parse          Reuse existing parsed data/screenshots
  --skip-translate      Reuse existing translations (rebuild HTML/PDF only)
  --model MODEL_ID      Anthropic model (default: claude-haiku-4-5-20251001)
```

## Configuration

Edit `config.py` to change defaults:

```python
OUTPUT_DIR = BASE_DIR / "output"       # Output directory
TRANSLATION_TEMPERATURE = 0.1          # Lower = more consistent translations
```

### Using a local LLM instead of Anthropic API

The pipeline also supports local LLMs via [LM Studio](https://lmstudio.ai/) (OpenAI-compatible API). See the `lm_studio` branch or modify `steps/translate.py` to use the `openai` client pointed at your local endpoint.

## Cost

Using Anthropic Haiku 4.5:
- ~$0.30 per 28-page book (figure extraction + translation)
- ~10 seconds per page
- Total: ~5-6 minutes for a full book

## Project Structure

```
pdf-book-converter/
├── pipeline.py              # Main entry point
├── config.py                # Configuration
├── requirements.txt         # Python dependencies
├── steps/
│   ├── parse_pdf.py         # liteparse wrapper (OCR + screenshots)
│   ├── translate.py         # Haiku 4.5 vision (figure extraction + translation)
│   ├── build_html.py        # Jinja2 HTML assembly
│   └── generate_pdf.py      # WeasyPrint PDF generation
├── templates/
│   └── book.html            # HTML template with book-like CSS
└── output/                  # Generated files (gitignored)
    ├── book_english.html
    ├── book_english.pdf
    ├── translations.json
    └── images/
```

## How the figure extraction works

Scanned PDFs have no separate image objects — each page is one large JPEG. The pipeline:

1. Sends each page screenshot to Haiku 4.5 and asks for bounding box coordinates of all SAP screenshots/diagrams
2. Crops those regions from the full-resolution page scan using PIL
3. Applies smart trimming: detects the SAP title bar (dark logo pixels) and trims any text that leaked into the crop
4. Saves clean cropped images and passes their paths to the translation step
5. The translation step outputs `<img src="..." title="English description">` tags at the correct positions

## License

MIT License — see [LICENSE](LICENSE).
