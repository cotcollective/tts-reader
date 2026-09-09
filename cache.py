#!/usr/bin/env python3
"""
Cache: cache lazy des chunks audio + bookmark position par fichier.

Structure:
  ~/.tts_reader_cache/
    audio/<hash_text>+<voice>.mp3     # audio généré
    bookmarks.json                      # position par fichier

Le hash combine (text_hash, voice) pour invalider si le texte ou la voix change.
Bookmark = {file_path: {position: int, updated_at: str}}
"""
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict
import time

CACHE_DIR = Path.home() / ".tts_reader_cache"
AUDIO_DIR = CACHE_DIR / "audio"
BOOKMARK_FILE = CACHE_DIR / "bookmarks.json"


def _ensure_dirs():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    if not BOOKMARK_FILE.exists():
        BOOKMARK_FILE.write_text("{}")


def audio_path(text_hash: str, voice: str) -> Path:
    """Path du fichier audio cachée pour un chunk donné."""
    _ensure_dirs()
    safe_voice = voice.replace("/", "_").replace("+", "")
    return AUDIO_DIR / f"{text_hash}_{safe_voice}.mp3"


def get_cached_audio(text_hash: str, voice: str) -> Optional[Path]:
    """Retourne le path de l'audio cachée, ou None si pas en cache."""
    p = audio_path(text_hash, voice)
    return p if p.exists() else None


def get_or_create_audio(text: str, voice: str, synth_fn) -> Path:
    """
    Retourne le path audio, en générant si pas en cache.

    synth_fn: callable(text, output_path) qui génère l'audio.
    """
    from .tts_engine import text_hash
    h = text_hash(text)
    cached = get_cached_audio(h, voice)
    if cached:
        return cached
    p = audio_path(h, voice)
    synth_fn(text, str(p))
    return p


# --- Bookmarks ---

def _load_bookmarks() -> Dict:
    _ensure_dirs()
    try:
        return json.loads(BOOKMARK_FILE.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def _save_bookmarks(data: Dict) -> None:
    _ensure_dirs()
    BOOKMARK_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def get_bookmark(file_path: str) -> int:
    """Retourne la position sauvegardée pour un fichier, 0 par défaut."""
    bookmarks = _load_bookmarks()
    entry = bookmarks.get(file_path, {})
    return int(entry.get("position", 0))


def set_bookmark(file_path: str, position: int) -> None:
    """Sauvegarde la position pour un fichier."""
    bookmarks = _load_bookmarks()
    bookmarks[file_path] = {
        "position": position,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    _save_bookmarks(bookmarks)


def list_bookmarks() -> Dict:
    """Liste tous les bookmarks."""
    return _load_bookmarks()


def clear_bookmark(file_path: str) -> None:
    """Efface le bookmark d'un fichier."""
    bookmarks = _load_bookmarks()
    if file_path in bookmarks:
        del bookmarks[file_path]
        _save_bookmarks(bookmarks)
