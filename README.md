# anything2slides-skill

[中文](README.zh-CN.md) | [English](README.en.md)

`anything2slides-skill` is a standard-structured general-purpose skill for converting multiple kinds of source material into editable, locally runnable, presentation-ready Reveal.js HTML slides.

For non-PPT document-to-slides workflows, this project references and extends ideas from [inhyeoklee/paper2slides-skill](https://github.com/inhyeoklee/paper2slides-skill), especially the `paper2slides`-style flow of extract first, understand next, then organize the presentation narrative.

It has two operating modes:

- For `ppt` / `pptx`: rebuild the web version by following the original slide order and major layout of the source PPT
- For `pdf` / `text` / `html` / `md` / `docx`: follow a `paper2slides`-inspired process, extracting text and images first, then deciding the presentation structure before generating the final HTML deck

## Good Fits

- Convert an existing PPT into a browser-presentable version
- Turn PDF, Markdown, Word, or HTML content into show-ready slides
- Produce internal presentation demos that can be hosted on the web
- Convert document content into an HTML deck that AI or humans can continue editing
- Rebuild a PPT as show-ready web slides while keeping the original slide order and major layout

## Installation

### Option 1: type this command

```text
Help me install the skill https://github.com/howardgy/anything2slides-skill/
```

### Option 2: clone it as a GitHub project and install it

```bash
cd <your project folder>
git clone https://github.com/howardgy/anything2slides-skill/
cp -R anything2slides-skill/anything2slides-skill ~/<your tool path, for example ~/.codex>/skills/
```

## Usage

### Python setup

First enter the skill directory and install the runtime dependencies from `requirements.txt`:

```bash
cd anything2slides-skill
python3 -m pip install -r requirements.txt
```

Requirements:
- Python 3.9 or newer

### Call it as a skill

You can directly ask the agent to use this skill, for example:

```text
Turn this PPT file into slides.
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

That means the generated HTML will usually appear at `show_ready/index.html` inside the output directory you specified.
