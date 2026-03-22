# anything2slides-skill

[中文](README.zh-CN.md) | [English](README.en.md)

`anything2slides-skill` is a reusable skill package for turning multiple source formats into editable, locally runnable Reveal.js HTML presentations.

This project references and extends workflow ideas from [inhyeoklee/paper2slides-skill](https://github.com/inhyeoklee/paper2slides-skill), especially for the `paper2slides`-style document workflow: extract first, understand second, then organize the final talk structure.

It has two operating modes:

- For `ppt` / `pptx`: rebuild the original deck as HTML while preserving slide order and the main layout
- For `pdf` / `text` / `html` / `md` / `docx`: extract text and visuals first, then design the presentation structure and generate the final HTML deck

## Good Fits

- Convert an existing PPT into a browser-presentable version
- Turn PDF, Markdown, Word, or HTML content into show-ready slides
- Produce an internal presentation demo for web hosting
- Convert document content into an HTML deck that AI or humans can keep editing
- Rebuild a PPT as web slides while keeping the original order and major layout

## Installation

### Option 1: ask your coding tool to install the skill

```text
Help me install the skill <your-github-repo-url>
```

### Option 2: clone from GitHub and install manually

```bash
git clone <your-github-repo-url>
mkdir -p ~/.codex/skills
cp -R anything2slides-skill/anything2slides-skill ~/.codex/skills/
```

## Usage

### Python setup

Change into the skill directory and install the runtime dependencies from `requirements.txt`:

```bash
cd anything2slides-skill
python3 -m pip install -r requirements.txt
```

Requirement:

- Python 3.9 or newer

### Ask the skill to run

You can call the skill with natural language, for example:

```text
Turn this source material into a slide deck.
```

### Example prompts for coding tools

- Codex Desktop / Codex CLI: `Please use the local skill at ./anything2slides-skill for file-to-Reveal conversion.`
- Claude Code: `Use the local skill in ./anything2slides-skill to turn source files into Reveal.js slides.`
- OpenClaw or similar tools: `Install the skill from ./anything2slides-skill and use it for document and PPT to Reveal.js conversion.`

### Example natural-language requests

- `Use $anything2slides-skill to convert ./examples/review.pdf into a Reveal.js deck in ./out/review-html`
- `Use $anything2slides-skill to turn ./notes/status.md into slides in ./out/status-slides`
- `Use $anything2slides-skill to convert ./deck/source.pptx into HTML slides in ./out/source-html`

### Run the script directly

From the repository root:

```bash
python3 anything2slides-skill/scripts/anything2slides.py \
  ./path/to/input \
  ./out/show_ready
```

## Output Layout

### Extraction stage

```text
extracted/
├── manifest.json
├── slides_outline.md
└── media/
```

For document-style sources:

```text
document_bundle/
├── manifest.json
├── source_outline.md
└── media/
```

### Generated output

```text
show_ready/
├── index.html
├── speaker_notes.md
└── assets/
    ├── css/
    └── media/
```

In practice, the generated HTML will usually appear at `show_ready/index.html` inside the output folder you provided.
