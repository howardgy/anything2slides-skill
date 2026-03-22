---
name: anything2slides-skill
description: "Turn source materials into a polished HTML presentation. For `.ppt` or `.pptx`, preserve the original slide count and layout as closely as possible. For `.pdf`, `.txt`, `.text`, `.html`, `.md`, or `.docx`, extract text and visuals into a structured bundle, then follow a paper2slides-style workflow to design and generate a show-ready HTML deck."
---

# anything2slides-skill

## Overview

This skill turns source materials into a polished HTML slide deck, but it deliberately uses **two different modes** depending on the input type.

For PowerPoint, the goal is faithful reconstruction.

For PDF, text, HTML, Markdown, and Word documents, the goal is presentation design with an automated extraction layer plus agent-style narrative curation: understand the content first, decide what kind of talk the material should become, and then build a coherent HTML deck.

## When To Use It

Use this skill when the user asks to:

- Convert `.ppt` or `.pptx` into HTML slides while preserving the original deck
- Turn a PowerPoint deck into a Reveal.js presentation
- Build a web presentation from a `.pdf`, `.md`, `.html`, `.txt`, `.docx`, or similar source
- Create a show-ready HTML talk from source documents rather than from an existing slide deck
- Produce an editable web slideshow from either presentation files or document-style source materials

Do not use it when the user only wants:

- A PDF export of the deck
- A static screenshot/video of slides
- Minor text edits inside the original PowerPoint file

## Routing Rule

Choose the workflow strictly by source type:

- **If the source is `.ppt` or `.pptx`**:
  Use the **faithful PPT workflow**.
  Preserve the original slide count.
  Preserve each slide's rough geometry, page order, and visual grouping.
  Do not silently reorganize the narrative unless the user explicitly asks for redesign.

- **If the source is `.pdf`, `.txt`, `.text`, `.html`, `.md`, or `.docx`**:
  Use the **paper2slides-style workflow**.
  First read and understand the source.
  Then decide what the presentation should look like.
  Then write a curated HTML deck with notes.
  In this mode, narrative design is expected.

When in doubt, prefer:

- **layout fidelity** for PPT
- **content curation** for non-PPT sources

## Workflow A: PPT / PPTX

### Goal

Rebuild the original presentation as HTML with minimal semantic drift.

### Prerequisites

- `python3`
- A `.pptx` file as input
- If the source is `.ppt`, convert it first, for example with LibreOffice:

```bash
libreoffice --headless --convert-to pptx --outdir "<converted_dir>" "<path/to/input.ppt>"
```

If LibreOffice is unavailable, ask the user whether they want a `.pptx` export from PowerPoint/Keynote first. The extraction scripts in this skill are `.pptx`-only.

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

### Phase 2: Inspect The Source Deck

Read:

- `slides_outline.md` for slide-by-slide intent
- `manifest.json` for structured details
- original speaker notes from the `notes` field

Preserve:

- original slide order
- original slide count
- major text/image geometry
- original media grouping

Only simplify when PowerPoint-specific effects cannot be carried over directly.

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

The generated deck keeps the original slide count and uses PPT geometry to position text and images. It also includes:

- left-bottom settings panel
- per-image click-to-enlarge preview
- top-layer lightbox with zoom/drag controls

### Phase 4: Conservative Cleanup

Use the generated deck as scaffolding and improve it conservatively:

- fix missing titles caused by extraction limits
- adjust text sizes when a source text box overflows in HTML
- remove clearly decorative assets only if they hurt readability
- preserve source notes where useful

Prefer fidelity first, redesign second.

### Phase 5: PPT QA

Check:

- images load correctly from `assets/media/`
- slide count matches the source PPT
- major text/image positions still resemble the source PPT
- final deck opens as a standalone local HTML file

If the user asked for a "faithful" conversion, explicitly mention any PowerPoint-only effects that were simplified.

## Workflow B: PDF / Text / HTML / Markdown / Word

### Goal

Read the material, understand it, and design the right presentation for it.

This branch follows the spirit of `paper2slides`:

1. **Mechanical reading layer**: inspect the source material and gather structured content
2. **Intelligence layer**: decide the talk structure, slide count, emphasis, pacing, and visual organization

### Supported Source Types

- `.pdf`
- `.txt`
- `.text`
- `.md`
- `.html`
- `.docx`

Use `.docx` instead of legacy `.doc`.

### Phase 0: Unified Entrypoint

The fastest path is the unified router:

```bash
python3 "<skill_dir>/scripts/anything2slides.py" \
  "<path/to/source>" \
  "<work_dir>/show_ready"
```

