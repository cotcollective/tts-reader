#!/usr/bin/env python3
"""CLI: interface terminal pour tester le TTS reader."""
import sys
import time
import select
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pipeline import prepare_audio
from player import TTSPlayer
from cache import get_bookmark, set_bookmark
from tts_engine import DEFAULT_VOICE, list_voices_sync, filter_voices


def list_voices():
    voices = list_voices_sync()
    fr_voices = filter_voices(voices, "fr")
    print(f"\n{len(fr_voices)} voix francaises:\n")
    for v in fr_voices:
        print(f"  {v.get('ShortName'):<30}  {v.get('Gender')}  {v.get('FriendlyName')}")
    print()


def main():
    args = sys.argv[1:]
    if "--list-voices" in args:
        list_voices()
        return
    if not args:
        print("Usage: python3 cli.py <fichier>")
        print("       python3 cli.py --list-voices")
        sys.exit(1)

    voice = DEFAULT_VOICE
    if "--voice" in args:
        idx = args.index("--voice")
        voice = args[idx + 1]
        args = args[:idx] + args[idx+2:]

    file_path = args[0]
    if not Path(file_path).exists():
        print(f"Fichier introuvable: {file_path}")
        sys.exit(1)

    print(f"\nFichier: {Path(file_path).name}")
    print(f"Voix: {voice}")
    print("Preparation...\n")

    def progress_cb(i, total, msg):
        print(f"  [{i}/{total}] {msg}", end="\r", flush=True)

    result = prepare_audio(file_path, voice=voice, progress_cb=progress_cb)
    print(f"\nOK: {len(result['chunks_audio'])} chunks prets")
    print(f"Titre: {result['title']}")
    print(f"Stats: {result['meta'].get('word_count', '?')} mots\n")

    bookmark_pos = get_bookmark(file_path)
    start_idx = bookmark_pos if bookmark_pos < len(result['chunks_audio']) else 0
    if bookmark_pos > 0:
        print(f"Reprise au chunk {bookmark_pos + 1}/{len(result['chunks_audio'])}")

    player = TTSPlayer(
        on_chunk_change=lambda i, total: print(f"\rChunk {i+1}/{total}", end="", flush=True),
    )
    player.load(result['chunks_audio'])
    player.chunk_idx = start_idx
    player.play()

    print("\n\n[p]ause [r]esume [n]ext [b]ack [q]uit [s N]eek\n")

    def read_kbd():
        if select.select([sys.stdin], [], [], 0.0)[0]:
            return sys.stdin.readline().strip()
        return None

    last_save = time.time()
    try:
        while True:
            cmd = read_kbd()
            if cmd:
                if cmd == "p":
                    player.pause()
                    print("Pause")
                elif cmd == "r":
                    player.resume()
                    print("Resume")
                elif cmd == "n":
                    player.skip_next()
                elif cmd == "b":
                    player.skip_prev()
                elif cmd == "q":
                    player.stop()
                    break
                elif cmd.startswith("s "):
                    try:
                        n = int(cmd.split()[1])
                        player.seek_to_chunk(n)
                    except (ValueError, IndexError):
                        print("Usage: s <numero>")

            if time.time() - last_save > 5:
                state = player.get_state()
                set_bookmark(file_path, state["chunk_idx"])
                last_save = time.time()

            time.sleep(0.2)

            if not player.play_thread.is_alive() and not player.paused:
                break
    except KeyboardInterrupt:
        player.stop()

    state = player.get_state()
    set_bookmark(file_path, state["chunk_idx"])
    print(f"\nBookmark: chunk {state['chunk_idx'] + 1}/{len(result['chunks_audio'])}")
    print("Bye")


if __name__ == "__main__":
    main()
