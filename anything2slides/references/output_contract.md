# PPTX Bundle Output Contract

This file explains the outputs produced by `scripts/extract_pptx_bundle.py` and how `scripts/bootstrap_reveal_from_bundle.py` uses them.

## Output Directory Layout

After extraction, the directory looks like:

```text
extracted/
├── manifest.json
├── slides_outline.md
└── media/
    ├── image1.png
    ├── image2.jpeg
    └── ...
```

## `manifest.json`

Top-level fields:

- `source_file`: original `.pptx` path string
- `presentation_size`: slide canvas size in EMUs when present
- `slide_count`: number of ordered slides
- `slides`: ordered array of slide objects

Each slide object includes:

- `number`: 1-based slide index
- `path`: package path such as `ppt/slides/slide3.xml`
- `title`: best-effort title chosen from title placeholders or first text block
- `notes`: extracted speaker notes as plain text
- `text_blocks`: text-bearing shapes in reading order
- `media`: embedded images referenced by that slide

## `text_blocks`

Each text block includes:

- `shape_id`: PowerPoint shape id when available
- `name`: shape name from `cNvPr`
- `placeholder`: placeholder type such as `title`, `ctrTitle`, `subTitle`, `body`
- `text`: normalized plain text
- `paragraphs`: paragraph array with line breaks preserved
- `geometry`: optional `x`, `y`, `cx`, `cy` numbers in EMUs

Recommended mapping:

- `title` or `ctrTitle`: prefer as HTML slide title
- `subTitle`: use as subtitle, deck meta, or supporting sentence
- `body`: convert into bullets or short paragraphs
- large freeform text without a placeholder: inspect manually before trusting it

## `media`

Each media item includes:

- `shape_id`
- `name`
- `source`: package-relative source path
- `output_rel`: relative path inside the extracted bundle, usually `media/<filename>`
- `geometry`: optional placement hints

Recommended mapping:

- one image plus several bullets: use a two-column layout
- two images: use a comparison or gallery layout
- three or more images: use a `media-grid`
- decorative logos/backgrounds: remove unless they are content-bearing

## `slides_outline.md`

This is a lightweight summary meant for fast reading before editing the HTML deck. Use it to understand the narrative without parsing raw JSON.

## Known Limitations

The extraction script intentionally favors robust metadata over full PowerPoint fidelity. Expect gaps for:

- SmartArt semantics
- chart data reconstruction
- animations and transitions
- grouped object semantics
- theme/font inheritance
- embedded video playback metadata

When these matter, inspect the original PPT manually and rebuild the slide in HTML rather than copying the PPT structure literally.
