#!/usr/bin/env python3
"""
Chunker: découpe le texte en chunks seamless pour TTS.

Stratégie:
  - Petit doc (< 5000 chars): un seul chunk
  - Gros doc: split aux frontières de phrases
  - Chaque chunk reste sous 5000 chars (limite safe edge-tts)
  - Évite de couper au milieu d'une phrase
"""
import re
from typing import List

# edge-tts peut gérer jusqu'à ~10k chars par requête, mais on garde une marge
MAX_CHUNK_CHARS = 4000
MIN_CHUNK_CHARS = 500  # éviter trop de micro-chunks


def chunk(text: str) -> List[str]:
    """
    Découpe le texte en chunks seamless.

    Returns: liste de strings, chacune étant un chunk audio indépendant.
    """
    if len(text) <= MAX_CHUNK_CHARS:
        return [text]

    # Stratégie: split aux paragraphes d'abord, puis aux phrases si trop gros
    chunks = _split_paragraphs(text, MAX_CHUNK_CHARS)

    # Vérifier qu'aucun chunk ne dépasse (peut arriver avec un paragraphe géant)
    final = []
    for c in chunks:
        if len(c) <= MAX_CHUNK_CHARS:
            final.append(c)
        else:
            # Découper aux phrases
            final.extend(_split_sentences(c, MAX_CHUNK_CHARS))
    return final


def _split_paragraphs(text: str, max_chars: int) -> List[str]:
    """Split aux frontières de paragraphes (\\n\\n)."""
    paragraphs = re.split(r"\n\s*\n", text)
    chunks = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # Si ajouter ce paragraphe dépasse la limite
        if len(current) + len(para) + 2 > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            # Si le paragraphe seul est déjà trop gros, on le garde tel quel
            # (sera re-split aux phrases)
            if len(para) > max_chars:
                chunks.append(para)
            else:
                current = para
        else:
            current = (current + "\n\n" + para).strip()

    if current:
        chunks.append(current.strip())

    return chunks


def _split_sentences(text: str, max_chars: int) -> List[str]:
    """Split aux frontières de phrases (., !, ?, :, ;, •, nouvelle ligne)."""
    # Regex: split après [.!?]\s+ ou après \n
    sentence_end = re.compile(r"(?<=[.!?])\s+|\n+")
    sentences = sentence_end.split(text)
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks = []
    current = ""

    for sent in sentences:
        if len(current) + len(sent) + 1 > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            # Phrase seule trop longue: on la tronque (rare)
            if len(sent) > max_chars:
                chunks.append(sent[:max_chars])
            else:
                current = sent
        else:
            current = (current + " " + sent).strip()

    if current:
        chunks.append(current.strip())

    return chunks


def estimate_duration(text: str, chars_per_sec: float = 20.0) -> float:
    """
    Estime la durée audio en secondes.
    ~20 chars/sec pour edge-tts voix Azure (français, vitesse normale).
    """
    return len(text) / chars_per_sec


def chunk_count(text: str) -> int:
    """Compte combien de chunks le texte produirait (sans les générer)."""
    return len(chunk(text))
