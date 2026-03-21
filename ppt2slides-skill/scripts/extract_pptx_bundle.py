#!/usr/bin/env python3
"""Extract text, notes, media, and layout hints from a PPTX package."""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import shutil
import zipfile
from pathlib import Path
from typing import Dict, List, Optional
from xml.etree import ElementTree as ET


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

REL_NOTES = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract a structured bundle from a .pptx file.",
    )
    parser.add_argument("pptx", help="Path to input .pptx")
    parser.add_argument("output_dir", help="Directory for extracted bundle")
    return parser.parse_args()


def ensure_pptx(path: Path) -> None:
    if path.suffix.lower() != ".pptx":
        raise SystemExit(f"Expected a .pptx file, got: {path}")
    if not path.exists():
        raise SystemExit(f"Input file not found: {path}")


def load_xml(archive: zipfile.ZipFile, member: str) -> ET.Element:
    return ET.fromstring(archive.read(member))


def read_relationships(archive: zipfile.ZipFile, part_path: str) -> Dict[str, Dict[str, str]]:
    rels_path = relationship_path(part_path)
    if rels_path not in archive.namelist():
        return {}
    root = load_xml(archive, rels_path)
    rels: Dict[str, Dict[str, str]] = {}
    for rel in root.findall("rel:Relationship", NS):
        rel_id = rel.attrib["Id"]
        rels[rel_id] = {
            "target": resolve_target(part_path, rel.attrib["Target"]),
            "type": rel.attrib.get("Type", ""),
        }
    return rels


def relationship_path(part_path: str) -> str:
    directory, filename = posixpath.split(part_path)
    return posixpath.join(directory, "_rels", f"{filename}.rels")


def resolve_target(part_path: str, target: str) -> str:
    base_dir = posixpath.dirname(part_path)
    normalized = posixpath.normpath(posixpath.join(base_dir, target))
    return normalized


def get_text_runs(node: ET.Element) -> List[str]:
    values = []
    for text_node in node.findall(".//a:t", NS):
        text = (text_node.text or "").strip()
        if text:
            values.append(text)
    return values


def extract_geometry(node: ET.Element) -> Optional[Dict[str, int]]:
    xfrm = node.find(".//a:xfrm", NS)
    if xfrm is None:
        return None
    off = xfrm.find("a:off", NS)
    ext = xfrm.find("a:ext", NS)
    if off is None and ext is None:
        return None
    geometry: Dict[str, int] = {}
    if off is not None:
        geometry["x"] = int(off.attrib.get("x", "0"))
        geometry["y"] = int(off.attrib.get("y", "0"))
    if ext is not None:
        geometry["cx"] = int(ext.attrib.get("cx", "0"))
        geometry["cy"] = int(ext.attrib.get("cy", "0"))
    return geometry


def normalize_paragraphs(node: ET.Element) -> List[str]:
    paragraphs: List[str] = []
    for para in node.findall(".//a:p", NS):
        runs = get_text_runs(para)
        text = " ".join(runs).strip()
        if text:
            paragraphs.append(text)
    return paragraphs


def extract_text_blocks(slide_root: ET.Element) -> List[Dict[str, object]]:
    blocks: List[Dict[str, object]] = []
    for shape in slide_root.findall(".//p:sp", NS):
        paragraphs = normalize_paragraphs(shape)
        text = "\n".join(paragraphs).strip()
        if not text:
            continue
        c_nv_pr = shape.find("./p:nvSpPr/p:cNvPr", NS)
        placeholder = shape.find("./p:nvSpPr/p:nvPr/p:ph", NS)
        blocks.append(
            {
                "shape_id": int(c_nv_pr.attrib.get("id", "0")) if c_nv_pr is not None else None,
                "name": c_nv_pr.attrib.get("name", "") if c_nv_pr is not None else "",
                "placeholder": placeholder.attrib.get("type", "") if placeholder is not None else "",
                "text": text,
                "paragraphs": paragraphs,
                "geometry": extract_geometry(shape),
            }
        )
    return blocks


