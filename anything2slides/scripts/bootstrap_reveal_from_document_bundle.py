#!/usr/bin/env python3
"""Bootstrap a curated Reveal.js deck from a document extraction bundle."""

from __future__ import annotations

import argparse
import html
import json
import math
import re
import shutil
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


DEFAULT_REVEAL_WIDTH = 1280
DEFAULT_REVEAL_HEIGHT = 720
MAX_BULLETS_PER_SLIDE = 4
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
    "we",
    "our",
    "their",
    "these",
    "those",
}
SKIP_SECTION_PATTERNS = (
    re.compile(r"^\s*references?\s*$", re.IGNORECASE),
    re.compile(r"^\s*bibliography\s*$", re.IGNORECASE),
    re.compile(r"^\s*appendix\s*$", re.IGNORECASE),
    re.compile(r"^\s*acknowledg(e)?ments?\s*$", re.IGNORECASE),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a curated Reveal.js deck from a document bundle.",
    )
    parser.add_argument("bundle_dir", help="Directory created by extract_document_bundle.py")
    parser.add_argument("output_dir", help="Directory where the HTML deck should be created")
    parser.add_argument(
        "--skill-dir",
        default=str(Path(__file__).resolve().parent.parent),
        help="Skill root containing assets/",
    )
    parser.add_argument(
        "--max-slides",
        type=int,
        default=14,
        help="Upper bound for visible slides in the generated deck",
    )
    return parser.parse_args()


def html_text(value: str) -> str:
    return html.escape(value, quote=True)


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def short_text(text: str, limit: int = 180) -> str:
    value = normalize_whitespace(text)
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def count_tokens(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]", text))


def split_sentences(text: str) -> List[str]:
    normalized = normalize_whitespace(text)
    if not normalized:
        return []
    sentences = re.split(r"(?<=[。！？!?;；.])\s+", normalized)
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def read_manifest(bundle_dir: Path) -> Dict[str, object]:
    manifest_path = bundle_dir / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"manifest.json not found in {bundle_dir}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def section_is_visible(section: Dict[str, object]) -> bool:
    title = str(section.get("title") or "")
    return not any(pattern.match(title) for pattern in SKIP_SECTION_PATTERNS)


def keyword_pool(text: str) -> List[str]:
    lowered = re.findall(r"[A-Za-z]{4,}", text.lower())
    scores: Dict[str, int] = {}
    for token in lowered:
        if token in STOPWORDS:
            continue
        scores[token] = scores.get(token, 0) + 1
    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return [token for token, _count in ordered[:10]]


def sentence_score(sentence: str, keywords: Sequence[str]) -> float:
    score = 0.0
    lowered = sentence.lower()
    for keyword in keywords:
        score += lowered.count(keyword) * 1.3
    score += min(len(sentence), 180) / 180
    if re.search(r"\d", sentence):
        score += 0.3
    return score


def summarize_section(section: Dict[str, object], max_sentences: int = 2) -> str:
    candidates: List[str] = []
    for bullet in section.get("bullets", []):
        if bullet:
            candidates.append(normalize_whitespace(str(bullet)))
    for paragraph in section.get("paragraphs", []):
        candidates.extend(split_sentences(str(paragraph))[:3])
    if not candidates:
        return ""
    keywords = keyword_pool(" ".join(candidates))
    ranked = sorted(
        dedupe_keep_order(candidates),
        key=lambda sentence: (-sentence_score(sentence, keywords), len(sentence)),
    )
    return " ".join(ranked[:max_sentences]).strip()


def clauseify(text: str) -> List[str]:
    parts = re.split(r"[;；:：,，]\s*|\s+\-\s+", normalize_whitespace(text))
    cleaned = [part.strip() for part in parts if part.strip()]
    return cleaned if cleaned else [normalize_whitespace(text)]


def bulletize(text: str, limit: int = 110) -> str:
    cleaned = normalize_whitespace(text)
    if len(cleaned) <= limit:
        return cleaned
    for chunk in clauseify(cleaned):
        if 18 <= len(chunk) <= limit:
            return chunk
    return short_text(cleaned, limit)


