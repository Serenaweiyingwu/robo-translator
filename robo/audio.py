"""Microphone recording with simple voice-activity detection, and speaker playback."""

import io
import wave

import numpy as np
import sounddevice as sd

MIC_RATE = 16000  # what Doubao speech recognition expects
BLOCK = 1600  # 100 ms


def _rms(block: np.ndarray) -> float:
    return float(np.sqrt(np.mean(block.astype(np.float32) ** 2)))


class Mic:
    def __init__(self, silence_s: float = 0.8, max_s: float = 15.0, sensitivity: float = 3.0):
        self.silence_blocks = int(silence_s * 10)
        self.max_blocks = int(max_s * 10)
        self.sensitivity = sensitivity
        self.floor = None

    def calibrate(self, seconds: float = 1.0) -> None:
        """Measure room noise so speech can be told apart from it."""
        audio = sd.rec(int(seconds * MIC_RATE), samplerate=MIC_RATE, channels=1, dtype="int16")
        sd.wait()
        self.floor = max(_rms(audio), 50.0)

    def listen(self) -> bytes:
        """Block until someone speaks, then return the utterance as WAV bytes."""
        if self.floor is None:
            self.calibrate()
        threshold = self.floor * self.sensitivity
        frames, quiet, started = [], 0, False
        with sd.InputStream(samplerate=MIC_RATE, channels=1, dtype="int16", blocksize=BLOCK) as stream:
            while True:
                block, _ = stream.read(BLOCK)
                loud = _rms(block) > threshold
                if not started:
                    frames = (frames + [block])[-3:]  # keep 300 ms before speech starts
                    started = loud
                    continue
                frames.append(block)
                quiet = 0 if loud else quiet + 1
                if quiet >= self.silence_blocks or len(frames) >= self.max_blocks:
                    break
        return to_wav(np.concatenate(frames).tobytes(), MIC_RATE)


def to_wav(pcm: bytes, rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


def play(pcm: bytes, rate: int) -> None:
    sd.play(np.frombuffer(pcm, dtype=np.int16), samplerate=rate)
    sd.wait()
