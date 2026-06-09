"""Bell sound generator — stdlib only, macOS/Linux/Windows portable."""
import array
import math
import os
import subprocess
import sys
import tempfile
import threading
import wave


def _generate_bell_wav(path: str, volume: float) -> None:
    """Write a short bell-like chime to a WAV file (stdlib only)."""
    sample_rate = 44100
    duration = 0.35       # seconds
    freq1 = 880.0         # A5 — bright, bell-like
    freq2 = 1320.0        # E6 — overtone

    n = int(sample_rate * duration)
    samples = array.array("h")  # signed short
    peak = int(32767 * max(0.0, min(1.0, volume)))

    for i in range(n):
        t = i / sample_rate
        envelope = math.exp(-6 * t / duration)
        value = envelope * (
            0.7 * math.sin(2 * math.pi * freq1 * t) +
            0.3 * math.sin(2 * math.pi * freq2 * t)
        )
        samples.append(int(value * peak))

    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(samples.tobytes())


def _play_wav(path: str) -> None:
    if sys.platform == "darwin":
        subprocess.Popen(["afplay", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif sys.platform.startswith("linux"):
        for player in ("aplay", "paplay", "ffplay"):
            if os.path.exists(f"/usr/bin/{player}") or os.path.exists(f"/usr/local/bin/{player}"):
                subprocess.Popen([player, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                break
    elif sys.platform == "win32":
        import winsound  # noqa: PLC0415
        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)


def play_bell(volume_pct: int = 70) -> None:
    """Play a bell chime asynchronously. volume_pct: 0–100."""
    volume = max(0, min(100, volume_pct)) / 100.0

    def _run():
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_path = tmp.name
        tmp.close()
        try:
            _generate_bell_wav(tmp_path, volume)
            _play_wav(tmp_path)
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()
