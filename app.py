#!/usr/bin/env python3
"""Webapp Flask pour TTS reader."""
import sys, json, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from flask import Flask, request, jsonify, Response, send_file
from pipeline import prepare_audio
from cache import get_bookmark, set_bookmark
from tts_engine import DEFAULT_VOICE
app = Flask(__name__)
STATE = {"file_path": None, "chunks_audio": [], "chunks_text": [], "title": "", "meta": {}, "voice": DEFAULT_VOICE}

INDEX_HTML = '<!DOCTYPE html>\n<html lang="fr">\n<head>\n<meta charset="UTF-8">\n<title>TTS Reader</title>\n<style>\n* { box-sizing: border-box; }\nbody { background: #0a0a0a; color: #e0e0e0; font-family: \'Segoe UI\', sans-serif; margin: 0; padding: 20px; }\n.container { max-width: 900px; margin: 0 auto; }\nh1 { color: #00ff9d; font-weight: 300; letter-spacing: 2px; margin: 0 0 20px; }\n.panel { background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 20px; margin-bottom: 20px; }\n.row { display: flex; gap: 10px; margin: 10px 0; align-items: center; }\ninput[type="text"] { flex: 1; background: #0a0a0a; border: 1px solid #333; color: #e0e0e0; padding: 10px; border-radius: 4px; font-family: monospace; }\nbutton { background: #00ff9d; color: #0a0a0a; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: bold; }\nbutton:hover { background: #00cc7d; }\nbutton:disabled { background: #333; color: #666; cursor: not-allowed; }\nbutton.secondary { background: #333; color: #e0e0e0; }\nbutton.secondary:hover { background: #444; }\n.player-controls { display: flex; gap: 10px; justify-content: center; align-items: center; flex-wrap: wrap; }\n.player-controls button { min-width: 80px; font-size: 14px; }\n.status { color: #888; font-family: monospace; font-size: 14px; }\n.chunk-text { background: #0a0a0a; border: 1px solid #333; border-radius: 4px; padding: 15px; max-height: 300px; overflow-y: auto; line-height: 1.6; white-space: pre-wrap; font-size: 15px; }\n.meta { color: #666; font-size: 13px; font-family: monospace; }\naudio { width: 100%; margin: 15px 0; }\n.slider-row { display: flex; align-items: center; gap: 10px; }\n.slider-row input[type="range"] { flex: 1; }\n#chunkLabel { min-width: 80px; text-align: right; font-family: monospace; }\n</style>\n</head>\n<body>\n<div class="container">\n<h1>TTS READER</h1>\n<div class="panel">\n<div class="row">\n<input type="text" id="filePath" placeholder="Chemin du fichier..." />\n<button onclick="loadFile()">LOAD</button>\n</div>\n<div class="row">\n<label>Voix:</label>\n<select id="voiceSelect" style="flex:1; background:#0a0a0a; color:#e0e0e0; border:1px solid #333; padding:8px; border-radius:4px;">\n<option value="fr-CA-SylvieNeural">fr-CA-SylvieNeural (QC, feminin)</option>\n<option value="fr-CA-AntoineNeural">fr-CA-AntoineNeural (QC, masculin)</option>\n<option value="fr-FR-DeniseNeural">fr-FR-DeniseNeural (FR, feminin)</option>\n<option value="fr-FR-HenriNeural">fr-FR-HenriNeural (FR, masculin)</option>\n</select>\n</div>\n<div id="loadStatus" class="status"></div>\n</div>\n<div class="panel" id="playerPanel" style="display:none;">\n<div class="meta" id="docMeta"></div>\n<h2 id="docTitle" style="margin: 10px 0; color: #fff;"></h2>\n<audio id="audioPlayer" controls></audio>\n<div class="slider-row" style="margin: 10px 0;">\n<span class="status">Chunk:</span>\n<input type="range" id="chunkSlider" min="0" max="0" value="0" step="1" />\n<span id="chunkLabel">0/0</span>\n</div>\n<div class="player-controls">\n<button class="secondary" onclick="playerAction(\'prev\')">Precedent</button>\n<button onclick="playerAction(\'play\')" id="playBtn">Play</button>\n<button class="secondary" onclick="playerAction(\'pause\')">Pause</button>\n<button class="secondary" onclick="playerAction(\'next\')">Suivant</button>\n<button class="secondary" onclick="saveBookmark()">Bookmark</button>\n</div>\n</div>\n<div class="panel" id="textPanel" style="display:none;">\n<h3 style="margin: 0 0 10px; color: #888; font-weight: 300;">Texte du chunk courant</h3>\n<div class="chunk-text" id="chunkText"></div>\n</div>\n</div>\n<script>\nconst audio = document.getElementById("audioPlayer");\nconst slider = document.getElementById("chunkSlider");\nconst chunkLabel = document.getElementById("chunkLabel");\nconst chunkTextEl = document.getElementById("chunkText");\nlet totalChunks = 0;\nlet currentChunk = 0;\n\nasync function loadFile() {\n  const filePath = document.getElementById("filePath").value.trim();\n  const voice = document.getElementById("voiceSelect").value;\n  if (!filePath) return;\n  document.getElementById("loadStatus").innerText = "Preparation... (peut prendre 1-2 min pour gros doc)";\n  try {\n    const r = await fetch("/api/load", {\n      method: "POST",\n      headers: { "Content-Type": "application/json" },\n      body: JSON.stringify({ file_path: filePath, voice: voice }),\n    });\n    const data = await r.json();\n    if (data.error) {\n      document.getElementById("loadStatus").innerText = "ERREUR: " + data.error;\n      return;\n    }\n    totalChunks = data.total_chunks;\n    slider.max = Math.max(0, totalChunks - 1);\n    document.getElementById("docTitle").innerText = data.title;\n    document.getElementById("docMeta").innerText =\n      (data.meta.format || "?") + " | " + (data.meta.word_count || "?") + " mots | " + totalChunks + " chunks | voix: " + data.voice +\n      (data.bookmark > 0 ? " | bookmark: chunk " + (data.bookmark + 1) : "");\n    document.getElementById("playerPanel").style.display = "block";\n    document.getElementById("textPanel").style.display = "block";\n    document.getElementById("loadStatus").innerText = "Pret";\n    seekToChunk(data.start_chunk || 0, true);\n  } catch (e) {\n    document.getElementById("loadStatus").innerText = "ERREUR: " + e.message;\n  }\n}\n\nfunction seekToChunk(idx, autoplay) {\n  if (idx < 0 || idx >= totalChunks) return;\n  currentChunk = idx;\n  audio.src = "/audio/" + idx;\n  slider.value = idx;\n  chunkLabel.innerText = (idx + 1) + "/" + totalChunks;\n  if (autoplay) audio.play();\n  fetch("/api/text/" + idx).then(r => r.json()).then(data => {\n    chunkTextEl.innerText = data.text;\n  });\n  fetch("/api/bookmark", {\n    method: "POST",\n    headers: { "Content-Type": "application/json" },\n    body: JSON.stringify({ position: idx }),\n  });\n}\n\nfunction playerAction(action) {\n  if (action === "play") audio.play();\n  else if (action === "pause") audio.pause();\n  else if (action === "next") seekToChunk(currentChunk + 1, true);\n  else if (action === "prev") seekToChunk(currentChunk - 1, true);\n}\n\naudio.addEventListener("ended", () => {\n  if (currentChunk < totalChunks - 1) seekToChunk(currentChunk + 1, true);\n  else { document.getElementById("loadStatus").innerText = "Document termine"; }\n});\n\nslider.addEventListener("input", (e) => {\n  seekToChunk(parseInt(e.target.value));\n});\n\nasync function saveBookmark() {\n  await fetch("/api/bookmark", {\n    method: "POST",\n    headers: { "Content-Type": "application/json" },\n    body: JSON.stringify({ position: currentChunk }),\n  });\n  document.getElementById("loadStatus").innerText = "Bookmark sauvegarde (chunk " + (currentChunk + 1) + ")";\n}\n\ndocument.getElementById("filePath").addEventListener("keydown", (e) => {\n  if (e.key === "Enter") loadFile();\n});\n</script>\n</body>\n</html>'

