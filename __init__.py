#!/usr/bin/env python3
"""
TTS Reader — Lecteur TTS local pour MD/TXT/PDF.

Architecture:
  - parser.py: extraction texte depuis .md / .txt / .pdf
  - chunker.py: découpage seamless (sentence boundary) pour gros documents
  - tts_engine.py: génération audio via edge-tts (voix Azure neural)
  - player.py: lecture audio avec pygame (pause/play/skip/rewind)
  - cache.py: cache lazy des chunks audio + bookmark position par fichier
  - cli.py: interface terminal (pré-UI web)
  - app.py: interface web Flask (drag-drop, slider, boutons)

Usage:
  python3 cli.py <fichier>           # CLI standalone
  python3 app.py                     # webapp localhost:5000
"""

__version__ = "0.1.0"
