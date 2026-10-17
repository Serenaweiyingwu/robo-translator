"""Thin clients for the three Doubao services: speech recognition, the language model, and speech synthesis."""

import base64
import json
import re
import uuid

import requests

from .config import LANGUAGES, Settings

ASR_URL = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash"
TTS_URL = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
ARK_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

TTS_SAMPLE_RATE = 24000


class DoubaoError(RuntimeError):
    pass


class Doubao:
    def __init__(self, settings: Settings):
        self.s = settings
        self.http = requests.Session()

    def transcribe(self, wav: bytes, lang: str | None) -> str:
        """Speech to text. lang=None lets Doubao auto-detect, which covers Chinese and English only."""
        audio = {"data": base64.b64encode(wav).decode(), "format": "wav"}
        if lang:
            audio["language"] = LANGUAGES[lang].asr
        r = self.http.post(
            ASR_URL,
            headers={
                "X-Api-Key": self.s.speech_api_key,
                "X-Api-Resource-Id": "volc.seedasr.auc",
                "X-Api-Request-Id": str(uuid.uuid4()),
                "X-Api-Sequence": "-1",
            },
            json={"user": {"uid": "robo"}, "audio": audio, "request": {"model_name": "bigmodel"}},
            timeout=20,
        )
        status = r.headers.get("X-Api-Status-Code", "")
        if status == "20000003":  # no speech in the audio
            return ""
        if status != "20000000":
            raise DoubaoError(f"ASR failed {status} {r.headers.get('X-Api-Message')} logid={r.headers.get('X-Tt-Logid')}")
        return r.json().get("result", {}).get("text", "").strip()

    def chat_json(self, system: str, user: str) -> dict:
        """Ask the language model for a JSON object."""
        r = self.http.post(
            ARK_URL,
            headers={"Authorization": f"Bearer {self.s.ark_api_key}"},
            json={
                "model": self.s.llm_model,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "thinking": {"type": "disabled"},  # translation doesn't need reasoning; keeps latency low
                "temperature": 0.2,
            },
            timeout=20,
        )
        if r.status_code != 200:
            raise DoubaoError(f"LLM failed {r.status_code}: {r.text[:300]}")
        text = r.json()["choices"][0]["message"]["content"]
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            raise DoubaoError(f"LLM returned no JSON: {text[:300]}")
        return json.loads(match.group(0))

    def speak(self, text: str, lang: str) -> bytes:
        """Text to speech. Returns 16-bit mono PCM at TTS_SAMPLE_RATE."""
        r = self.http.post(
            TTS_URL,
            headers={
                "X-Api-Key": self.s.speech_api_key,
                "X-Api-Resource-Id": "seed-tts-2.0",
                "X-Api-Request-Id": str(uuid.uuid4()),
            },
            json={
                "req_params": {
                    "text": text,
                    "speaker": self.s.tts_voices.get(lang, self.s.tts_voice),
                    "audio_params": {"format": "pcm", "sample_rate": TTS_SAMPLE_RATE},
                    "additions": json.dumps({"explicit_language": LANGUAGES[lang].tts}),
                }
            },
            stream=True,
            timeout=30,
        )
        if r.status_code != 200:
            raise DoubaoError(f"TTS failed {r.status_code}: {r.text[:300]}")
        pcm = bytearray()
        for line in r.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            if chunk.get("code", 0) not in (0, 20000000):
                raise DoubaoError(f"TTS failed {chunk.get('code')}: {chunk.get('message')}")
            if chunk.get("data"):
                pcm += base64.b64decode(chunk["data"])
        return bytes(pcm)
