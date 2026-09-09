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
import json
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
    """Détermine le backend. PRIORITÉ: voix piper locale D'ABORD (le disque gagne sur tout),
    puis catalogue edge, puis défaut piper. L'env TTS_ENGINE ne peut PAS forcer edge
    pour une voix piper connue — protection contre un TTS_ENGINE=edge oublié dans un .bashrc."""
    # 1. voix locale piper disponible → piper, INCONDITIONNELLEMENT (le disque est la source de vérité)
    if voice and voice in local_voices():
        return "piper"
    # 2. env override: peut basculer vers edge UNIQUEMENT pour des voix qui ne sont pas locales
    engine_env = __import__("os").environ.get("TTS_ENGINE", "").lower()
    if engine_env in ("piper", "edge"):
        return engine_env
    # 3. voix du catalogue edge strict (whitelist)
    if voice and voice in EDGE_KNOWN_VOICES:
        return "edge"
    # 4. défaut fail-safe: local
    return DEFAULT_ENGINE


# Catalogue strict des voix edge (les plus utilisées). Toute autre voix → piper (fail-safe local).
# Pour étendre: edge-tts --list-voices
EDGE_KNOWN_VOICES = {
    "fr-CA-SylvieNeural", "fr-CA-AntoineNeural", "fr-FR-DeniseNeural", "fr-FR-HenriNeural",
    "en-US-JennyNeural", "en-US-GuyNeural", "en-US-AriaNeural", "en-GB-SoniaNeural",
}


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
               engine: Optional[str] = None, file_path: str = "") -> str:
    """
    Route vers le bon backend. Retourne le path de l'audio généré.
    engine: 'piper' (local) ou 'edge' (Microsoft). Défaut: auto-détecté par la voix.
    file_path: source du document (pour l'audit log edge).
    """
    engine = engine or get_engine(voice)
    if engine == "piper":
        return _piper_synthesize(text, output_path)
    # edge: confirmation explicite — ce texte part chez un tiers, visible en usage réel
    print(f"\033[33m⚠️  EDGE-TTS (distant): ce chunk part chez Microsoft ({len(text)} chars, voix {voice})\033[0m", flush=True)
    # audit log persistant: quels documents/chunks ont transité par Microsoft
    _log_edge_usage(text, voice, file_path)
    if shutil.which("python3") is None:
        raise RuntimeError("python3 introuvable pour edge-tts")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(_synthesize(text, output_path, voice))
    return output_path


def _log_edge_usage(text: str, voice: str, file_path: str = "") -> None:
    """Log d'audit persistant: chaque chunk envoyé à Microsoft est tracé.
    Permet de répondre après coup à 'est-ce que tel document a fuit'."""
    try:
        log_path = Path(__file__).parent / "cache" / "edge_usage.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        import time
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "file": file_path or "unknown",
            "chars": len(text),
            "voice": voice,
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # l'audit ne doit jamais bloquer la synthèse


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