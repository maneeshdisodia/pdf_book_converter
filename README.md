# PDF Book Converter

Convert scanned PDF books from any language to English while preserving formatting, layout, and embedded images.

Built for technical books with complex layouts — tables, margin notes, screenshots, diagrams, numbered lists, and multi-column spreads.

## How It Works

```
PDF ──> liteparse (OCR + screenshots) ──> Claude Haiku 4.5 (extract figures + translate) ──> HTML + PDF
```

1. **Parse** — [liteparse](https://github.com/run-llama/liteparse) extracts text via OCR and generates page screenshots
2. **Extract figures** — Claude Haiku 4.5 identifies screenshots/diagrams on each page and crops them from the page scan
3. **Translate** — Same vision model reads each page and produces structured English HTML, embedding cropped figures as `<img>` tags with hover tooltips
4. **Generate** — Jinja2 assembles styled HTML, WeasyPrint renders to PDF

## Quickstart

### Prerequisites

- **Node.js 18+** (for liteparse)
- **Python 3.10+**
- **Anthropic API key** — [get one here](https://console.anthropic.com/)

### Install

```bash
git clone https://github.com/maneeshdisodia/pdf_book_converter.git
cd pdf_book_converter

# Install liteparse
npm i -g @llamaindex/liteparse

# Setup Python environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### Run

```bash
# Convert a German PDF (default)
python pipeline.py my_book.pdf

# Specify output directory
python pipeline.py my_book.pdf -o ./translated

# Convert a French book
python pipeline.py livre.pdf --source-lang French --ocr-lang fra

# Convert a Spanish book
python pipeline.py libro.pdf --source-lang Spanish --ocr-lang spa
```

### Output

```
output/
├── book_english.html     # Styled HTML with embedded images + hover tooltips
├── book_english.pdf      # PDF version
├── translations.json     # Cached translations (for re-runs)
├── parsed.json           # Cached OCR data
└── images/               # Page screenshots + cropped figures
```

## CLI Options

```
python pipeline.py --help

positional arguments:
  input                 Path to the input PDF file

options:
  -o, --output DIR      Output directory (default: ./output)
  --source-lang LANG    Source language (default: German)
  --ocr-lang CODE       OCR language code (default: deu)
  --model MODEL         Anthropic model ID (default: claude-haiku-4-5-20251001)
  --title TITLE         Book title for output HTML
  --temperature FLOAT   Translation temperature (default: 0.1)
  --skip-parse          Reuse existing OCR data and screenshots
  --skip-translate      Reuse existing translations, rebuild HTML/PDF only
```

## Configuration

All settings can be configured via environment variables or a `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | (required) | Your Anthropic API key |
| `ANTHROPIC_MODEL` | `claude-haiku-4-5-20251001` | Model for translation |
| `SOURCE_LANG` | `German` | Source language of the PDF |
| `OCR_LANG` | `deu` | OCR language code |
| `TRANSLATION_TEMPERATURE` | `0.1` | Lower = more consistent |

CLI flags override environment variables.

## Cost

Using Claude Haiku 4.5 (~$0.80/M input, $4/M output):

| Pages | Time | Cost |
|-------|------|------|
| 10 | ~2 min | ~$0.10 |
| 28 | ~6 min | ~$0.30 |
| 100 | ~20 min | ~$1.00 |

## Features

- Preserves document structure: headings, paragraphs, lists, tables, margin notes
- Extracts screenshots/figures as actual images (not text descriptions)
- Hover tooltips on images with English descriptions
- Book-like CSS layout with margin notes
- Built-in SAP terminology glossary (for German technical books)
- Supports any source language via `--source-lang` and `--ocr-lang`
- Skip flags to resume interrupted runs

## Project Structure

```
pdf-book-converter/
├── pipeline.py              # CLI entry point
├── requirements.txt         # Python dependencies
├── .env.example             # Configuration template
├── steps/
│   ├── parse_pdf.py         # liteparse wrapper
│   ├── translate.py         # Claude vision (figure extraction + translation)
│   ├── build_html.py        # Jinja2 HTML assembly
│   └── generate_pdf.py      # WeasyPrint PDF generation
└── templates/
    └── book.html            # HTML template with book CSS
```

## License

MIT
