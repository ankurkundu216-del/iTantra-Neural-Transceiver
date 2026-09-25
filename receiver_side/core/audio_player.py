"""
Priority Audio Player
Manages low-latency PCM playback and handles emergency distress overrides.
"""

import threading
import queue
import time
import numpy as np

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False


class AudioPlayer:
    def __init__(self, default_sample_rate: int = 22050):
        self.default_sample_rate = default_sample_rate
        self.audio_queue = queue.Queue()
        self.is_playing = False
        self.playback_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._worker_thread = None

    def play(self, audio_data: np.ndarray, sample_rate: int = 22050, is_distress: bool = False) -> None:
        """
        Enqueues audio for playback. If is_distress is True, interrupts active audio immediately.
        """
        if is_distress:
            print("🚨 [Audio Player] DISTRESS FLAG DETECTED! Overriding audio queue and playing emergency note.")
            self._emergency_override(audio_data, sample_rate)
        else:
            self.audio_queue.put((audio_data, sample_rate))
            if not self.is_playing:
                self._start_worker()

    def _emergency_override(self, audio_data: np.ndarray, sample_rate: int) -> None:
        """Clears normal playback queue, stops active output, and forces playback."""
        with self.playback_lock:
            # Drain non-emergency queue
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    break

            if SOUNDDEVICE_AVAILABLE:
                sd.stop()  # Halt active speaker stream immediately

            # Play high-volume emergency audio synchronously on priority thread
            self._execute_playback(audio_data * 1.5, sample_rate, is_distress=True)

    def _execute_playback(self, audio_data: np.ndarray, sample_rate: int, is_distress: bool = False) -> None:
        if len(audio_data) == 0:
            return

        # Clip values to prevent digital clipping / distortion
        audio_data = np.clip(audio_data, -1.0, 1.0)

        if SOUNDDEVICE_AVAILABLE:
            try:
                sd.play(audio_data, samplerate=sample_rate)
                sd.wait()  # Wait until audio clip finishes playing
            except Exception as e:
                print(f"[Audio Player] Playback error: {e}")
        else:
            duration = len(audio_data) / sample_rate
            prefix = "🚨 [DISTRESS PLAYBACK]" if is_distress else "🔊 [NORMAL PLAYBACK]"
            print(f"{prefix} Mock playing {duration:.2f} seconds of audio...")
            time.sleep(duration)

    def _worker_loop(self) -> None:
        self.is_playing = True
        while not self._stop_event.is_set():
            try:
                audio_data, sample_rate = self.audio_queue.get(timeout=0.5)
                with self.playback_lock:
                    self._execute_playback(audio_data, sample_rate)
                self.audio_queue.task_done()
            except queue.Empty:
                if self.audio_queue.empty():
                    break
        self.is_playing = False

    def _start_worker(self) -> None:
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._stop_event.clear()
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker_thread.start()

    def stop(self) -> None:
        """Stops all active audio and shuts down worker thread."""
        self._stop_event.set()
        if SOUNDDEVICE_AVAILABLE:
            sd.stop()


if __name__ == "__main__":
    player = AudioPlayer()
    
    # Test normal tone
    t = np.linspace(0, 1.0, 22050, False)
    normal_wave = (0.2 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    distress_wave = (0.5 * np.sin(2 * np.pi * 880 * t)).astype(np.float32)

    print("[Test Audio Player] Testing normal playback...")
    player.play(normal_wave, 22050, is_distress=False)
    time.sleep(0.5)

    print("[Test Audio Player] Testing emergency override...")
    player.play(distress_wave, 22050, is_distress=True)