#!/usr/bin/env python3
"""Bootstrap a faithful Reveal.js deck from an extracted PPTX bundle."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from pathlib import Path
from typing import Dict, List, Tuple


DEFAULT_SOURCE_WIDTH = 12192000
DEFAULT_SOURCE_HEIGHT = 6858000
DEFAULT_REVEAL_WIDTH = 1280


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a layout-faithful Reveal.js deck from an extracted PPTX bundle.",
    )
    parser.add_argument("bundle_dir", help="Directory created by extract_pptx_bundle.py")
    parser.add_argument("output_dir", help="Directory where the HTML deck should be created")
    parser.add_argument(
        "--skill-dir",
        default=str(Path(__file__).resolve().parent.parent),
        help="Skill root containing assets/",
    )
    return parser.parse_args()


def read_manifest(bundle_dir: Path) -> Dict[str, object]:
    manifest_path = bundle_dir / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"manifest.json not found in {bundle_dir}")
    return json.loads(manifest_path.read_text())


def html_text(value: str) -> str:
    return html.escape(value, quote=True)


def slide_sizes(manifest: Dict[str, object]) -> Tuple[int, int, int, int]:
    source_size = manifest.get("presentation_size") or {}
    source_width = int(source_size.get("cx") or DEFAULT_SOURCE_WIDTH)
    source_height = int(source_size.get("cy") or DEFAULT_SOURCE_HEIGHT)
    reveal_width = DEFAULT_REVEAL_WIDTH
    reveal_height = max(360, round(reveal_width * source_height / source_width))
    return source_width, source_height, reveal_width, reveal_height


def percent(value: int, total: int) -> str:
    if total <= 0:
        return "0%"
    return f"{(value / total) * 100:.4f}%"


def normalized_px(value: int, source_total: int, reveal_total: int) -> float:
    if source_total <= 0:
        return 0.0
    return reveal_total * value / source_total


def guess_font_size_px(
    block: Dict[str, object],
    source_width: int,
    source_height: int,
    reveal_width: int,
    reveal_height: int,
) -> float:
    geometry = block.get("geometry") or {}
    placeholder = str(block.get("placeholder") or "")
    paragraphs = block.get("paragraphs") or []
    line_count = max(1, len(paragraphs))
    box_height = normalized_px(int(geometry.get("cy", 0) or 0), source_height, reveal_height)
    box_width = normalized_px(int(geometry.get("cx", 0) or 0), source_width, reveal_width)
    text_length = max(1, len(str(block.get("text") or "").replace("\n", "")))

    if placeholder in {"title", "ctrTitle"}:
        return max(24, min(40, box_height / 2.4))
    if placeholder == "subTitle":
        return max(16, min(26, box_height / 2.8))

    if box_height > 0:
        size = box_height / max(1.6, line_count * 1.45)
    else:
        size = 20

    if text_length > 120:
        size *= 0.9
    if box_width < 240:
        size *= 0.92
    return max(12, min(28, size))


def line_height(placeholder: str) -> float:
    if placeholder in {"title", "ctrTitle"}:
        return 1.08
    if placeholder == "subTitle":
        return 1.15
    return 1.22


def sanitize_placeholder(value: str) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def sorted_text_blocks(slide: Dict[str, object]) -> List[Dict[str, object]]:
    blocks = slide.get("text_blocks", [])
    return sorted(
        blocks,
        key=lambda block: (
            int((block.get("geometry") or {}).get("y", 0) or 0),
            int((block.get("geometry") or {}).get("x", 0) or 0),
            int(block.get("shape_id") or 0),
        ),
    )


def sorted_media_items(slide: Dict[str, object]) -> List[Dict[str, object]]:
    media = slide.get("media", [])
    return sorted(
        media,
        key=lambda item: (
            int((item.get("geometry") or {}).get("y", 0) or 0),
            int((item.get("geometry") or {}).get("x", 0) or 0),
            int(item.get("shape_id") or 0),
        ),
    )


def render_textbox(
    block: Dict[str, object],
    source_width: int,
    source_height: int,
    reveal_width: int,
    reveal_height: int,
) -> str:
    geometry = block.get("geometry") or {}
    left = int(geometry.get("x", 0) or 0)
    top = int(geometry.get("y", 0) or 0)
    width = int(geometry.get("cx", source_width) or source_width)
    height = int(geometry.get("cy", 0) or 0)
    placeholder = str(block.get("placeholder") or "")
    font_size = guess_font_size_px(block, source_width, source_height, reveal_width, reveal_height)
    paragraphs = block.get("paragraphs") or [str(block.get("text") or "")]
    rendered_paragraphs = "\n".join(
        f"          <p>{html_text(str(paragraph))}</p>" for paragraph in paragraphs if str(paragraph).strip()
    )
    if not rendered_paragraphs:
        rendered_paragraphs = "          <p></p>"

    class_suffix = sanitize_placeholder(placeholder)
    class_attr = "ppt-textbox"
    if class_suffix:
        class_attr += f" ppt-placeholder-{class_suffix}"

    style = (
        f"left:{percent(left, source_width)};"
        f"top:{percent(top, source_height)};"
        f"width:{percent(width, source_width)};"
        f"height:{percent(height, source_height)};"
        f"font-size:calc({font_size:.2f}px * var(--font-scale));"
        f"line-height:{line_height(placeholder)};"
    )
    return "\n".join(
        [
            f"      <div class=\"{class_attr}\" data-placeholder=\"{html_text(placeholder)}\" style=\"{style}\">",
            rendered_paragraphs,
            "      </div>",
        ]
    )


def render_media(
    item: Dict[str, object],
    slide_number: int,
    media_index: int,
    source_width: int,
    source_height: int,
) -> str:
    geometry = item.get("geometry") or {}
    left = int(geometry.get("x", 0) or 0)
    top = int(geometry.get("y", 0) or 0)
    width = int(geometry.get("cx", 0) or 0)
    height = int(geometry.get("cy", 0) or 0)
    src = html_text(f"assets/{item['output_rel']}")
    alt = html_text(str(item.get("name") or f"Slide {slide_number} image {media_index}"))
    fig_id = html_text(f"s{slide_number}-m{media_index}")
    style = (
        f"left:{percent(left, source_width)};"
        f"top:{percent(top, source_height)};"
        f"width:{percent(width, source_width)};"
        f"height:{percent(height, source_height)};"
    )
    return "\n".join(
        [
            f"      <div class=\"ppt-media figure-frame\" data-fig=\"{fig_id}\" style=\"{style}\">",
            f"        <img src=\"{src}\" alt=\"{alt}\">",
            "      </div>",
        ]
    )


def render_notes(notes: str, slide_title: str, slide_number: int) -> str:
    if not notes.strip():
        return html_text(f"Slide {slide_number}: {slide_title}")
    trimmed = " ".join(notes.split())
    return html_text(trimmed[:1000])


def render_slide(
    slide: Dict[str, object],
    source_width: int,
    source_height: int,
    reveal_width: int,
    reveal_height: int,
) -> str:
    parts = []
    for block in sorted_text_blocks(slide):
        parts.append(render_textbox(block, source_width, source_height, reveal_width, reveal_height))
    for media_index, item in enumerate(sorted_media_items(slide), start=1):
        parts.append(render_media(item, int(slide["number"]), media_index, source_width, source_height))

    canvas_style = f"--slide-width:{reveal_width}px;--slide-height:{reveal_height}px;"
    title = str(slide.get("title") or f"Slide {slide['number']}")
    notes = render_notes(str(slide.get("notes") or ""), title, int(slide["number"]))

    return "\n".join(
        [
            f"      <section class=\"ppt-slide\" data-title=\"{html_text(title)}\">",
            f"        <div class=\"ppt-slide-canvas\" style=\"{canvas_style}\">",
            "\n".join(parts) if parts else "",
            "        </div>",
            f"        <aside class=\"notes\">{notes}</aside>",
            "      </section>",
        ]
    )


def build_html(manifest: Dict[str, object], template_path: Path) -> str:
    source_width, source_height, reveal_width, reveal_height = slide_sizes(manifest)
    slides = manifest.get("slides", [])
    rendered_slides = [
        render_slide(slide, source_width, source_height, reveal_width, reveal_height)
        for slide in slides
    ]

    template = template_path.read_text()
    title = Path(str(manifest["source_file"])).stem or "HTML Presentation"
    if slides and slides[0].get("title"):
        title = str(slides[0]["title"])
    return (
        template.replace("{{TITLE}}", html_text(title))
        .replace("{{SOURCE_FILE}}", html_text(Path(str(manifest["source_file"])).name))
        .replace("{{REVEAL_WIDTH}}", str(reveal_width))
        .replace("{{REVEAL_HEIGHT}}", str(reveal_height))
        .replace("{{SLIDES}}", "\n".join(rendered_slides))
    )


def build_notes(manifest: Dict[str, object], template_path: Path) -> str:
    chunks = []
    for slide in manifest.get("slides", []):
        note_text = str(slide.get("notes", "")).strip() or "No source notes were embedded in the PPT."
        chunks.append(
            "\n".join(
                [
                    f"## Slide {slide['number']} — {slide['title']}",
                    "",
                    "**Source notes:**",
                    note_text,
                    "",
                ]
            )
        )

    title = Path(str(manifest["source_file"])).stem or "HTML Presentation"
    if manifest.get("slides") and manifest["slides"][0].get("title"):
        title = str(manifest["slides"][0]["title"])
    return (
        template_path.read_text()
        .replace("{{TITLE}}", title)
        .replace("{{SLIDE_NOTES}}", "\n".join(chunks).rstrip())
    )


def copy_media(bundle_dir: Path, output_dir: Path) -> None:
    src = bundle_dir / "media"
    dst = output_dir / "assets" / "media"
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.is_file():
            shutil.copy2(item, dst / item.name)


def main() -> None:
    args = parse_args()
    bundle_dir = Path(args.bundle_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    skill_dir = Path(args.skill_dir).expanduser().resolve()
    manifest = read_manifest(bundle_dir)

    (output_dir / "assets" / "css").mkdir(parents=True, exist_ok=True)
    copy_media(bundle_dir, output_dir)
    shutil.copy2(skill_dir / "assets" / "slides.css", output_dir / "assets" / "css" / "style.css")

    html_output = build_html(manifest, skill_dir / "assets" / "template_shell.html")
    notes_output = build_notes(manifest, skill_dir / "assets" / "speaker_notes_template.md")

    (output_dir / "index.html").write_text(html_output)
    (output_dir / "speaker_notes.md").write_text(notes_output)

    print(f"Wrote {output_dir / 'index.html'}")
    print(f"Wrote {output_dir / 'speaker_notes.md'}")


if __name__ == "__main__":
    main()
