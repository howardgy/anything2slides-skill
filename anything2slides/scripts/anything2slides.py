#!/usr/bin/env python3
"""Unified entrypoint for converting sources into Reveal.js decks."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


PPT_EXTENSIONS = {".ppt", ".pptx"}
DOC_EXTENSIONS = {".pdf", ".docx", ".md", ".markdown", ".html", ".htm", ".txt", ".text"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert PPT/PPTX or document sources into a Reveal.js deck.",
    )
    parser.add_argument("source", help="Path to source file")
    parser.add_argument("output_dir", help="Directory for the final HTML deck")
    parser.add_argument(
        "--work-dir",
        help="Optional working directory for extracted bundles and conversions",
    )
    parser.add_argument(
        "--skill-dir",
        default=str(Path(__file__).resolve().parent.parent),
        help="Skill root containing assets/ and scripts/",
    )
    parser.add_argument(
        "--max-slides",
        type=int,
        default=14,
        help="Maximum visible slides for document-style sources",
    )
    return parser.parse_args()


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def ensure_parent(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def convert_ppt_to_pptx(source_path: Path, work_dir: Path) -> Path:
    libreoffice = shutil.which("libreoffice")
    if not libreoffice:
        raise SystemExit(
            "Input is .ppt, but LibreOffice is not available. Convert it to .pptx first or install LibreOffice."
        )
    converted_dir = work_dir / "converted"
    ensure_parent(converted_dir)
    run([libreoffice, "--headless", "--convert-to", "pptx", "--outdir", str(converted_dir), str(source_path)])
    converted = converted_dir / f"{source_path.stem}.pptx"
    if not converted.exists():
        raise SystemExit(f"LibreOffice did not produce the expected file: {converted}")
    return converted


def main() -> None:
    args = parse_args()
    source_path = Path(args.source).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    skill_dir = Path(args.skill_dir).expanduser().resolve()
    work_dir = Path(args.work_dir).expanduser().resolve() if args.work_dir else output_dir / "_work"

    if not source_path.exists():
        raise SystemExit(f"Input file not found: {source_path}")

    ensure_parent(output_dir)
    ensure_parent(work_dir)

    extension = source_path.suffix.lower()
    scripts_dir = skill_dir / "scripts"

    if extension not in PPT_EXTENSIONS | DOC_EXTENSIONS:
        raise SystemExit(f"Unsupported input type: {extension}")

    if extension == ".ppt":
        source_path = convert_ppt_to_pptx(source_path, work_dir)
        extension = ".pptx"

    if extension == ".pptx":
        bundle_dir = work_dir / "ppt_bundle"
        ensure_parent(bundle_dir)
        run([sys.executable, str(scripts_dir / "extract_pptx_bundle.py"), str(source_path), str(bundle_dir)])
        run(
            [
                sys.executable,
                str(scripts_dir / "bootstrap_reveal_from_bundle.py"),
                str(bundle_dir),
                str(output_dir),
                "--skill-dir",
                str(skill_dir),
            ]
        )
        return

    bundle_dir = work_dir / "document_bundle"
    ensure_parent(bundle_dir)
    run([sys.executable, str(scripts_dir / "extract_document_bundle.py"), str(source_path), str(bundle_dir)])
    run(
        [
            sys.executable,
            str(scripts_dir / "bootstrap_reveal_from_document_bundle.py"),
            str(bundle_dir),
            str(output_dir),
            "--skill-dir",
            str(skill_dir),
            "--max-slides",
            str(args.max_slides),
        ]
    )


if __name__ == "__main__":
    main()
