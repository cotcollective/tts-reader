# TTS Reader

Lecteur de documents avec synthèse vocale — webapp Flask locale qui transforme n'importe quel texte (PDF, EPUB, TXT, MD) en audio.

## ⚠️ Deux backends: local vs distant — lis ceci avant de choisir

| Backend | Qualité | Où va ton texte | Clé API | Modèle |
|---|---|---|---|---|
| **piper** (défaut) | Très bonne | **Nulle part — 100% local, offline** | aucune | `fr_FR-siwis-medium` (incluse) |
| **edge** | Excellente (neurale) | **Chez Microsoft** (`speech.platform.bing.com`), en clair | aucune | fr-CA-SylvieNeural + 300 voix |

**Important**: le package `edge-tts` n'est PAS local. Il fait du reverse-engineering de l'API "Read Aloud" de Microsoft Edge — ton texte part en HTTPS vers les serveurs Azure à chaque chunk. "Sans clé API" ≠ "local". Pour des documents sensibles (contrats, dossiers médicaux, notes privées), utilise **piper** — le texte ne quitte jamais ta machine.

## Features

- **Formats supportés**: PDF, EPUB, TXT, Markdown (extraction texte propre)
- **Dual backend**: piper (local, privé) ou edge-tts (neurale, distant) — auto-détecté par la voix, overridable
- **Chunking intelligent**: découpage par phrases/groupes, lecture continue
- **Bookmarks**: reprend où tu as laissé (par fichier, persistant)
- **Cache audio**: les chunks déjà synthétisés ne sont jamais régénérés (key = hash texte + voix + backend)
- **Web UI dark**: player complet (play/pause, chunk précédent/suivant, slider, texte affiché en synchro)
- **100% offline possible**: avec piper, zéro appel réseau après install

## Install

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

### Voix piper (incluse)

Le modèle `fr_FR-siwis-medium` (~63MB) vit dans `voices/`. Si absent:

```bash
cd voices/
curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx
curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx.json
```

Autres langues/voix piper: https://huggingface.co/rhasspy/piper-voices/tree/main

### ffmpeg (optionnel)

Piper sort du WAV; si `ffmpeg` est installé, les chunks sont convertis en MP3 automatiquement. Sans ffmpeg, le player lit le WAV tel quel.

## Usage

### Web UI (recommandé)

```bash
./venv/bin/python app.py
# → http://localhost:5000
```

Dans l'UI: choix du backend au chargement du fichier (`engine: "piper"` ou `"edge"`), ou auto (voix `*Neural` → edge, sinon piper).

### CLI

```bash
python3 cli.py <fichier> [--voice fr_FR-siwis-medium] [--out ./audio]
```

### Variable d'environnement

```bash
TTS_ENGINE=piper python3 app.py   # force local (défaut)
TTS_ENGINE=edge python3 app.py    # force Microsoft
```

## Voix

| Backend | Défaut | Autres |
|---|---|---|
| piper (local) | `fr_FR-siwis-medium` | toutes les voix Piper HF (fr_FR-siwis, fr_FR-tom, en_US-amy...) |
| edge (distant) | `fr-CA-SylvieNeural` | `edge-tts --list-voices` (300+ voix neurales) |

Règle d'auto-détection: une voix contenant "Neural" → backend edge; toute autre voix (ou nom de modèle piper) → backend local.

## Architecture

```
tts_reader/
├── app.py          # Webapp Flask (API + UI inline)
├── pipeline.py     # Orchestration: parse → chunk → synthesize (backend routing)
├── parser.py       # Extraction texte (PDF/EPUB/TXT/MD)
├── chunker.py      # Découpage intelligent par phrases
├── tts_engine.py   # DUAL BACKEND: piper (local) | edge-tts (Microsoft)
├── cache.py        # Cache audio + bookmarks persistants
├── player.py       # Gestion des chunks audio
├── cli.py          # Interface ligne de commande
├── voices/         # Modèles piper (.onnx) — fr_FR-siwis inclus
├── venv/           # Python env (piper-tts, flask, edge-tts...)
└── cache/          # MP3s/WAVs générés + bookmarks (auto-créé)
```

## Dépendances

- Python 3.10+
- `piper-tts` — synthèse 100% locale (modèle ONNX, CPU suffit)
- `edge-tts` — backend Microsoft Azure (optionnel, gratuit sans clé)
- `flask` — webapp
- `pypdf` / `ebooklib` / `beautifulsoup4` — extraction PDF/EPUB/HTML
- `ffmpeg` (optionnel) — conversion WAV→MP3 pour piper

## Privacy

- **piper**: rien ne quitte ta machine. Le modèle ONNX tourne en local, sur CPU.
- **edge-tts**: le texte des chunks est envoyé en clair à Microsoft. Ne PAS utiliser pour du contenu sensible.
- Le cache audio local (`.tts_reader_cache/`) contient le texte sous forme audio — le traiter comme un document sensé.

## License

MIT