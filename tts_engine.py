#!/usr/bin/env python3
"""
TTS Engine — dual backend: piper (100% local) | edge-tts (Microsoft Azure neural, gratuit).

BACKENDS:
  - piper (défaut): 100% local, offline, voix fr_FR-siwis-medium. Texte JAMAIS envoyé dehors.
  - edge: edge-tts (Microsoft Azure) — qualité neurale supérieure, MAIS le texte part en clair
          vers speech.platform.bing.com. À éviter pour documents sensibles.

Voix:
  piper: fr_FR-siwis-medium (incluse dans voices/)
  edge : fr-CA-SylvieNeural, fr-FR-DeniseNeural, fr-CA-AntoineNeural, etc. (edge-tts --list-voices)
"""
import asyncio
import hashlib
import shutil
import subprocess
from pathlib import Path
from typing import Optional

# ---------- Backend selection ----------
# WB-style env var: TTS_ENGINE=piper (default, local) | TTS_ENGINE=edge
DEFAULT_ENGINE = "piper"

# piper
PIPER_MODEL = str(Path(__file__).parent / "voices" / "fr_FR-siwis-medium.onnx")
PIPER_BIN = shutil.which("piper") or str(Path(__file__).parent / "venv" / "bin" / "piper")

# edge-tts
DEFAULT_VOICE = "fr-CA-SylvieNeural"
RATE = "+0%"
PITCH = "+0Hz"


def get_engine(voice: Optional[str] = None) -> str:
    """Détermine le backend: la voix edge-* → edge, sinon piper."""
    engine_env = __import__("os").environ.get("TTS_ENGINE", "").lower()
    if engine_env in ("piper", "edge"):
        return engine_env
    if voice and voice.startswith(("fr-", "en-")) and "Neural" in voice:
        return "edge"
    return DEFAULT_ENGINE


# ---------- piper (local) ----------
def _piper_synthesize(text: str, output_path: str) -> str:
    """Synthèse 100% locale via piper. Texte jamais envoyé sur le réseau."""
    if not Path(PIPER_MODEL).exists():
        raise FileNotFoundError(
            f"Modèle piper introuvable: {PIPER_MODEL}\n"
            "Télécharge: https://huggingface.co/rhasspy/piper-voices/tree/main/fr/fr_FR/siwis/medium\n"
            "(ou bascule sur --voice fr-CA-SylvieNeural pour le backend edge)"
        )
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    # piper sort du WAV; l'extension demandée (souvent .mp3) est remplacée par .wav
    wav_path = output_path.rsplit(".", 1)[0] + ".wav"
    proc = subprocess.run(
        [PIPER_BIN, "-m", PIPER_MODEL, "-f", wav_path],
        input=text.encode("utf-8"),
        capture_output=True,
        timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"piper failed: {proc.stderr.decode()[:200]}")
    # le pipeline s'attend au path d'origine: si .mp3 demandé, on convertit le WAV → MP3 avec ffmpeg si dispo, sinon on garde le .wav pis on renomme le path attendu
    if wav_path != output_path:
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            conv = subprocess.run([ffmpeg, "-y", "-i", wav_path, output_path],
                                  capture_output=True, timeout=60)
            if conv.returncode == 0:
                Path(wav_path).unlink(missing_ok=True)
                return output_path
        # pas de ffmpeg: on renvoie le .wav (le player web le lit très bien)
        return wav_path
    return output_path


# ---------- edge-tts (distant) ----------
async def _synthesize(text: str, output_path: str, voice: str = DEFAULT_VOICE,
                      rate: str = RATE, pitch: str = PITCH) -> None:
    """Génère un fichier MP3 via edge-tts (Microsoft Azure — texte envoyé à Microsoft)."""
    import edge_tts
    communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(output_path)


def synthesize(text: str, output_path: str, voice: str = DEFAULT_VOICE,
               engine: Optional[str] = None) -> str:
    """
    Route vers le bon backend. Retourne le path de l'audio généré.
    engine: 'piper' (local) ou 'edge' (Microsoft). Défaut: auto-détecté par la voix.
    """
    engine = engine or get_engine(voice)
    if engine == "piper":
        return _piper_synthesize(text, output_path)
    # edge
    if shutil.which("python3") is None:
        raise RuntimeError("python3 introuvable pour edge-tts")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(_synthesize(text, output_path, voice))
    return output_path


def voice_id(voice: str = DEFAULT_VOICE) -> str:
    """ID unique pour la voix (utilisé pour le cache key) — inclut le backend."""
    return f"{get_engine(voice)}:{voice}"


def text_hash(text: str) -> str:
    """Hash du texte pour invalider le cache si le texte change."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def list_voices_sync() -> list:
    """Liste les voix edge disponibles (sync wrapper)."""
    import edge_tts
    async def _list():
        voices = await edge_tts.list_voices()
        return voices
    return asyncio.run(_list())


def filter_voices(voices: list, lang: str = "fr") -> list:
    """Filtre les voix par langue."""
    return [v for v in voices if v.get("Locale", "").startswith(lang)]


def local_voices() -> list:
    """Voix piper disponibles dans voices/."""
    vdir = Path(__file__).parent / "voices"
    return [p.stem for p in vdir.glob("*.onnx")] if vdir.exists() else []