Routing behavior:

- `.ppt` / `.pptx` -> faithful PPT pipeline
- `.pdf` / `.txt` / `.text` / `.md` / `.html` / `.docx` -> document pipeline

### Phase 1: Read The Source

Run the document extractor:

```bash
python3 "<skill_dir>/scripts/extract_document_bundle.py" \
  "<path/to/source>" \
  "<work_dir>/document_bundle"
```

This creates:

- `manifest.json` — source metadata, extracted sections, and image inventory
- `source_outline.md` — a readable summary of the recovered structure
- `media/` — copied or extracted local visuals when available

Then inspect the bundle and, if needed, read the original source directly using the host environment's file-reading abilities.

Extract:

- title or topic
- major sections
- key claims, data points, and examples
- supporting visuals if present
- likely audience and talk purpose

### Phase 2: Decide What Kind Of Deck It Should Become

Before writing slides, decide:

- Is this an explainer, report-out, proposal, journal club, tutorial, or status update?
- Should the deck be brief and executive, or detailed and technical?
- Which sections deserve full slides, and which should be compressed?
- Which ideas need visuals, comparisons, timelines, or diagrams?

This step is mandatory. Do not dump source paragraphs into slides without first designing the narrative.

### Phase 3: Build A Curated HTML Deck

Run the document bootstrapper:

```bash
python3 "<skill_dir>/scripts/bootstrap_reveal_from_document_bundle.py" \
  "<work_dir>/document_bundle" \
  "<work_dir>/show_ready"
```

This creates:

- `show_ready/index.html`
- `show_ready/speaker_notes.md`
- `show_ready/assets/css/style.css`
- `show_ready/assets/media/`

Create a show-ready Reveal.js deck that is:

- coherent
- audience-aware
- concise on each slide
- stronger than the raw source document

The bootstrapper already generates:

- title / opening framing
- document-at-a-glance slide
- agenda when the source has enough sections
- section slides that switch between text, two-column, and gallery layouts
- takeaways and closing slides

In this mode you are still allowed, and expected, to:

- rewrite headings
- combine or split sections
- compress verbose prose
- convert prose into bullets, comparisons, timelines, or structured layouts
- introduce section dividers and stronger transitions

### Phase 4: Write Speaker Notes

Write notes like `paper2slides` does:

- what the slide is showing
- what the speaker should emphasize
- any exact terminology, numbers, or caveats
- a transition to the next idea when useful

### Phase 5: Non-PPT QA

Check:

- narrative flow makes sense without the source document open
- no slide is a raw paragraph dump
- titles communicate takeaways, not just section labels
- the final deck feels intentionally designed for presentation

## Design Principle

- **PPT / PPTX**: reconstruct
- **PDF / text / html / md / word**: interpret and redesign

## Layout Patterns

Use these patterns repeatedly inside `index.html` when you need to hand-edit or curate slides:

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

For PPT mode, preserve source notes when they are useful.

For non-PPT mode, write notes from scratch as presenter guidance.

Good notes should include:

1. what is on the screen
2. the main message
3. any number, name, or caveat worth emphasizing
4. a transition to the next slide when helpful

Do not paste long raw note blocks into the final deck unchanged if they read like an internal memo.

## Files In This Skill

- `scripts/anything2slides.py`: unified router for PPT and document-style sources
- `scripts/extract_pptx_bundle.py`: unzips and parses the `.pptx` into a reusable bundle
- `scripts/bootstrap_reveal_from_bundle.py`: turns a PPT extraction bundle into a Reveal.js deck
- `scripts/extract_document_bundle.py`: extracts sections, text, and visuals from PDF / DOCX / Markdown / HTML / TXT
- `scripts/bootstrap_reveal_from_document_bundle.py`: turns a document bundle into a curated Reveal.js deck
- `references/output_contract.md`: explains the manifest schema and recommended mapping
- `assets/template_shell.html`: HTML shell used by the bootstrap script
- `assets/slides.css`: default presentation theme
- `assets/speaker_notes_template.md`: note scaffold used by the bootstrap script

## Quality Checklist

- [ ] Source type was routed to the correct workflow
- [ ] PPT mode preserves page count and main layout
- [ ] Non-PPT mode reflects deliberate narrative design
- [ ] Media assets are linked with relative paths and load locally
- [ ] Image preview/lightbox controls work
- [ ] Left-bottom settings panel works
- [ ] Speaker notes are useful for presentation, not raw dump text
- [ ] The final HTML deck is editable without re-running the whole pipeline
