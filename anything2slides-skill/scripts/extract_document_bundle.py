#!/usr/bin/env python3
"""Extract text, structure, and images from document-like sources."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import shutil
import zipfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

try:
    import fitz  # type: ignore
except ImportError:  # pragma: no cover - optional dependency in runtime only
    fitz = None

try:
    import numpy as np  # type: ignore
except ImportError:  # pragma: no cover - optional dependency in runtime only
    np = None

try:
    from PIL import Image  # type: ignore
except ImportError:  # pragma: no cover - optional dependency in runtime only
    Image = None


W_NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".markdown", ".html", ".htm", ".txt", ".text"}
KNOWN_SECTION_TITLES = {
    "abstract",
    "background",
    "conclusion",
    "discussion",
    "findings",
    "future work",
    "implementation",
    "introduction",
    "limitations",
    "materials and methods",
    "method",
    "methodology",
    "motivation",
    "overview",
    "problem",
    "related work",
    "results",
    "summary",
    "takeaways",
    "一、背景",
    "一、研究背景",
    "二、方法",
    "三、结果",
    "四、讨论",
    "五、结论",
    "摘要",
    "引言",
    "方法",
    "结果",
    "讨论",
    "结论",
    "总结",
}
SKIP_SECTION_PATTERNS = (
    re.compile(r"^\s*references?\s*$", re.IGNORECASE),
    re.compile(r"^\s*bibliography\s*$", re.IGNORECASE),
    re.compile(r"^\s*acknowledg(e)?ments?\s*$", re.IGNORECASE),
    re.compile(r"^\s*appendix\s*$", re.IGNORECASE),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract a structured bundle from a PDF, DOCX, Markdown, HTML, or TXT file.",
    )
    parser.add_argument("source", help="Path to source document")
    parser.add_argument("output_dir", help="Directory for extracted bundle")
    return parser.parse_args()


def normalize_whitespace(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text.replace("\u00a0", " ")).strip()


def clean_paragraph(text: str) -> str:
    text = text.replace("\r", "\n")
    lines = [normalize_whitespace(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    return " ".join(lines).strip()


def short_text(text: str, limit: int = 180) -> str:
    value = normalize_whitespace(text)
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", value).strip("-").lower()
    return slug or "item"


def count_tokens(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]", text))


def split_sentences(text: str) -> List[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    parts = re.split(r"(?<=[。！？!?;；.])\s+", normalized)
    sentences = [part.strip() for part in parts if part.strip()]
    if sentences:
        return sentences
    return [normalized]


def contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


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


def language_hint(text: str) -> str:
    sample = text[:2000]
    return "zh" if contains_cjk(sample) else "en"


def infer_doc_shape(text: str) -> str:
    lowered = text.casefold()
    if any(token in lowered for token in ("abstract", "method", "results", "discussion", "conclusion")):
        return "research talk"
    if any(token in lowered for token in ("roadmap", "timeline", "milestone", "plan", "proposal")):
        return "proposal briefing"
    if any(token in lowered for token in ("tutorial", "workflow", "guide", "how to", "walkthrough")):
        return "tutorial"
    if any(token in lowered for token in ("status", "update", "progress", "weekly", "monthly")):
        return "status update"
    if contains_cjk(text) and any(token in text for token in ("研究", "方法", "结果", "结论")):
        return "research talk"
    if contains_cjk(text) and any(token in text for token in ("方案", "计划", "路线图", "里程碑")):
        return "proposal briefing"
    return "structured explainer"


def infer_audience(text: str, shape: str) -> str:
    if shape in {"research talk", "proposal briefing"}:
        return "technical audience"
    if contains_cjk(text) and re.search(r"[A-Za-z]{3,}", text):
        return "mixed technical audience"
    if sum(ch.isdigit() for ch in text[:3000]) > 12:
        return "data-literate audience"
    return "general professional audience"


def looks_like_heading(text: str) -> bool:
    line = normalize_whitespace(text)
    if not line or len(line) > 90:
        return False
    if re.search(r"[。！？!?;；,:，：]$", line):
        return False
    lowered = line.casefold()
    if lowered in KNOWN_SECTION_TITLES:
        return True
    if re.match(r"^(chapter|section)\s+\d+\b", lowered):
        return True
    if re.match(r"^\d+(\.\d+)*[\s\-:：、)]{1,3}.+", line):
        return True
    if re.match(r"^[ivxlcdm]+[\.\)]\s+.+", lowered):
        return True
    if re.match(r"^[一二三四五六七八九十]+[、.]\s*.+", line):
        return True
    if re.match(r"^[（(]?[一二三四五六七八九十0-9]+[)）]\s*.+", line):
        return True
    words = line.split()
    if len(words) <= 9 and all(word[:1].isupper() for word in words if word[:1].isalpha()):
        return True
    if contains_cjk(line) and len(line) <= 24 and not re.search(r"\s", line):
        return True
    return False


def safe_section_title(text: str, index: int) -> str:
    cleaned = short_text(text, 80).strip()
    return cleaned or f"Section {index}"


def add_source_ref(section: Dict[str, object], source_ref: Optional[str]) -> None:
    if not source_ref:
        return
    refs = section.setdefault("source_refs", [])
    if source_ref not in refs:
        refs.append(source_ref)


def new_section(title: str, index: int, level: int = 1) -> Dict[str, object]:
    return {
        "id": f"section-{index}",
        "title": safe_section_title(title, index),
        "level": level,
        "paragraphs": [],
        "bullets": [],
        "source_refs": [],
    }


def finalize_sections(sections: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    normalized: List[Dict[str, object]] = []
    for section in sections:
        paragraphs = [clean_paragraph(text) for text in section.get("paragraphs", []) if clean_paragraph(text)]
        bullets = [clean_paragraph(text) for text in section.get("bullets", []) if clean_paragraph(text)]
        refs = dedupe_keep_order(str(ref) for ref in section.get("source_refs", []) if ref)
        if not paragraphs and not bullets:
            continue
        candidate = dict(section)
        candidate["paragraphs"] = paragraphs
        candidate["bullets"] = bullets
        candidate["source_refs"] = refs
        title = str(candidate.get("title") or "").strip()

        if normalized and count_tokens(" ".join(paragraphs) + " " + " ".join(bullets)) < 36 and not looks_like_heading(title):
            normalized[-1]["paragraphs"].extend(paragraphs)
            normalized[-1]["bullets"].extend(bullets)
            normalized[-1]["source_refs"] = dedupe_keep_order(
                list(normalized[-1].get("source_refs", [])) + refs
            )
            continue

        candidate["title"] = safe_section_title(title, len(normalized) + 1)
        normalized.append(candidate)

    if not normalized:
        return [new_section("Core Material", 1)]
    return normalized


def choose_title_from_lines(lines: Sequence[str], fallback: str) -> str:
    for line in lines:
        cleaned = normalize_whitespace(line)
        if cleaned and len(cleaned) <= 160:
            return cleaned
    return fallback


def derive_highlights(sections: Sequence[Dict[str, object]]) -> List[str]:
    picks: List[str] = []
    for section in sections:
        title = str(section.get("title") or "").strip()
        if title and not any(pattern.match(title) for pattern in SKIP_SECTION_PATTERNS):
            picks.append(title)
        for bullet in section.get("bullets", []):
            picks.append(short_text(str(bullet), 120))
        for paragraph in section.get("paragraphs", []):
            first_sentence = split_sentences(str(paragraph))[:1]
            if first_sentence:
                picks.append(short_text(first_sentence[0], 120))
        if len(picks) >= 8:
            break
    return dedupe_keep_order([pick for pick in picks if pick])[:5]


def build_outline(manifest: Dict[str, object]) -> str:
    lines = [
        f"# Source Outline — {Path(str(manifest['source_file'])).name}",
        "",
        f"- Source type: {manifest['source_type']}",
        f"- Title: {manifest['title']}",
        f"- Words extracted: {manifest['word_count']}",
        f"- Sections: {len(manifest['sections'])}",
        f"- Images: {len(manifest['images'])}",
        f"- Suggested talk shape: {manifest['overview']['doc_shape']}",
        f"- Suggested audience: {manifest['overview']['audience']}",
        "",
    ]
    for section in manifest["sections"]:
        refs = ", ".join(section.get("source_refs", [])[:2]) or "n/a"
        lines.append(f"## {section['title']}")
        lines.append(f"- Source refs: {refs}")
        lines.append(f"- Paragraphs: {len(section.get('paragraphs', []))}")
        lines.append(f"- Bullets: {len(section.get('bullets', []))}")
        preview = ""
        if section.get("bullets"):
            preview = str(section["bullets"][0])
        elif section.get("paragraphs"):
            preview = split_sentences(str(section["paragraphs"][0]))[:1][0]
        if preview:
            lines.append(f"- Anchor: {short_text(preview, 160)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def copy_local_asset(
    image_path: Path,
    media_dir: Path,
    *,
    prefix: str,
    source_ref: Optional[str],
    section_hint: Optional[str],
    alt: str = "",
) -> Dict[str, object]:
    suffix = image_path.suffix.lower() or ".bin"
    digest = hashlib.sha1(str(image_path.resolve()).encode("utf-8")).hexdigest()[:10]
    filename = f"{prefix}-{digest}{suffix}"
    destination = media_dir / filename
    if not destination.exists():
        shutil.copy2(image_path, destination)
    return {
        "id": slugify(f"{prefix}-{image_path.stem}")[:48],
        "caption": alt or image_path.stem.replace("_", " ").replace("-", " "),
        "source_ref": source_ref or "",
        "section_hint": section_hint or "",
        "output_rel": f"media/{filename}",
        "origin": "local",
    }


def resolve_image_reference(source_path: Path, ref: str) -> Optional[Path]:
    candidate = ref.strip().strip('"').strip("'")
    if not candidate or re.match(r"^[a-z]+://", candidate, re.IGNORECASE):
        return None
    parsed = urlparse(candidate)
    path_part = unquote(parsed.path if parsed.scheme == "file" else candidate)
    path = Path(path_part)
    if not path.is_absolute():
        path = (source_path.parent / path).resolve()
    if path.exists() and path.is_file():
        return path
    return None


def collect_markdown_images(source_path: Path, text: str, media_dir: Path) -> List[Dict[str, object]]:
    images: List[Dict[str, object]] = []
    seen = set()
    markdown_pattern = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<src>[^)]+)\)")
    html_pattern = re.compile(r"<img[^>]+src=[\"'](?P<src>[^\"']+)[\"'][^>]*>", re.IGNORECASE)
    for match in markdown_pattern.finditer(text):
        src = match.group("src")
        alt = match.group("alt")
        resolved = resolve_image_reference(source_path, src)
        if not resolved:
            continue
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        images.append(
            copy_local_asset(resolved, media_dir, prefix="md", source_ref="", section_hint="", alt=alt)
        )
    for match in html_pattern.finditer(text):
        src = match.group("src")
        resolved = resolve_image_reference(source_path, src)
        if not resolved:
            continue
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        images.append(
            copy_local_asset(resolved, media_dir, prefix="html", source_ref="", section_hint="", alt="")
        )
    return images


def parse_markdown(source_path: Path, media_dir: Path) -> Tuple[str, List[Dict[str, object]], List[Dict[str, object]]]:
    text = source_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    title = ""
    sections: List[Dict[str, object]] = []
    current = new_section("Opening Frame", 1)
    paragraph_buffer: List[str] = []
    section_index = 1

    def flush_paragraph() -> None:
        if paragraph_buffer:
            current["paragraphs"].append(" ".join(paragraph_buffer).strip())
            paragraph_buffer.clear()

    front_matter = False
    if lines and lines[0].strip() == "---":
        front_matter = True
    for idx, raw_line in enumerate(lines):
        line = raw_line.rstrip()
        if front_matter:
            if idx > 0 and line.strip() == "---":
                front_matter = False
            continue
        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        bullet = re.match(r"^\s*[-*+]\s+(.*)$", line)
        ordered = re.match(r"^\s*\d+\.\s+(.*)$", line)
        if heading:
            flush_paragraph()
            heading_text = normalize_whitespace(heading.group(2))
            level = len(heading.group(1))
            if level == 1 and not title:
                title = heading_text
                if current["paragraphs"] or current["bullets"]:
                    sections.append(current)
                current = new_section("Opening Frame", section_index)
                continue
            if current["paragraphs"] or current["bullets"]:
                sections.append(current)
            section_index += 1
            current = new_section(heading_text, section_index, level)
            continue
        if markdown_image := re.match(r"!\[[^\]]*\]\([^)]+\)", line.strip()):
            flush_paragraph()
            continue
        if bullet:
            flush_paragraph()
            current["bullets"].append(normalize_whitespace(bullet.group(1)))
            continue
        if ordered:
            flush_paragraph()
            current["bullets"].append(normalize_whitespace(ordered.group(1)))
            continue
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            continue
        paragraph_buffer.append(stripped)

    flush_paragraph()
    if current["paragraphs"] or current["bullets"]:
        sections.append(current)

    images = collect_markdown_images(source_path, text, media_dir)
    if not title:
        title = choose_title_from_lines(lines, source_path.stem)
    return title, finalize_sections(sections), images


def parse_html(source_path: Path, media_dir: Path) -> Tuple[str, List[Dict[str, object]], List[Dict[str, object]]]:
    html = source_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    for tag_name in ("script", "style", "noscript"):
        for node in soup.find_all(tag_name):
            node.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = normalize_whitespace(soup.title.string)

    sections: List[Dict[str, object]] = []
    current = new_section("Opening Frame", 1)
    section_index = 1
    images: List[Dict[str, object]] = []
    seen_images = set()

    body = soup.body or soup
    for element in body.find_all(["h1", "h2", "h3", "p", "li", "img"]):
        name = element.name.lower()
        text = normalize_whitespace(element.get_text(" ", strip=True))
        if name in {"h1", "h2", "h3"}:
            if name == "h1" and not title and text:
                title = text
                continue
            if current["paragraphs"] or current["bullets"]:
                sections.append(current)
            section_index += 1
            current = new_section(text or f"Section {section_index}", section_index, int(name[1]))
            continue
        if name == "p":
            if text:
                current["paragraphs"].append(text)
            continue
        if name == "li":
            if text:
                current["bullets"].append(text)
            continue
        if name == "img":
            src = element.get("src", "").strip()
            resolved = resolve_image_reference(source_path, src)
            if not resolved:
                continue
            key = str(resolved)
            if key in seen_images:
                continue
            seen_images.add(key)
            images.append(
                copy_local_asset(
                    resolved,
                    media_dir,
                    prefix="html",
                    source_ref="",
                    section_hint=str(current.get("title") or ""),
                    alt=element.get("alt", ""),
                )
            )

    if current["paragraphs"] or current["bullets"]:
        sections.append(current)
    if not title:
        title = choose_title_from_lines([element.get_text(" ", strip=True) for element in body.find_all(["h1", "h2", "p"])], source_path.stem)
    return title, finalize_sections(sections), images


def extract_docx_text(paragraph: ET.Element) -> str:
    texts = [(node.text or "") for node in paragraph.findall(".//w:t", W_NS)]
    return normalize_whitespace("".join(texts))


def parse_docx(source_path: Path, media_dir: Path) -> Tuple[str, List[Dict[str, object]], List[Dict[str, object]]]:
    title = source_path.stem
    sections: List[Dict[str, object]] = []
    current = new_section("Opening Frame", 1)
    section_index = 1
    images: List[Dict[str, object]] = []
    seen_targets = set()

    with zipfile.ZipFile(source_path) as archive:
        document_xml = ET.fromstring(archive.read("word/document.xml"))
        rels_root = ET.fromstring(archive.read("word/_rels/document.xml.rels"))
        relationships: Dict[str, str] = {}
        for rel in rels_root.findall("rel:Relationship", W_NS):
            rel_id = rel.attrib.get("Id")
            target = rel.attrib.get("Target")
            if rel_id and target:
                relationships[rel_id] = target

        body = document_xml.find("w:body", W_NS)
        if body is None:
            return title, finalize_sections(sections), images

        for child in body:
            if child.tag == f"{{{W_NS['w']}}}p":
                text = extract_docx_text(child)
                style_name = ""
                style = child.find("./w:pPr/w:pStyle", W_NS)
                if style is not None:
                    style_name = style.attrib.get(f"{{{W_NS['w']}}}val", "")
                if style_name.lower().startswith("title") and text:
                    title = text
                    continue
                if style_name.lower().startswith("heading") and text:
                    if current["paragraphs"] or current["bullets"]:
                        sections.append(current)
                    section_index += 1
                    level_match = re.search(r"(\d+)", style_name)
                    level = int(level_match.group(1)) if level_match else 1
                    current = new_section(text, section_index, level)
                elif text:
                    current["paragraphs"].append(text)

                for blip in child.findall(".//a:blip", W_NS):
                    rel_id = blip.attrib.get(f"{{{W_NS['r']}}}embed")
                    target = relationships.get(rel_id or "")
                    if not target:
                        continue
                    normalized_target = target.replace("\\", "/")
                    internal = f"word/{normalized_target}"
                    if internal in seen_targets or internal not in archive.namelist():
                        continue
                    seen_targets.add(internal)
                    data = archive.read(internal)
                    suffix = Path(internal).suffix.lower() or ".bin"
                    filename = f"docx-{len(images)+1:02d}{suffix}"
                    destination = media_dir / filename
                    destination.write_bytes(data)
                    images.append(
                        {
                            "id": f"docx-image-{len(images)+1}",
                            "caption": Path(internal).stem.replace("_", " "),
                            "source_ref": "",
                            "section_hint": str(current.get("title") or ""),
                            "output_rel": f"media/{filename}",
                            "origin": "docx-embedded",
                        }
                    )

    if current["paragraphs"] or current["bullets"]:
        sections.append(current)
    return title, finalize_sections(sections), images


def paragraphs_from_plain_text(text: str, source_ref: Optional[str]) -> List[Dict[str, str]]:
    entries: List[Dict[str, str]] = []
    buffer: List[str] = []
    for raw_line in text.splitlines():
        line = normalize_whitespace(raw_line)
        if not line:
            if buffer:
                entries.append({"text": "\n".join(buffer), "source_ref": source_ref or ""})
                buffer.clear()
            continue
        buffer.append(line)
    if buffer:
        entries.append({"text": "\n".join(buffer), "source_ref": source_ref or ""})
    return entries


def sectionalize_entries(entries: Sequence[Dict[str, str]], *, fallback_title: str) -> Tuple[str, List[Dict[str, object]]]:
    title = ""
    section_index = 1
    sections: List[Dict[str, object]] = []
    current = new_section("Opening Frame", section_index)

    for entry in entries:
        raw_text = entry.get("text", "")
        lines = [normalize_whitespace(line) for line in raw_text.splitlines() if normalize_whitespace(line)]
        if len(lines) >= 2 and looks_like_heading(lines[0]):
            heading = lines[0]
            if current["paragraphs"] or current["bullets"]:
                sections.append(current)
            section_index += 1
            current = new_section(heading, section_index)
            add_source_ref(current, entry.get("source_ref") or "")
            paragraph = clean_paragraph("\n".join(lines[1:]))
            if paragraph:
                current["paragraphs"].append(paragraph)
                add_source_ref(current, entry.get("source_ref") or "")
            continue

        paragraph = clean_paragraph(raw_text)
        if not paragraph:
            continue
        if not title:
            title = paragraph if len(paragraph) <= 180 else ""
            if title and len(entries) > 1:
                continue
        if looks_like_heading(paragraph):
            if current["paragraphs"] or current["bullets"]:
                sections.append(current)
            section_index += 1
            current = new_section(paragraph, section_index)
            add_source_ref(current, entry.get("source_ref") or "")
            continue
        current["paragraphs"].append(paragraph)
        add_source_ref(current, entry.get("source_ref") or "")

    if current["paragraphs"] or current["bullets"]:
        sections.append(current)

    return title or fallback_title, finalize_sections(sections)


def parse_txt(source_path: Path) -> Tuple[str, List[Dict[str, object]], List[Dict[str, object]]]:
    text = source_path.read_text(encoding="utf-8")
    title, sections = sectionalize_entries(
        paragraphs_from_plain_text(text, ""),
        fallback_title=source_path.stem,
    )
    return title, sections, []


def ensure_pdf_dependencies() -> None:
    missing: List[str] = []
    if fitz is None:
        missing.append("PyMuPDF")
    if np is None:
        missing.append("numpy")
    if Image is None:
        missing.append("Pillow")
    if missing:
        raise SystemExit(
            "PDF support requires the following Python packages to be installed: "
            + ", ".join(missing)
        )


def extract_pdf_title(doc: "fitz.Document", fallback: str) -> str:
    if not doc.page_count:
        return fallback

    first_page_text = doc[0].get_text("text")
    lines = [line.strip() for line in first_page_text.splitlines() if line.strip()]
    for line in lines:
        if len(line) > 20 and not line.startswith("http"):
            return line

    candidates: List[Tuple[float, str]] = []
    page = doc[0]
    page_dict = page.get_text("dict")
    for block in page_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            text_parts = []
            sizes = []
            for span in line.get("spans", []):
                span_text = normalize_whitespace(span.get("text", ""))
                if span_text:
                    text_parts.append(span_text)
                    sizes.append(float(span.get("size", 0.0)))
            text = normalize_whitespace(" ".join(text_parts))
            if text and len(text) <= 180:
                candidates.append((max(sizes) if sizes else 0.0, text))
    if not candidates:
        return fallback
    candidates.sort(key=lambda item: (-item[0], len(item[1])))
    return candidates[0][1]


def cluster_pdf_image_rects(page: "fitz.Page") -> List["fitz.Rect"]:
    img_info_list = page.get_image_info(hashes=False)
    if not img_info_list:
        return []

    rects = [fitz.Rect(info["bbox"]) for info in img_info_list if info.get("bbox")]
    clusters: List["fitz.Rect"] = []
    for rect in rects:
        merged = False
        for index, cluster in enumerate(clusters):
            if rect.distance_to(cluster) < 60:
                clusters[index] = cluster | rect
                merged = True
                break
        if not merged:
            clusters.append(rect)
    return clusters


def pil_to_gray_array(img: "Image.Image") -> "np.ndarray":
    return np.array(img.convert("L"))


def row_projection(gray: "np.ndarray", threshold: int = 240) -> "np.ndarray":
    return np.sum(gray < threshold, axis=1)


def col_projection(gray: "np.ndarray", threshold: int = 240) -> "np.ndarray":
    return np.sum(gray < threshold, axis=0)


def find_projection_gaps(
    projection: "np.ndarray", min_gap: int = 8, max_content: int = 10
) -> List[Tuple[int, int]]:
    gaps: List[Tuple[int, int]] = []
    in_gap = False
    gap_start = 0

    for index, value in enumerate(projection):
        if value <= max_content:
            if not in_gap:
                in_gap = True
                gap_start = index
        else:
            if in_gap:
                if index - gap_start >= min_gap:
                    gaps.append((gap_start, index))
                in_gap = False

    if in_gap and len(projection) - gap_start >= min_gap:
        gaps.append((gap_start, len(projection)))

    return gaps


def gaps_to_bands(
    gaps: List[Tuple[int, int]], total_size: int, margin: int = 2
) -> List[Tuple[int, int]]:
    bands: List[Tuple[int, int]] = []
    previous_end = 0

    for gap_start, gap_end in gaps:
        band_start = max(0, previous_end + margin)
        band_end = min(total_size, gap_start - margin)
        if band_end > band_start + 10:
            bands.append((band_start, band_end))
        previous_end = gap_end

    band_start = max(0, previous_end + margin)
    if total_size > band_start + 10:
        bands.append((band_start, total_size))

    return bands


def save_pdf_panels(
    figure_img: "Image.Image",
    figure_num: int,
    media_dir: Path,
    *,
    source_ref: str,
    threshold: int = 245,
    min_gap: int = 10,
    pad: int = 2,
) -> List[Dict[str, object]]:
    gray = pil_to_gray_array(figure_img)
    height, width = gray.shape

    row_proj = row_projection(gray, threshold)
    horizontal_gaps = find_projection_gaps(row_proj, min_gap=min_gap)
    horizontal_bands = gaps_to_bands(horizontal_gaps, height) or [(0, height)]

    labels = "abcdefghijklmnopqrstuvwxyz"
    panels: List[Dict[str, object]] = []
    label_index = 0

    for band_y0, band_y1 in horizontal_bands:
        band_gray = gray[band_y0:band_y1, :]
        col_proj = col_projection(band_gray, threshold)
        vertical_gaps = find_projection_gaps(col_proj, min_gap=min_gap)
        vertical_bands = gaps_to_bands(vertical_gaps, width) or [(0, width)]

        for band_x0, band_x1 in vertical_bands:
            x0 = max(0, band_x0 - pad)
            y0 = max(0, band_y0 - pad)
            x1 = min(width, band_x1 + pad)
            y1 = min(height, band_y1 + pad)

            panel_img = figure_img.crop((x0, y0, x1, y1))
            if panel_img.width < 100 or panel_img.height < 100:
                if panel_img.width < 50 or panel_img.height < 50:
                    continue

            label = labels[label_index] if label_index < len(labels) else str(label_index)
            filename = f"pdf-fig{figure_num}{label}.png"
            destination = media_dir / filename
            panel_img.save(destination, "PNG")
            panels.append(
                {
                    "id": f"pdf-fig{figure_num}{label}",
                    "caption": f"Figure {figure_num}{label.upper()}",
                    "source_ref": source_ref,
                    "section_hint": "",
                    "output_rel": f"media/{filename}",
                    "origin": "pdf-panel",
                    "kind": "panel",
                    "figure_num": figure_num,
                    "panel_label": label,
                    "score": panel_img.width * panel_img.height,
                }
            )
            label_index += 1

    return panels


def parse_pdf(source_path: Path, media_dir: Path) -> Tuple[str, List[Dict[str, object]], List[Dict[str, object]]]:
    ensure_pdf_dependencies()

    entries: List[Dict[str, str]] = []
    images: List[Dict[str, object]] = []
    figure_counter = 0

    with fitz.open(source_path) as doc:
        title = extract_pdf_title(doc, source_path.stem)
        for page_index, page in enumerate(doc, start=1):
            page_text = page.get_text("text", sort=True)
            entries.extend(paragraphs_from_plain_text(page_text, f"Page {page_index}"))
            page_area = page.rect.width * page.rect.height
            for rect in cluster_pdf_image_rects(page):
                expanded = rect + (-12, -12, 12, 12)
                expanded = expanded & page.rect
                image_area = expanded.width * expanded.height
                ratio = image_area / page_area if page_area else 0.0
                if ratio < 0.05:
                    if expanded.width < 100 and expanded.height < 100:
                        continue

                try:
                    pix = page.get_pixmap(clip=expanded, matrix=fitz.Matrix(4.0, 4.0), alpha=False)
                except Exception:
                    continue

                if pix.width < 100 or pix.height < 100:
                    if pix.width < 60 or pix.height < 60:
                        continue
                    if pix.width / max(1, pix.height) > 15 or pix.height / max(1, pix.width) > 15:
                        continue

                figure_counter += 1
                figure_img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
                filename = f"pdf-fig{figure_counter}.png"
                destination = media_dir / filename
                figure_img.save(destination, "PNG")

                panel_images = save_pdf_panels(
                    figure_img,
                    figure_counter,
                    media_dir,
                    source_ref=f"Page {page_index}",
                )
                images.append(
                    {
                        "id": f"pdf-figure-{figure_counter}",
                        "caption": f"Figure {figure_counter}",
                        "source_ref": f"Page {page_index}",
                        "section_hint": "",
                        "output_rel": f"media/{filename}",
                        "origin": "pdf-figure",
                        "kind": "figure",
                        "figure_num": figure_counter,
                        "panel_label": "",
                        "score": int(ratio * 100000),
                        "panel_count": len(panel_images),
                    }
                )
                images.extend(panel_images)

    parsed_title, sections = sectionalize_entries(entries, fallback_title=title)
    return parsed_title or title, sections, images


def extract_source(source_path: Path, media_dir: Path) -> Tuple[str, List[Dict[str, object]], List[Dict[str, object]]]:
    extension = source_path.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise SystemExit(f"Unsupported document type: {extension}")
    if extension in {".md", ".markdown"}:
        return parse_markdown(source_path, media_dir)
    if extension in {".html", ".htm"}:
        return parse_html(source_path, media_dir)
    if extension == ".docx":
        return parse_docx(source_path, media_dir)
    if extension == ".pdf":
        return parse_pdf(source_path, media_dir)
    return parse_txt(source_path)


def build_manifest(source_path: Path, title: str, sections: List[Dict[str, object]], images: List[Dict[str, object]]) -> Dict[str, object]:
    combined_text = "\n\n".join(
        ["\n".join(section.get("paragraphs", [])) + "\n" + "\n".join(section.get("bullets", [])) for section in sections]
    )
    doc_shape = infer_doc_shape(combined_text)
    manifest = {
        "source_file": str(source_path),
        "source_type": source_path.suffix.lower().lstrip("."),
        "title": title or source_path.stem,
        "language_hint": language_hint(combined_text),
        "word_count": count_tokens(combined_text),
        "paragraph_count": sum(len(section.get("paragraphs", [])) for section in sections),
        "sections": sections,
        "images": images,
        "overview": {
            "doc_shape": doc_shape,
            "audience": infer_audience(combined_text, doc_shape),
            "highlights": derive_highlights(sections),
        },
    }
    return manifest


def main() -> None:
    args = parse_args()
    source_path = Path(args.source).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    if not source_path.exists():
        raise SystemExit(f"Input file not found: {source_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    media_dir = output_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    title, sections, images = extract_source(source_path, media_dir)
    manifest = build_manifest(source_path, title, sections, images)

    manifest_path = output_dir / "manifest.json"
    outline_path = output_dir / "source_outline.md"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    outline_path.write_text(build_outline(manifest), encoding="utf-8")

    print(f"Wrote {manifest_path}")
    print(f"Wrote {outline_path}")
    print(f"Extracted {len(manifest['sections'])} sections and {len(manifest['images'])} images")


if __name__ == "__main__":
    main()
