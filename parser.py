#!/usr/bin/env python3
"""
Parser: extrait le texte propre depuis .md, .txt, .pdf.

Returns: (texte:str, meta:dict) où meta contient le titre, le nombre de mots, etc.
"""
import re
from pathlib import Path
from typing import Tuple, Dict


def parse(path: str) -> Tuple[str, Dict]:
    """Parse un fichier et retourne (texte, metadata)."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Fichier introuvable: {path}")

    suffix = p.suffix.lower()
    if suffix == ".md":
        text, meta = _parse_md(p)
    elif suffix == ".txt":
        text, meta = _parse_txt(p)
    elif suffix == ".pdf":
        text, meta = _parse_pdf(p)
    else:
        # Fallback: essayer comme texte brut
        text, meta = _parse_txt(p)

    text = _clean(text)
    meta["file_path"] = str(p.resolve())
    meta["file_size"] = p.stat().st_size
    meta["word_count"] = len(text.split())
    meta["char_count"] = len(text)
    return text, meta


def _parse_md(p: Path) -> Tuple[str, Dict]:
    """Lit un .md, garde le contenu textuel, ignore la syntaxe markdown."""
    raw = p.read_text(encoding="utf-8", errors="replace")
    # Enlever blocs de code (```...```) car illisibles en TTS
    text = re.sub(r"```.*?```", " [bloc de code] ", raw, flags=re.DOTALL)
    # Enlever liens markdown [text](url) → garder text
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # Enlever images ![alt](url)
    text = re.sub(r"!\[[^\]]*\]\([^\)]+\)", "", text)
    # Enlever gras/italique markers
    text = re.sub(r"[*_]{1,3}([^*_]+)[*_]{1,3}", r"\1", text)
    # Enlever headers markers
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    # Extraire titre (premier # ou première ligne)
    title_match = re.search(r"^#\s+(.+)$", raw, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else p.stem
    return text, {"title": title, "format": "markdown"}


def _parse_txt(p: Path) -> Tuple[str, Dict]:
    """Lit un .txt brut."""
    text = p.read_text(encoding="utf-8", errors="replace")
    # Première ligne non-vide comme titre
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    title = lines[0][:80] if lines else p.stem
    return text, {"title": title, "format": "text"}


def _parse_pdf(p: Path) -> Tuple[str, Dict]:
    """Lit un .pdf avec pdfplumber, extrait le texte par page."""
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pip install pdfplumber pour lire les PDF")

    pages_text = []
    with pdfplumber.open(p) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages_text.append(text)

    text = "\n\n".join(pages_text)
    title = p.stem
    return text, {"title": title, "format": "pdf", "page_count": len(pages_text)}


def _clean(text: str) -> str:
    """Nettoie le texte pour TTS: espaces, caractères weird, etc."""
    # Normaliser les sauts de ligne
    text = re.sub(r"\r\n?", "\n", text)
    # Enlever lignes vides multiples
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Enlever espaces multiples
    text = re.sub(r"[ \t]{2,}", " ", text)
    # Enlever caractères de contrôle
    text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", text)
    return text.strip()
