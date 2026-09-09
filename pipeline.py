#!/usr/bin/env python3
"""Pipeline: orchestre parser -> chunker -> tts_engine -> cache (scopé par backend)."""
import os
import sys
from pathlib import Path
from typing import Optional, Callable

sys.path.insert(0, str(Path(__file__).parent))

from parser import parse
from chunker import chunk
from tts_engine import synthesize, DEFAULT_VOICE, get_engine
from cache import get_cached_audio, audio_path
from tts_engine import text_hash


def prepare_audio(file_path, voice=DEFAULT_VOICE, engine=None, progress_cb=None):
    text, meta = parse(file_path)
    chunks_text = chunk(text)
    chunks_audio = []
    # engine résolu UNE fois avant la boucle (fail-safe: piper sauf voix edge connue / env override)
    resolved_engine = engine or os.environ.get("TTS_ENGINE", "").lower() or None
    if resolved_engine not in ("piper", "edge"):
        resolved_engine = get_engine(voice) if engine is None and not os.environ.get("TTS_ENGINE") else (resolved_engine or get_engine(voice))
    for i, ctext in enumerate(chunks_text):
        h = text_hash(ctext)
        cached = get_cached_audio(h, voice, resolved_engine)
        if cached:
            chunks_audio.append(str(cached))
        else:
            if progress_cb:
                progress_cb(i, len(chunks_text), f"Synthese chunk {i+1}/{len(chunks_text)} ({resolved_engine})")
            out_path = audio_path(h, voice, resolved_engine)
            synthesize(ctext, str(out_path), voice, engine=resolved_engine)
            chunks_audio.append(str(out_path))
            if progress_cb:
                progress_cb(i + 1, len(chunks_text), f"Chunk {i+1}/{len(chunks_text)} pret")
    return {
        "chunks_text": chunks_text,
        "chunks_audio": chunks_audio,
        "title": meta.get("title", Path(file_path).stem),
        "meta": meta,
        "engine": resolved_engine,
    }


def estimate_total_duration(chunks_text, chars_per_sec=20.0):
    total_chars = sum(len(c) for c in chunks_text)
    return total_chars / chars_per_sec