---
name: ppt2slides-skill
description: Convert a PowerPoint `.ppt` or `.pptx` into a polished HTML presentation by extracting slide text, speaker notes, layout cues, and embedded media, then rebuilding the deck as a show-ready Reveal.js site. Use when the user asks to turn an existing PPT into browser-based slides, a web demo, or an editable HTML deck.
---

# ppt2slides-skill

## Overview

This skill mirrors the spirit of `paper2slides`: a deterministic extraction layer prepares structure and assets, then the agent turns that raw material into a coherent HTML deck with speaker notes.

The default goal is a faithful PowerPoint-to-web rebuild: preserve the original slide count, preserve each slide's overall layout, and keep media near their original positions. The HTML result should still be editable and web-friendly, but it should not silently reorganize the deck unless the user explicitly asks for redesign.

## When To Use It

Use this skill when the user asks to:

- Convert `.ppt` or `.pptx` into HTML slides
- Turn a PowerPoint deck into a Reveal.js presentation
- Rebuild an internal PPT as a browser-based demo
- Produce an editable web slideshow from an existing slide deck

Do not use it when the user only wants:

- A PDF export of the deck
- A static screenshot/video of slides
- Minor text edits inside the original PowerPoint file

## Mental Model

This skill has two layers:

1. **Mechanical layer**: bundled scripts extract slide order, text, speaker notes, media references, and geometry hints from a `.pptx`.
2. **Intelligence layer**: the agent reviews the extracted bundle, preserves the original slide-by-slide structure, and only makes minimal adjustments needed for a robust HTML presentation.

The scripts should do the repetitive parsing. The agent should do the narrative and design decisions.

## Prerequisites

- `python3`
- A `.pptx` file as input
- If the source is `.ppt`, convert it first, for example with LibreOffice:

```bash
libreoffice --headless --convert-to pptx --outdir "<converted_dir>" "<path/to/input.ppt>"
```

If LibreOffice is unavailable, ask the user whether they want a `.pptx` export from PowerPoint/Keynote first. The extraction scripts in this skill are `.pptx`-only.

## Workflow

### Phase 1: Extract The PPTX Bundle

Run the extraction script:

```bash
python3 "<skill_dir>/scripts/extract_pptx_bundle.py" \
  "<path/to/input.pptx>" \
  "<work_dir>/extracted"
```

This creates:

- `manifest.json` — ordered slide manifest with titles, text blocks, notes, media, and geometry
- `slides_outline.md` — quick human-readable summary of the deck
- `media/` — copied embedded assets from the PPTX package

If you need the manifest field meanings, read `references/output_contract.md`.

### Phase 2: Inspect The Source Story

Read:

- `slides_outline.md` for slide-by-slide intent
- `manifest.json` for structured details
- original speaker notes from the `notes` field

Decide whether the HTML output should:

- closely mirror the original slide sequence
- compress redundant slides into a shorter web talk
- split dense PPT slides into multiple cleaner HTML slides

Preserve the original hierarchy, page count, and major layout blocks. Only simplify when PowerPoint-specific effects cannot be carried over directly.

### Phase 3: Bootstrap A Reveal.js Deck

Run the bootstrap script:

```bash
python3 "<skill_dir>/scripts/bootstrap_reveal_from_bundle.py" \
  "<work_dir>/extracted" \
  "<work_dir>/show_ready"
```

This creates:

- `show_ready/index.html` — a layout-faithful Reveal.js deck
- `show_ready/assets/css/style.css` — theme CSS copied from this skill
- `show_ready/assets/media/` — media assets for the HTML deck
- `show_ready/speaker_notes.md` — presentation notes scaffold

The generated deck now keeps the original slide count and uses PPT geometry to position text and images. It also includes:

- left-bottom settings panel
- per-image zoom in / zoom out / reset / lightbox controls

Expect to edit `index.html` and `speaker_notes.md` only when you want refinements beyond the source deck.

### Phase 4: Curate The HTML Presentation

Use the generated deck as scaffolding and improve it conservatively:

- fix any missing titles caused by PPT extraction limits
- adjust text sizes when a source text box overflows in HTML
- remove clearly decorative assets only if they hurt readability
- surface speaker notes where they meaningfully help the presenter

Prefer fidelity first, redesign second.

### Phase 5: QA Before Delivery

Check:

- images load correctly from `assets/media/`
- slide titles and bullets fit without overflow
- speaker notes exist for every important slide
- source deck order still makes sense after curation
- final deck opens as a standalone local HTML file

If the user asked for a "faithful" conversion, call out places where PowerPoint-only effects were simplified.

## Layout Patterns

Use these patterns repeatedly inside `index.html`:

### Text slide

```html
<section>
  <h2>Slide Title</h2>
  <ul>
    <li>Point one</li>
    <li>Point two</li>
    <li>Point three</li>
  </ul>
  <aside class="notes">Presenter notes.</aside>
</section>
```

### Two-column text + media

```html
<section>
  <h2>Slide Title</h2>
  <div class="two-col-layout">
    <div class="col-text">
      <ul>
        <li>Key point</li>
        <li>Supporting point</li>
      </ul>
    </div>
    <div class="col-media">
      <div class="media-frame">
        <img src="assets/media/image1.png" alt="Description">
      </div>
    </div>
  </div>
  <aside class="notes">Talk track.</aside>
</section>
```

### Media comparison

```html
<section>
  <h2>Before / After</h2>
  <div class="media-grid media-grid-2">
    <figure class="media-card">
      <div class="media-frame"><img src="assets/media/image1.png" alt="Before"></div>
      <figcaption>Before</figcaption>
    </figure>
    <figure class="media-card">
      <div class="media-frame"><img src="assets/media/image2.png" alt="After"></div>
      <figcaption>After</figcaption>
    </figure>
  </div>
  <aside class="notes">Explain the comparison.</aside>
</section>
```

### Section divider

```html
<section class="section-slide">
  <h1>Section Title</h1>
  <p>Short transition subtitle</p>
  <aside class="notes">Transition cue.</aside>
</section>
```

### Hidden backup slide

```html
<section data-visibility="hidden">
  <h2>Backup Detail</h2>
  <p>Useful during Q&amp;A.</p>
</section>
```

## Speaker Notes Guidance

Use the source PPT speaker notes when they are useful, but rewrite them for spoken delivery. Good notes should include:

1. what is on the screen
2. the main message
3. any number, name, or caveat worth emphasizing
4. a transition to the next slide when helpful

Do not paste long raw note blocks into the final deck unchanged if they read like an internal memo.

## Files In This Skill

- `scripts/extract_pptx_bundle.py`: unzips and parses the `.pptx` into a reusable bundle
- `scripts/bootstrap_reveal_from_bundle.py`: turns the extracted bundle into a first-pass Reveal.js deck
- `references/output_contract.md`: explains the manifest schema and recommended mapping
- `assets/template_shell.html`: HTML shell used by the bootstrap script
- `assets/slides.css`: default presentation theme
- `assets/speaker_notes_template.md`: note scaffold used by the bootstrap script

## Quality Checklist

- [ ] Original slide order is preserved
- [ ] Original slide count is preserved
- [ ] Major text/image positions still match the source PPT
- [ ] Titles are outcome-oriented, not file-name-like
- [ ] Speaker notes are preserved where useful and rewritten where needed
- [ ] Media assets are linked with relative paths and load locally
- [ ] Image zoom/lightbox controls work
- [ ] Left-bottom settings panel works
- [ ] Animations or SmartArt that could not be preserved are simplified explicitly
- [ ] The final HTML deck is editable without re-running PowerPoint
