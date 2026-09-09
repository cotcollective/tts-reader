# TTS Reader

Lecteur de documents avec synthèse vocale — webapp Flask locale qui transforme n'importe quel texte (PDF, EPUB, TXT, MD) en audio avec des voix neurales gratuites (Microsoft Edge TTS).

## Features

- **Formats supportés**: PDF, EPUB, TXT, Markdown (extraction texte propre)
- **Voix neurales Edge TTS** (gratuites, Microsoft Azure): fr-CA-SylvieNeural par défaut, fr-FR-DeniseNeural, fr-CA-AntoineNeural, et toutes les voix edge-tts
- **Chunking intelligent**: découpage par phrases/groupes, lecture continue
- **Bookmarks**: reprend où tu as laissé (par fichier, persistant)
- **Cache audio**: les chunks déjà synthétisés ne sont jamais régénérés
- **Web UI dark**: player complet (play/pause, chunk précédent/suivant, slider, texte affiché en synchro)
- **100% local**: aucun compte, aucune clé API — edge-tts utilise le service public gratuit

## Install

```bash
pip install -r requirements.txt
```

## Usage

### Web UI (recommandé)

```bash
python3 app.py
# → http://localhost:5000
```

Ou le launcher (ouvre le browser automatiquement):

```bash
./start_tts_reader.sh
```

### CLI

```bash
python3 cli.py <fichier> [--voice fr-CA-SylvieNeural] [--out ./audio]
```

## Voix

Lister toutes les voix disponibles:

```bash
edge-tts --list-voices
```

Défaut: `fr-CA-SylvieNeural` (français canadien, féminin, naturel).

## Architecture

```
tts_reader/
├── app.py          # Webapp Flask (API + UI inline)
├── pipeline.py     # Orchestration: parse → chunk → synthesize
├── parser.py       # Extraction texte (PDF/EPUB/TXT/MD)
├── chunker.py      # Découpage intelligent par phrases
├── tts_engine.py   # edge-tts wrapper (synthèse, voix, rate, pitch)
├── cache.py        # Cache audio + bookmarks persistants
├── player.py       # Gestion des chunks audio
├── cli.py          # Interface ligne de commande
└── cache/          # MP3s générés + bookmarks (auto-créé)
```

## Dépendances

- Python 3.10+
- `edge-tts` — synthèse vocale Microsoft (gratuit, sans clé)
- `flask` — webapp
- `pypdf` / `ebooklib` — extraction PDF/EPUB

## Note OPSEC

L'outil envoie le texte à synthétiser aux serveurs Microsoft Edge TTS (service public gratuit). Pour des documents sensibles, utiliser un moteur TTS 100% local (piper, Coqui) à la place.

## License

MIT