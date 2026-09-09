#!/usr/bin/env python3
"""Pipeline: orchestre parser -> chunker -> tts_engine -> cache."""
import sys
from pathlib import Path
from typing import List, Optional, Callable

sys.path.insert(0, str(Path(__file__).parent))

from parser import parse
from chunker import chunk
from tts_engine import synthesize, DEFAULT_VOICE
from cache import get_cached_audio, audio_path
from tts_engine import text_hash


def prepare_audio(file_path, voice=DEFAULT_VOICE, progress_cb=None):
    text, meta = parse(file_path)
    chunks_text = chunk(text)
    chunks_audio = []
    for i, ctext in enumerate(chunks_text):
        h = text_hash(ctext)
        cached = get_cached_audio(h, voice)
        if cached:
            chunks_audio.append(str(cached))
        else:
            if progress_cb:
                progress_cb(i, len(chunks_text), f"Synthese chunk {i+1}/{len(chunks_text)}")
            out_path = audio_path(h, voice)
            synthesize(ctext, str(out_path), voice)
            chunks_audio.append(str(out_path))
        if progress_cb:
            progress_cb(i + 1, len(chunks_text), f"Chunk {i+1}/{len(chunks_text)} pret")
    return {
        "chunks_text": chunks_text,
        "chunks_audio": chunks_audio,
        "title": meta.get("title", Path(file_path).stem),
        "meta": meta,
    }


def estimate_total_duration(chunks_text, chars_per_sec=20.0):
    total_chars = sum(len(c) for c in chunks_text)
    return total_chars / chars_per_sec