def dedupe_keep_order(values: Iterable[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for value in values:
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(value)
    return ordered


def section_bullets(section: Dict[str, object], limit: int = MAX_BULLETS_PER_SLIDE) -> List[str]:
    candidates: List[str] = []
    explicit = [bulletize(str(item)) for item in section.get("bullets", []) if str(item).strip()]
    candidates.extend(explicit)
    if len(candidates) < limit:
        for paragraph in section.get("paragraphs", []):
            sentences = split_sentences(str(paragraph))
            if contains_cjk(str(paragraph)):
                candidates.extend(bulletize(sentence, 44) for sentence in sentences[:2])
            else:
                candidates.extend(bulletize(sentence, 120) for sentence in sentences[:2])
            if len(candidates) >= limit * 2:
                break
    cleaned = [candidate for candidate in dedupe_keep_order(candidates) if candidate]
    return cleaned[:limit]


def section_weight(section: Dict[str, object]) -> int:
    content = " ".join(section.get("paragraphs", [])) + " " + " ".join(section.get("bullets", []))
    return count_tokens(content) + len(section.get("bullets", [])) * 12 + len(section.get("paragraphs", [])) * 8


def choose_major_sections(sections: Sequence[Dict[str, object]], max_sections: int) -> List[Dict[str, object]]:
    visible = [section for section in sections if section_is_visible(section)]
    if not visible:
        return list(sections[:max_sections])
    scored = [(index, section_weight(section), section) for index, section in enumerate(visible)]
    keep = sorted(scored, key=lambda item: (-item[1], item[0]))[:max_sections]
    keep_indices = {visible.index(item[2]) for item in keep}
    chosen = [section for index, section in enumerate(visible) if index in keep_indices]
    return chosen


def assign_images_to_sections(sections: Sequence[Dict[str, object]], images: Sequence[Dict[str, object]]) -> Dict[str, List[Dict[str, object]]]:
    mapping: Dict[str, List[Dict[str, object]]] = {str(section.get("id")): [] for section in sections}
    title_lookup = {str(section.get("title")): str(section.get("id")) for section in sections}
    visible_ids = [str(section.get("id")) for section in sections]
    if not visible_ids:
        return mapping

    next_index = 0
    for image in images:
        hint = str(image.get("section_hint") or "")
        assigned_id = ""
        if hint in title_lookup:
            assigned_id = title_lookup[hint]
        elif hint:
            for title, section_id in title_lookup.items():
                if hint.casefold() in title.casefold() or title.casefold() in hint.casefold():
                    assigned_id = section_id
                    break
        if not assigned_id:
            assigned_id = visible_ids[min(next_index, len(visible_ids) - 1)]
            next_index += 1
        mapping.setdefault(assigned_id, []).append(image)
    return mapping


def source_ref(section: Dict[str, object]) -> str:
    refs = section.get("source_refs", [])
    if not refs:
        return ""
    return ", ".join(str(ref) for ref in refs[:2])


def build_slide_notes(slide: Dict[str, object]) -> str:
    notes: List[str] = []
    if slide["kind"] == "hero":
        notes.append("Open by setting audience expectations and the promise of the deck.")
        notes.append(f"Frame the source as a {slide['doc_shape']} for a {slide['audience']}.")
    elif slide["kind"] == "overview":
        notes.append("Use this slide to explain how the source was translated into a presentation narrative.")
        notes.append("Call out the talk shape, audience fit, and the strongest extracted themes.")
    elif slide["kind"] == "agenda":
        notes.append("Preview the sequence so the audience knows how the material will unfold.")
    elif slide["kind"] in {"content", "gallery"}:
        summary = slide.get("summary", "")
        if summary:
            notes.append(f"Lead with the headline: {summary}")
        bullets = slide.get("bullets", [])
        if bullets:
            notes.append("Emphasize: " + "; ".join(bullets[:3]))
        if slide.get("source_ref"):
            notes.append(f"Source anchor: {slide['source_ref']}.")
        if slide.get("images"):
            captions = [str(image.get("caption") or "").strip() for image in slide["images"][:3]]
            captions = [caption for caption in captions if caption]
            if captions:
                notes.append("Point to the visuals as evidence: " + "; ".join(captions))
    elif slide["kind"] == "takeaways":
        notes.append("Land the three or four ideas that should stay with the audience after the talk.")
    elif slide["kind"] == "closing":
        notes.append("Close with the recommended next step and where the source can be revisited.")

    return " ".join(notes).strip()


def build_slide_plan(manifest: Dict[str, object], max_slides: int) -> List[Dict[str, object]]:
    sections = manifest.get("sections", [])
    images = manifest.get("images", [])
    overview = manifest.get("overview", {})
    title = str(manifest.get("title") or Path(str(manifest["source_file"])).stem)
    visible_sections = choose_major_sections(sections, max(3, min(6, max_slides - 5)))
    image_map = assign_images_to_sections(visible_sections, images)

    slides: List[Dict[str, object]] = []
    slides.append(
        {
            "kind": "hero",
            "title": title,
            "lede": short_text(summarize_section(visible_sections[0], 2) if visible_sections else title, 220),
            "doc_shape": str(overview.get("doc_shape") or "structured talk"),
            "audience": str(overview.get("audience") or "general audience"),
            "stats": [
                f"{manifest.get('source_type', 'document').upper()} source",
                f"{manifest.get('word_count', 0)} extracted words",
                f"{len(visible_sections)} major sections",
            ],
        }
    )
    slides.append(
        {
            "kind": "overview",
            "title": "Document At A Glance",
            "highlights": list(overview.get("highlights", []))[:4],
            "doc_shape": str(overview.get("doc_shape") or "structured talk"),
            "audience": str(overview.get("audience") or "general audience"),
            "stats": [
                f"{manifest.get('paragraph_count', 0)} paragraphs extracted",
                f"{len(images)} visuals recovered",
                f"{manifest.get('language_hint', 'en').upper()} source language",
            ],
        }
    )

    if len(visible_sections) >= 3 and len(slides) < max_slides - 2:
        slides.append(
            {
                "kind": "agenda",
                "title": "Narrative Spine",
                "items": [str(section.get("title") or "") for section in visible_sections[:6]],
            }
        )

    content_budget = max_slides - len(slides) - 2
    if content_budget < 1:
        content_budget = 1

    section_summaries = {
        str(section.get("id")): summarize_section(section, 2) for section in visible_sections
    }

    for index, section in enumerate(visible_sections):
        if len(slides) >= max_slides - 2:
            break
        section_id = str(section.get("id"))
        summary = section_summaries[section_id]
        bullets = section_bullets(section)
        assigned_images = image_map.get(section_id, [])

        if assigned_images and len(assigned_images) >= 2 and len(slides) < max_slides - 2 and index % 2 == 1:
            slides.append(
                {
                    "kind": "gallery",
                    "title": str(section.get("title") or f"Section {index + 1}"),
                    "summary": summary,
                    "bullets": bullets[:3],
                    "images": assigned_images[:3],
                    "source_ref": source_ref(section),
                }
            )
        else:
            slides.append(
                {
                    "kind": "content",
                    "title": str(section.get("title") or f"Section {index + 1}"),
                    "summary": summary,
                    "bullets": bullets,
                    "images": assigned_images[:2],
                    "source_ref": source_ref(section),
                }
            )

    takeaway_candidates: List[str] = []
    for section in visible_sections:
        takeaway_candidates.extend(section_bullets(section, 2))
    takeaways = dedupe_keep_order([candidate for candidate in takeaway_candidates if candidate])[:4]
    if not takeaways:
        takeaways = list(overview.get("highlights", []))[:4]
    slides.append(
        {
            "kind": "takeaways",
            "title": "Takeaways",
            "items": takeaways[:4],
        }
    )

    closing_items = [
        f"Revisit the original {manifest.get('source_type', 'document')} for raw detail.",
        f"Deck built from {Path(str(manifest['source_file'])).name}.",
    ]
    if visible_sections:
        closing_items.insert(0, f"Best next discussion topic: {visible_sections[-1]['title']}")
    slides.append(
        {
            "kind": "closing",
            "title": "Closing Frame",
            "items": closing_items[:3],
        }
    )

    for slide in slides:
        slide["notes"] = build_slide_notes(slide)
    return slides[:max_slides]


def render_notes_html(text: str) -> str:
    return f"<aside class=\"notes\">{html_text(text)}</aside>"


def image_src(image: Dict[str, object]) -> str:
    if image.get("output_rel"):
        return html_text(f"assets/{image['output_rel']}")
    if image.get("source_url"):
        return html_text(str(image["source_url"]))
    return ""


def render_figure(image: Dict[str, object], *, compact: bool = False) -> str:
    caption = html_text(str(image.get("caption") or "Visual extract"))
    source = image_src(image)
    figure_class = "doc-figure compact" if compact else "doc-figure"
    fig_id = html_text(str(image.get("id") or "figure"))
    return "\n".join(
        [
            f"          <figure class=\"{figure_class}\">",
            f"            <div class=\"figure-frame\" data-fig=\"{fig_id}\">",
            f"              <img src=\"{source}\" alt=\"{caption}\">",
            "            </div>",
            f"            <figcaption>{caption}</figcaption>",
            "          </figure>",
        ]
    )


def render_hero_slide(slide: Dict[str, object]) -> str:
    stats = "\n".join(
        f"            <li>{html_text(str(item))}</li>" for item in slide.get("stats", [])
    )
    return "\n".join(
        [
            "      <section class=\"doc-slide hero-slide\">",
            "        <div class=\"doc-shell hero-shell\">",
            "          <div class=\"eyebrow\">Anything To Slides</div>",
            f"          <h1>{html_text(str(slide['title']))}</h1>",
            f"          <p class=\"hero-lede\">{html_text(str(slide.get('lede') or ''))}</p>",
            "          <div class=\"hero-meta\">",
            f"            <span>{html_text(str(slide.get('doc_shape') or 'Structured talk'))}</span>",
            f"            <span>{html_text(str(slide.get('audience') or 'General audience'))}</span>",
            "          </div>",
            "          <ul class=\"meta-pill-list\">",
            stats,
            "          </ul>",
            render_notes_html(str(slide.get("notes") or "")),
            "        </div>",
            "      </section>",
        ]
    )


def render_overview_slide(slide: Dict[str, object]) -> str:
    highlight_items = "\n".join(
        f"              <li>{html_text(str(item))}</li>" for item in slide.get("highlights", [])
    )
    stat_items = "\n".join(
        f"              <li>{html_text(str(item))}</li>" for item in slide.get("stats", [])
    )
    return "\n".join(
        [
            "      <section class=\"doc-slide\">",
            "        <div class=\"doc-shell\">",
            f"          <h2>{html_text(str(slide['title']))}</h2>",
            "          <div class=\"doc-grid doc-grid-2\">",
            "            <article class=\"doc-card\">",
            "              <div class=\"card-eyebrow\">Deck strategy</div>",
            f"              <p class=\"card-lede\">{html_text(str(slide.get('doc_shape') or 'Structured talk'))}</p>",
            f"              <p>{html_text(str(slide.get('audience') or 'General audience'))}</p>",
            "            </article>",
            "            <article class=\"doc-card\">",
            "              <div class=\"card-eyebrow\">Extraction snapshot</div>",
            "              <ul class=\"doc-list\">",
            stat_items,
            "              </ul>",
            "            </article>",
            "          </div>",
            "          <div class=\"doc-callout\">",
            "            <div class=\"card-eyebrow\">Top threads to carry through the talk</div>",
            "            <ul class=\"doc-list\">",
            highlight_items,
            "            </ul>",
            "          </div>",
            render_notes_html(str(slide.get("notes") or "")),
            "        </div>",
            "      </section>",
        ]
    )


def render_agenda_slide(slide: Dict[str, object]) -> str:
    items = "\n".join(
        "\n".join(
            [
                "            <li>",
                f"              <span class=\"agenda-index\">{index + 1:02d}</span>",
                f"              <span>{html_text(str(item))}</span>",
                "            </li>",
            ]
        )
        for index, item in enumerate(slide.get("items", []))
    )
    return "\n".join(
        [
            "      <section class=\"doc-slide section-slide\">",
            "        <div class=\"doc-shell\">",
            f"          <h2>{html_text(str(slide['title']))}</h2>",
            "          <ol class=\"agenda-list\">",
            items,
            "          </ol>",
            render_notes_html(str(slide.get("notes") or "")),
            "        </div>",
            "      </section>",
        ]
    )


def render_content_slide(slide: Dict[str, object]) -> str:
    bullets = "\n".join(
        f"              <li>{html_text(str(item))}</li>" for item in slide.get("bullets", [])
    )
    images = slide.get("images", [])
    image_block = ""
    if images:
        image_block = "\n".join(
            [
                "            <div class=\"doc-media-stack\">",
                render_figure(images[0], compact=bool(len(images) > 1)),
                render_figure(images[1], compact=True) if len(images) > 1 else "",
                "            </div>",
            ]
        )
    else:
        image_block = "\n".join(
            [
                "            <div class=\"doc-callout side-callout\">",
                "              <div class=\"card-eyebrow\">Source anchor</div>",
                f"              <p>{html_text(str(slide.get('source_ref') or 'Text-driven section'))}</p>",
                "            </div>",
            ]
        )

    return "\n".join(
        [
            "      <section class=\"doc-slide\">",
            "        <div class=\"doc-shell\">",
            f"          <div class=\"slide-kicker\">{html_text(str(slide.get('source_ref') or 'Core section'))}</div>",
            f"          <h2>{html_text(str(slide['title']))}</h2>",
            f"          <p class=\"slide-summary\">{html_text(str(slide.get('summary') or ''))}</p>",
            "          <div class=\"doc-two-col\">",
            "            <div class=\"doc-copy\">",
            "              <ul class=\"doc-list strong-list\">",
            bullets,
            "              </ul>",
            "            </div>",
            "            <div class=\"doc-side\">",
            image_block,
            "            </div>",
            "          </div>",
            render_notes_html(str(slide.get("notes") or "")),
            "        </div>",
            "      </section>",
        ]
    )


def render_gallery_slide(slide: Dict[str, object]) -> str:
    bullets = "\n".join(
        f"              <li>{html_text(str(item))}</li>" for item in slide.get("bullets", [])
    )
    figures = "\n".join(render_figure(image, compact=True) for image in slide.get("images", []))
    return "\n".join(
        [
            "      <section class=\"doc-slide\">",
            "        <div class=\"doc-shell\">",
            f"          <div class=\"slide-kicker\">{html_text(str(slide.get('source_ref') or 'Visual evidence'))}</div>",
            f"          <h2>{html_text(str(slide['title']))}</h2>",
            f"          <p class=\"slide-summary\">{html_text(str(slide.get('summary') or ''))}</p>",
            "          <div class=\"doc-two-col gallery-layout\">",
            "            <div class=\"doc-copy\">",
            "              <ul class=\"doc-list strong-list\">",
            bullets,
            "              </ul>",
            "            </div>",
            "            <div class=\"doc-side\">",
            "              <div class=\"doc-gallery-grid\">",
            figures,
            "              </div>",
            "            </div>",
            "          </div>",
            render_notes_html(str(slide.get("notes") or "")),
            "        </div>",
            "      </section>",
        ]
    )


def render_takeaways_slide(slide: Dict[str, object]) -> str:
    items = "\n".join(
        "\n".join(
            [
                "            <article class=\"doc-card takeaway-card\">",
                f"              <span class=\"agenda-index\">{index + 1:02d}</span>",
                f"              <p>{html_text(str(item))}</p>",
                "            </article>",
            ]
        )
        for index, item in enumerate(slide.get("items", []))
    )
    return "\n".join(
        [
            "      <section class=\"doc-slide section-slide\">",
            "        <div class=\"doc-shell\">",
            f"          <h2>{html_text(str(slide['title']))}</h2>",
            "          <div class=\"doc-grid doc-grid-2\">",
            items,
            "          </div>",
            render_notes_html(str(slide.get("notes") or "")),
            "        </div>",
            "      </section>",
        ]
    )


def render_closing_slide(slide: Dict[str, object]) -> str:
    items = "\n".join(
        f"            <li>{html_text(str(item))}</li>" for item in slide.get("items", [])
    )
    return "\n".join(
        [
            "      <section class=\"doc-slide closing-slide\">",
            "        <div class=\"doc-shell hero-shell compact\">",
            "          <div class=\"eyebrow\">Next Step</div>",
            f"          <h2>{html_text(str(slide['title']))}</h2>",
            "          <ul class=\"meta-pill-list closing-list\">",
            items,
            "          </ul>",
            render_notes_html(str(slide.get("notes") or "")),
            "        </div>",
            "      </section>",
        ]
    )


def render_slide(slide: Dict[str, object]) -> str:
    kind = slide["kind"]
    if kind == "hero":
        return render_hero_slide(slide)
    if kind == "overview":
        return render_overview_slide(slide)
    if kind == "agenda":
        return render_agenda_slide(slide)
    if kind == "gallery":
        return render_gallery_slide(slide)
    if kind == "takeaways":
        return render_takeaways_slide(slide)
    if kind == "closing":
        return render_closing_slide(slide)
    return render_content_slide(slide)


def build_html(manifest: Dict[str, object], slides: Sequence[Dict[str, object]], template_path: Path) -> str:
    rendered_slides = [render_slide(slide) for slide in slides]
    template = template_path.read_text(encoding="utf-8")
    title = str(manifest.get("title") or Path(str(manifest["source_file"])).stem)
    return (
        template.replace("{{TITLE}}", html_text(title))
        .replace("{{SOURCE_FILE}}", html_text(Path(str(manifest["source_file"])).name))
        .replace("{{REVEAL_WIDTH}}", str(DEFAULT_REVEAL_WIDTH))
        .replace("{{REVEAL_HEIGHT}}", str(DEFAULT_REVEAL_HEIGHT))
        .replace("{{SLIDES}}", "\n".join(rendered_slides))
    )


def build_notes(manifest: Dict[str, object], slides: Sequence[Dict[str, object]], template_path: Path) -> str:
    chunks: List[str] = []
    for index, slide in enumerate(slides, start=1):
        lines = [
            f"## Slide {index} — {slide['title']}",
            "",
            f"**Slide type:** {slide['kind']}",
            "",
            "**Presenter notes:**",
            str(slide.get("notes") or "No notes generated."),
            "",
        ]
        if slide.get("bullets"):
            lines.append("**On-screen bullets:**")
            lines.extend([f"- {item}" for item in slide["bullets"]])
            lines.append("")
        if slide.get("images"):
            lines.append("**Visuals:**")
            lines.extend([f"- {image.get('caption') or image.get('id')}" for image in slide["images"]])
            lines.append("")
        chunks.append("\n".join(lines).rstrip())

    title = str(manifest.get("title") or Path(str(manifest["source_file"])).stem)
    return (
        template_path.read_text(encoding="utf-8")
        .replace("{{TITLE}}", title)
        .replace("{{SLIDE_NOTES}}", "\n\n".join(chunks))
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

    slides = build_slide_plan(manifest, max(8, args.max_slides))

    (output_dir / "assets" / "css").mkdir(parents=True, exist_ok=True)
    copy_media(bundle_dir, output_dir)
    shutil.copy2(skill_dir / "assets" / "slides.css", output_dir / "assets" / "css" / "style.css")

    html_output = build_html(manifest, slides, skill_dir / "assets" / "template_shell.html")
    notes_output = build_notes(manifest, slides, skill_dir / "assets" / "speaker_notes_template.md")

    (output_dir / "index.html").write_text(html_output, encoding="utf-8")
    (output_dir / "speaker_notes.md").write_text(notes_output, encoding="utf-8")

    print(f"Wrote {output_dir / 'index.html'}")
    print(f"Wrote {output_dir / 'speaker_notes.md'}")
    print(f"Rendered {len(slides)} slides")


if __name__ == "__main__":
    main()
