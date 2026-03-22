# anything2slides-skill

[中文](README.zh-CN.md) | [English](README.en.md)

`anything2slides-skill` is a reusable skill package that turns multiple source formats into editable, locally runnable Reveal.js presentations.

This project references and extends workflow ideas from [inhyeoklee/paper2slides-skill](https://github.com/inhyeoklee/paper2slides-skill), especially for the non-PPT branch inspired by a `paper2slides`-style extract-then-curate presentation workflow.

It has two operating modes:

- For `ppt` / `pptx`: reconstruct the original deck in HTML while preserving slide order and approximate layout
- For `pdf` / `text` / `html` / `md` / `docx`: extract text and visuals first, design a narrative second, and then generate a show-ready HTML deck

## What This Is

This repository contains a distributable skill package, a unified entrypoint, and two working conversion pipelines:

- `anything2slides.py`: unified entrypoint that routes by source file type
- `extract_pptx_bundle.py`: extracts structured content, notes, and media from `.pptx`
- `bootstrap_reveal_from_bundle.py`: builds a Reveal.js HTML deck from the PPTX bundle
- `extract_document_bundle.py`: extracts structured text and images from `pdf` / `docx` / `md` / `html` / `txt`
- `bootstrap_reveal_from_document_bundle.py`: builds a curated Reveal.js deck from the document bundle

Typical use cases:

- Convert an existing PowerPoint deck into a browser-presentable version
- Turn PDF, Markdown, Word, or HTML content into show-ready slides
- Produce an internal presentation demo that can be hosted on the web
- Convert documents into an HTML deck that AI or humans can continue editing
- Rebuild a PPT deck on the web while keeping the original page order and major visual structure

## Core Features

- Keeps original slide order for `ppt` / `pptx`
- Reconstructs PPT text and image positions using extracted geometry
- Extracts speaker notes and writes an editable notes document
- Copies embedded media into relative paths for local HTML playback
- Uses a `paper2slides`-style understand-plan-build flow for non-PPT sources
- Outputs a Reveal.js-style show-ready deck by default
- Keeps the generated result editable for later refinement
- Includes image zoom, lightbox, and presentation settings controls

## Compatibility

The project follows a standard local-skill directory structure:

- `SKILL.md`
- `agents/`
- `assets/`
- `references/`
- `scripts/`

That makes it usable not only in Codex, but also in other environments that support local skill directories, such as:

- OpenClaw
- Claw / claw-compatible environments
- Codex Desktop
- Codex CLI
- Claude Code
- Other local-skill-capable tooling

In other words, this is not tied to a single product-specific plugin format. It is a reusable skill package for agent and coding-assistant environments.

The repository does not currently provide standalone packaging for:

- PowerPoint plugins
- Browser extensions
- Cursor / VS Code marketplace plugins
- ChatGPT custom GPT plugin bundles

## Installation

### Python setup

This repository does not currently ship a separate `anything2slides-skill/library` Python package directory.

Instead, install the runtime dependencies directly:

```bash
python3 -m pip install beautifulsoup4 pymupdf
```

Requirements:

- Python 3.9 or newer
- `beautifulsoup4` for HTML parsing and document extraction
- `pymupdf` for PDF extraction
- LibreOffice is optional, but useful when you need to convert legacy `.ppt` files into `.pptx`

The version pushed to GitHub is intended to remain a source-only repository. It does not include an installed environment or generated packaging artifacts such as `build/`, `dist/`, `*.egg-info`, or `__pycache__/`.

### Option 1: Install into a compatible skill directory

Copy `anything2slides-skill/` into your skill search path.

For Codex-style environments, a common location is `~/.codex/skills`:

```bash
mkdir -p ~/.codex/skills
cp -R /path/to/anything2slides-skill/anything2slides-skill ~/.codex/skills/
```

The installed layout will usually look like:

```text
~/.codex/skills/anything2slides-skill/
├── SKILL.md
├── agents/
├── assets/
├── references/
└── scripts/
```

If your host environment needs a restart or skill reload, reopen the tool after copying.

### Option 2: Clone from GitHub and then install

```bash
git clone <your-github-repo-url>
mkdir -p ~/.codex/skills
cp -R anything2slides-skill/anything2slides-skill ~/.codex/skills/
```

## Requirements

- `python3` for the PPT/PPTX extraction flow
- Supported inputs:
  `ppt`, `pptx`, `pdf`, `txt`, `text`, `html`, `md`, `docx`

If the input is `.ppt`, convert it to `.pptx` first, for example:

```bash
libreoffice --headless --convert-to pptx --outdir "./converted" "./input.ppt"
```

## Usage

### Invoke it as a skill

You can ask an agent to use this skill directly, for example:

```text
Use $anything2slides-skill to turn this source material into a polished Reveal.js HTML presentation.
```

Example requests:

- Convert this PPT into HTML slides while preserving structure
- Turn this PDF into a presentation suitable for a report-out
- Build a show-ready slide deck from this Markdown document
- Turn this HTML page into a presentation with speaker-flow structure
- Output a locally openable, editable HTML presentation

### Run the scripts manually

The recommended starting point is the unified entrypoint:

```bash
python3 /path/to/anything2slides-skill/scripts/anything2slides.py \
  /path/to/input \
  /path/to/work/show_ready
```

It routes automatically:

- `ppt` / `pptx`: faithful PPT reconstruction
- `pdf` / `txt` / `html` / `md` / `docx`: document extraction plus narrative generation

You can also run each branch step by step.

### Branch A: PPT / PPTX

1. Extract the PPTX bundle

```bash
python3 /path/to/anything2slides-skill/scripts/extract_pptx_bundle.py \
  /path/to/input.pptx \
  /path/to/work/extracted
```

This creates:

- `manifest.json`
- `slides_outline.md`
- `media/`

2. Build the Reveal.js HTML deck

```bash
python3 /path/to/anything2slides-skill/scripts/bootstrap_reveal_from_bundle.py \
  /path/to/work/extracted \
  /path/to/work/show_ready
```

This creates:

- `show_ready/index.html`
- `show_ready/speaker_notes.md`
- `show_ready/assets/css/style.css`
- `show_ready/assets/media/`

### Branch B: PDF / Text / HTML / Markdown / DOCX

1. Extract the document bundle

```bash
python3 /path/to/anything2slides-skill/scripts/extract_document_bundle.py \
  /path/to/input.pdf \
  /path/to/work/document_bundle
```

This creates:

- `manifest.json`
- `source_outline.md`
- `media/`

2. Build the Reveal.js HTML deck

```bash
python3 /path/to/anything2slides-skill/scripts/bootstrap_reveal_from_document_bundle.py \
  /path/to/work/document_bundle \
  /path/to/work/show_ready
```

This creates:

- `show_ready/index.html`
- `show_ready/speaker_notes.md`
- `show_ready/assets/css/style.css`
- `show_ready/assets/media/`

## Output Layout

### Extraction outputs

```text
extracted/
├── manifest.json
├── slides_outline.md
└── media/
```

For document-style sources, the extraction directory looks like:

```text
document_bundle/
├── manifest.json
├── source_outline.md
└── media/
```

### Generated outputs

```text
show_ready/
├── index.html
├── speaker_notes.md
└── assets/
    ├── css/
    └── media/
```

## Workflow

### Branch A: PPT / PPTX

1. Extract text, notes, images, and geometry from `.pptx`
2. Build a structured `manifest.json`
3. Generate HTML slides from layout and media information
4. Keep the original slide count and overall arrangement
5. Output an editable Reveal.js deck and speaker notes

### Branch B: PDF / Text / HTML / Markdown / DOCX

1. Extract title, sections, paragraphs, and usable visuals
2. Decide what kind of presentation the source should become
3. Plan slide structure, pacing, and emphasis automatically
4. Generate HTML slides and speaker notes
5. Follow a `paper2slides`-style agent-driven workflow rather than page-faithful document reproduction

## Project Structure

```text
anything2slides-skill/
├── anything2slides-skill/
│   ├── SKILL.md
│   ├── agents/openai.yaml
│   ├── assets/
│   ├── references/
│   └── scripts/
```

Contents:

- `anything2slides-skill/SKILL.md`: main skill instructions and usage rules
- `anything2slides-skill/agents/openai.yaml`: host agent display configuration
- `anything2slides-skill/assets/`: HTML template, CSS, and speaker notes template
- `anything2slides-skill/references/output_contract.md`: extraction output contract
- `anything2slides-skill/scripts/`: unified entrypoint plus PPT and document conversion scripts

## Command Example

You can manually validate the PPT flow like this:

```bash
python3 anything2slides-skill/scripts/extract_pptx_bundle.py /path/to/input.pptx /tmp/anything2slides_extracted
python3 anything2slides-skill/scripts/bootstrap_reveal_from_bundle.py /tmp/anything2slides_extracted /tmp/anything2slides_show_ready
```

## Current Limitations

For PPT mode, the current goal is robust extraction plus editable reconstruction, not pixel-perfect PowerPoint emulation. These areas may still need manual review:

- SmartArt semantics
- Chart data reconstruction
- Animation and transition effects
- Complex grouped objects
- Theme font inheritance
- Video playback metadata

If the original PPT depends heavily on those features, treat the generated HTML as a strong draft and refine it manually.

## Recommended GitHub Layout

If you want to publish this project in your own GitHub repository, keep the repo root minimal:

- `README.md`
- `README.zh-CN.md`
- `README.en.md`
- `anything2slides-skill/`

Then run:

```bash
git init
git add .
git commit -m "Initial commit: add anything2slides-skill"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```
