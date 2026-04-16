# CLAUDE.md — Context for AI assistants working on this repo

## What this project does

Converts scanned PDF books from any language to English HTML + PDF, preserving formatting, layout, and embedded screenshots/figures.

## Architecture

4-step pipeline orchestrated by `pipeline.py`:

1. `steps/parse_pdf.py` — Calls liteparse CLI (Node.js) for OCR + page screenshots
2. `steps/translate.py` — Two Anthropic API calls per page:
   - **Pass 1**: Send page image, get JSON bounding boxes of figures/screenshots
   - **Pass 2**: Send page image + figure list, get structured English HTML with `<img>` tags
3. `steps/build_html.py` — Jinja2 renders translated pages into `templates/book.html`
4. `steps/generate_pdf.py` — WeasyPrint converts HTML to PDF

## Key files

- `pipeline.py` — CLI entry point with argparse. All config via CLI flags + env vars + `.env`
- `steps/translate.py` — Most complex file. Contains prompts, figure extraction with PIL cropping + SAP toolbar detection, and translation logic
- `templates/book.html` — Jinja2 HTML template with CSS for book layout (margin notes, figures, tables)
- `.env.example` — Template for API key and settings

## Important patterns

- **No config.py** — All config flows from CLI args and env vars. No hardcoded paths.
- **Source language is parameterized** — `--source-lang` and `--ocr-lang` flags. SAP glossary only activates for German.
- **Figure extraction uses smart trimming** — `_trim_to_sap_window()` detects dark logo pixels to crop text above screenshots. `_trim_bottom_caption()` trims captions below.
- **Skip flags** — `--skip-parse` and `--skip-translate` allow resuming interrupted runs or iterating on HTML/CSS without re-calling the API.
- **Translations are cached** — `output/translations.json` stores all translated HTML. Delete it to force re-translation.

## Dependencies

- **liteparse** (Node.js, installed globally via npm) — PDF parsing + OCR
- **anthropic** (Python) — Claude API for vision-based translation
- **Pillow + numpy** — Image cropping and SAP toolbar detection
- **jinja2** — HTML template rendering
- **weasyprint** — HTML to PDF conversion

## Common tasks

```bash
# Run full pipeline
python pipeline.py input.pdf -o ./output

# Iterate on HTML template only (no API calls)
python pipeline.py input.pdf --skip-parse --skip-translate

# Test figure extraction on one page
# (modify and run the extraction logic in translate.py directly)
```

## Things to watch out for

- WeasyPrint doesn't support `box-shadow` or `@media (max-width: ...)` — these are silently ignored in PDF output but work in browser HTML
- The figure bounding boxes from the LLM are sometimes loose — the trimming functions in translate.py compensate but aren't perfect
- Large pages (>4000px wide) should be resized before sending to the API to stay within token limits
