#!/usr/bin/env python3
"""
TTS Engine: génère l'audio via edge-tts (Microsoft Azure neural voices).

Voix par défaut: fr-CA-SylvieNeural (français canadien, féminin, naturel)
Voix FR alternatives: fr-FR-DeniseNeural, fr-CA-AntoineNeural

Pour lister: edge-tts --list-voices
"""
import asyncio
import hashlib
import edge_tts
from pathlib import Path
from typing import Optional

# Voix par défaut: français canadien (Syll)
DEFAULT_VOICE = "fr-CA-SylvieNeural"
RATE = "+0%"  # Vitesse (peut être -50% à +100%)
PITCH = "+0Hz"  # Pitch


async def _synthesize(text: str, output_path: str, voice: str = DEFAULT_VOICE,
                      rate: str = RATE, pitch: str = PITCH) -> None:
    """Génère un fichier MP3 depuis le texte."""
    communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(output_path)


def synthesize(text: str, output_path: str, voice: str = DEFAULT_VOICE) -> str:
    """
    Sync wrapper pour synthesize. Retourne le path de l'audio généré.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(_synthesize(text, output_path, voice))
    return output_path


def voice_id(voice: str = DEFAULT_VOICE) -> str:
    """ID unique pour la voix (utilisé pour le cache key)."""
    return voice


def text_hash(text: str) -> str:
    """Hash du texte pour invalider le cache si le texte change."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def list_voices_sync() -> list:
    """Liste les voix disponibles (sync wrapper)."""
    async def _list():
        voices = await edge_tts.list_voices()
        return voices
    return asyncio.run(_list())


def filter_voices(voices: list, lang: str = "fr") -> list:
    """Filtre les voix par langue."""
    return [v for v in voices if v.get("Locale", "").startswith(lang)]