@app.route("/")
def index():
    return INDEX_HTML

@app.route("/api/load", methods=["POST"])
def api_load():
    data = request.get_json()
    file_path = data.get("file_path", "").strip()
    if not file_path: return jsonify({"error": "file_path required"}), 400
    if not Path(file_path).exists(): return jsonify({"error": "Fichier introuvable: " + file_path}), 404
    voice = data.get("voice", DEFAULT_VOICE)
    try:
        result = prepare_audio(file_path, voice=voice, progress_cb=lambda i,t,m: print("  ["+str(i)+"/"+str(t)+"] "+m, flush=True))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    STATE["file_path"] = file_path
    STATE["chunks_audio"] = result["chunks_audio"]
    STATE["chunks_text"] = result["chunks_text"]
    STATE["title"] = result["title"]
    STATE["meta"] = result["meta"]
    STATE["voice"] = voice
    bookmark = get_bookmark(file_path)
    start_chunk = min(bookmark, len(STATE["chunks_audio"]) - 1) if STATE["chunks_audio"] else 0
    return jsonify({"title": result["title"], "meta": result["meta"], "total_chunks": len(STATE["chunks_audio"]), "bookmark": bookmark, "start_chunk": start_chunk, "voice": voice})

@app.route("/api/state", methods=["GET"])
def api_state():
    return jsonify({"file_path": STATE["file_path"], "title": STATE["title"], "total_chunks": len(STATE["chunks_audio"]), "voice": STATE["voice"]})

@app.route("/api/bookmark", methods=["POST"])
def api_bookmark():
    data = request.get_json()
    position = int(data.get("position", 0))
    if STATE["file_path"]:
        set_bookmark(STATE["file_path"], position)
        return jsonify({"ok": True, "position": position, "file": STATE["file_path"]})
    return jsonify({"error": "no file loaded"}), 400

@app.route("/audio/<int:chunk_idx>", methods=["GET"])
def audio_chunk(chunk_idx):
    if not STATE["chunks_audio"]: return "no file loaded", 404
    if chunk_idx < 0 or chunk_idx >= len(STATE["chunks_audio"]): return "out of range", 404
    return send_file(STATE["chunks_audio"][chunk_idx], mimetype="audio/mpeg", conditional=True)

@app.route("/api/text/<int:chunk_idx>", methods=["GET"])
def api_text(chunk_idx):
    if not STATE["chunks_text"]: return jsonify({"error": "no file loaded"}), 404
    if chunk_idx < 0 or chunk_idx >= len(STATE["chunks_text"]): return jsonify({"error": "out of range"}), 404
    return jsonify({"text": STATE["chunks_text"][chunk_idx], "idx": chunk_idx})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("TTS Reader webapp: http://localhost:" + str(port))
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)