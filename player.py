#!/usr/bin/env python3
"""Player: lecteur audio avec pygame, support pause/play/skip/rewind."""
import threading
import time
from pathlib import Path
from typing import Callable, Optional

try:
    import pygame
    pygame.mixer.init()
    PYGAME_OK = True
except Exception as e:
    PYGAME_OK = False
    INIT_ERROR = str(e)


class TTSPlayer:
    def __init__(self, on_chunk_change=None, on_finished=None):
        if not PYGAME_OK:
            raise RuntimeError(f"pygame.mixer init failed: {INIT_ERROR}")
        self.chunks = []
        self.chunk_idx = 0
        self.paused = False
        self.stopped = False
        self.lock = threading.Lock()
        self.on_chunk_change = on_chunk_change
        self.on_finished = on_finished
        self.play_thread = None

    def load(self, audio_paths):
        with self.lock:
            self.chunks = list(audio_paths)
            self.chunk_idx = 0
            self.paused = False
            self.stopped = False

    def play(self):
        if self.play_thread and self.play_thread.is_alive():
            self.resume()
            return
        self.stopped = False
        self.paused = False
        self.play_thread = threading.Thread(target=self._play_loop, daemon=True)
        self.play_thread.start()

    def pause(self):
        with self.lock:
            if not self.paused:
                self.paused = True
                pygame.mixer.music.pause()

    def resume(self):
        with self.lock:
            if self.paused:
                self.paused = False
                pygame.mixer.music.unpause()

    def stop(self):
        with self.lock:
            self.stopped = True
            self.paused = False
            pygame.mixer.music.stop()

    def skip_next(self):
        with self.lock:
            if self.chunk_idx + 1 < len(self.chunks):
                self.chunk_idx += 1
                pygame.mixer.music.stop()

    def skip_prev(self):
        with self.lock:
            if self.chunk_idx > 0:
                self.chunk_idx -= 1
                pygame.mixer.music.stop()

    def seek_to_chunk(self, idx):
        with self.lock:
            if 0 <= idx < len(self.chunks):
                self.chunk_idx = idx
                pygame.mixer.music.stop()

    def get_state(self):
        with self.lock:
            return {
                "chunk_idx": self.chunk_idx,
                "total_chunks": len(self.chunks),
                "paused": self.paused,
                "stopped": self.stopped,
            }

    def _play_loop(self):
        while not self.stopped:
            with self.lock:
                if self.chunk_idx >= len(self.chunks):
                    break
                chunk_path = self.chunks[self.chunk_idx]
            try:
                pygame.mixer.music.load(str(chunk_path))
            except Exception as e:
                print(f"[player] Erreur load chunk {self.chunk_idx}: {e}")
                with self.lock:
                    self.chunk_idx += 1
                continue
            if self.on_chunk_change:
                self.on_chunk_change(self.chunk_idx, len(self.chunks))
            with self.lock:
                self.paused = False
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy() or self.paused:
                if self.stopped:
                    pygame.mixer.music.stop()
                    return
                time.sleep(0.1)
            with self.lock:
                if not self.stopped:
                    self.chunk_idx += 1
        if self.on_finished:
            self.on_finished()
