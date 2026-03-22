# anything2slides-skill

[中文](README.zh-CN.md) | [English](README.en.md)

`anything2slides-skill` is a reusable skill package for turning multiple source formats into editable, locally runnable Reveal.js presentations.

This project references and extends workflow ideas from [inhyeoklee/paper2slides-skill](https://github.com/inhyeoklee/paper2slides-skill), especially for the document-to-slides branch inspired by a `paper2slides`-style extraction and curation flow.

## Quick Overview

- `ppt` / `pptx`: preserve original slide order and approximate layout
- `pdf` / `docx` / `md` / `html` / `txt`: extract text and visuals, design a narrative, then generate a curated Reveal deck
- Unified entrypoint: `anything2slides-skill/scripts/anything2slides.py`

## Repository Layout

This repository is intentionally kept minimal:

- `README.md`
- `README.zh-CN.md`
- `README.en.md`
- `anything2slides-skill/`

## Get Started

Use the skill directory in a compatible environment such as Codex Desktop, Codex CLI, Claude Code, or other local-skill-capable tooling.

Install the Python runtime dependencies first:

```bash
python3 -m pip install beautifulsoup4 pymupdf
```

This repository is published as a source-only skill package. It does not include an installed virtualenv, wheel, `egg-info`, `build/`, `dist/`, or `__pycache__` artifacts.

```bash
python3 anything2slides-skill/scripts/anything2slides.py \
  /path/to/input \
  /path/to/work/show_ready
```

For full installation and usage details, open:

- [中文说明](README.zh-CN.md)
- [English Documentation](README.en.md)