def extract_media(
    archive: zipfile.ZipFile,
    slide_path: str,
    slide_root: ET.Element,
    output_dir: Path,
) -> List[Dict[str, object]]:
    media_items: List[Dict[str, object]] = []
    rels = read_relationships(archive, slide_path)
    media_dir = output_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    for pic in slide_root.findall(".//p:pic", NS):
        c_nv_pr = pic.find("./p:nvPicPr/p:cNvPr", NS)
        blip = pic.find(".//a:blip", NS)
        if blip is None:
            continue
        rel_id = blip.attrib.get(f"{{{NS['r']}}}embed")
        if not rel_id or rel_id not in rels:
            continue
        source = rels[rel_id]["target"]
        filename = Path(source).name
        destination = media_dir / filename
        if not destination.exists():
            with archive.open(source) as src, destination.open("wb") as dst:
                shutil.copyfileobj(src, dst)
        media_items.append(
            {
                "shape_id": int(c_nv_pr.attrib.get("id", "0")) if c_nv_pr is not None else None,
                "name": c_nv_pr.attrib.get("name", "") if c_nv_pr is not None else "",
                "source": source,
                "output_rel": f"media/{filename}",
                "geometry": extract_geometry(pic),
            }
        )
    return media_items


def choose_title(text_blocks: List[Dict[str, object]], slide_number: int) -> str:
    for preferred in ("title", "ctrTitle", "subTitle"):
        for block in text_blocks:
            if block.get("placeholder") == preferred and block.get("text"):
                return str(block["text"]).splitlines()[0]
    for block in text_blocks:
        text = str(block.get("text", "")).strip()
        if text:
            return text.splitlines()[0][:120]
    return f"Slide {slide_number}"


def extract_notes(archive: zipfile.ZipFile, slide_path: str) -> str:
    rels = read_relationships(archive, slide_path)
    notes_path = None
    for rel in rels.values():
        if rel["type"] == REL_NOTES:
            notes_path = rel["target"]
            break
    if not notes_path or notes_path not in archive.namelist():
        return ""
    root = load_xml(archive, notes_path)
    raw = "\n".join(get_text_runs(root))
    cleaned = re.sub(r"\n{3,}", "\n\n", raw).strip()
    return cleaned


def extract_slide_size(archive: zipfile.ZipFile) -> Optional[Dict[str, int]]:
    presentation_path = "ppt/presentation.xml"
    if presentation_path not in archive.namelist():
        return None
    root = load_xml(archive, presentation_path)
    size = root.find("./p:sldSz", NS)
    if size is None:
        return None
    return {
        "cx": int(size.attrib.get("cx", "0")),
        "cy": int(size.attrib.get("cy", "0")),
    }


def ordered_slide_paths(archive: zipfile.ZipFile) -> List[str]:
    presentation_path = "ppt/presentation.xml"
    root = load_xml(archive, presentation_path)
    rels = read_relationships(archive, presentation_path)
    slide_paths: List[str] = []
    for slide_ref in root.findall("./p:sldIdLst/p:sldId", NS):
        rel_id = slide_ref.attrib.get(f"{{{NS['r']}}}id")
        if rel_id and rel_id in rels:
            slide_paths.append(rels[rel_id]["target"])
    return slide_paths


def build_outline(manifest: Dict[str, object]) -> str:
    lines = [
        f"# Slides Outline — {Path(str(manifest['source_file'])).name}",
        "",
        f"- Slide count: {manifest['slide_count']}",
        "",
    ]
    for slide in manifest["slides"]:
        lines.append(f"## Slide {slide['number']} — {slide['title']}")
        text_blocks = slide.get("text_blocks", [])
        if text_blocks:
            for block in text_blocks[:3]:
                first_line = str(block.get("text", "")).splitlines()[0]
                lines.append(f"- {first_line[:140]}")
        if slide.get("media"):
            lines.append(f"- Media items: {len(slide['media'])}")
        if slide.get("notes"):
            note_line = str(slide["notes"]).splitlines()[0]
            lines.append(f"- Notes: {note_line[:140]}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> None:
    args = parse_args()
    input_path = Path(args.pptx).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    ensure_pptx(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(input_path) as archive:
        slides = []
        for index, slide_path in enumerate(ordered_slide_paths(archive), start=1):
            slide_root = load_xml(archive, slide_path)
            text_blocks = extract_text_blocks(slide_root)
            slides.append(
                {
                    "number": index,
                    "path": slide_path,
                    "title": choose_title(text_blocks, index),
                    "notes": extract_notes(archive, slide_path),
                    "text_blocks": text_blocks,
                    "media": extract_media(archive, slide_path, slide_root, output_dir),
                }
            )

        manifest = {
            "source_file": str(input_path),
            "presentation_size": extract_slide_size(archive),
            "slide_count": len(slides),
            "slides": slides,
        }

    manifest_path = output_dir / "manifest.json"
    outline_path = output_dir / "slides_outline.md"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    outline_path.write_text(build_outline(manifest))

    print(f"Wrote {manifest_path}")
    print(f"Wrote {outline_path}")
    print(f"Extracted {manifest['slide_count']} slides")


if __name__ == "__main__":
    main()
