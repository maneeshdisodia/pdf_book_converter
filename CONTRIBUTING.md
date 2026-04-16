# Contributing to PDF Book Converter

Thanks for your interest in contributing! This guide will help you get started.

## Development Setup

```bash
git clone https://github.com/maneeshdisodia/pdf_book_converter.git
cd pdf_book_converter

# Install liteparse (PDF parser + OCR)
npm i -g @llamaindex/liteparse

# Python environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env
```

## Project Architecture

```
pipeline.py          ← CLI entry point, orchestrates the 4 steps
steps/
  parse_pdf.py       ← Wraps liteparse CLI for OCR + page screenshots
  translate.py       ← Two-pass Anthropic vision: extract figures, then translate
  build_html.py      ← Jinja2 template rendering
  generate_pdf.py    ← WeasyPrint HTML → PDF
templates/
  book.html          ← HTML/CSS template for book-like layout
```

### Data Flow

```
Input PDF
  → liteparse: OCR text (parsed.json) + page screenshots (images/page_N.png)
  → Pass 1 (Haiku vision): detect figure bounding boxes → crop from page scans
  → Pass 2 (Haiku vision): translate text + embed <img> tags for figures
  → Jinja2: wrap in styled HTML template
  → WeasyPrint: render to PDF
```

### Key Design Decisions

- **Why liteparse?** Lightweight Node.js tool (~70 packages). Alternatives like Docling pull in PyTorch + NVIDIA CUDA (1.7GB+).
- **Why vision-based translation?** The PDF is scanned — each page is one JPEG. Text extraction alone loses structure (columns merge, margin notes mix in). Vision models see the actual layout.
- **Why two-pass figure extraction?** Scanned PDFs have no separate image objects. We must crop screenshots from the page scan. Pass 1 gets bounding boxes, then PIL crops + trims to the actual UI window.
- **Why SAP glossary is conditional?** The tool supports any language. The SAP terminology glossary only activates when `--source-lang German` to avoid polluting prompts for other domains.

## Areas for Contribution

### Good First Issues

- **Add more language glossaries** — Add domain-specific terminology for other languages in `steps/translate.py` `GLOSSARIES` dict
- **Improve figure trimming** — The `_trim_to_sap_window()` function in `translate.py` works for SAP screenshots but could be more generic for other UI styles
- **Add progress bar** — Replace log output with `tqdm` or `rich` progress bars
- **Parallel page translation** — Pages are independent, could be translated concurrently with `asyncio`

### Larger Features

- **Local LLM support** — The codebase previously supported LM Studio (OpenAI-compatible API). Could be re-added as a `--provider local` flag
- **Target language selection** — Currently hardcoded to English output. Add `--target-lang` flag
- **Custom glossary file** — Accept a JSON/CSV glossary via `--glossary terms.json`
- **Better table detection** — Some text tables get lost. Could use liteparse bounding box data to improve table reconstruction

## How to Submit Changes

1. Fork the repo
2. Create a feature branch: `git checkout -b my-feature`
3. Make your changes
4. Test with a real PDF: `python pipeline.py test.pdf -o ./test_output`
5. Commit with a clear message
6. Push and open a Pull Request

## Testing

There's no automated test suite yet (contributions welcome!). To verify your changes:

```bash
# Full pipeline test
python pipeline.py your_book.pdf -o ./test_out

# Skip parse (reuse existing OCR data — faster iteration)
python pipeline.py your_book.pdf -o ./test_out --skip-parse

# Skip translate (just rebuild HTML/PDF from cached translations)
python pipeline.py your_book.pdf -o ./test_out --skip-parse --skip-translate

# Verify help text
python pipeline.py --help
```

## Code Style

- Python 3.10+, type hints where helpful
- Keep functions focused — one job per function
- Log meaningful progress messages via `logging`
- No unnecessary abstractions — this is a pipeline, not a framework
