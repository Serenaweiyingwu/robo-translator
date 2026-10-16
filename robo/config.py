"""Settings and the language table shared by speech recognition and speech synthesis."""

import os
from dataclasses import dataclass


def _load_dotenv(path: str = ".env") -> None:
    """Read KEY=VALUE lines from .env without overriding real environment variables."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Language:
    code: str  # short code used everywhere in this project
    name: str
    asr: str  # Doubao speech recognition `audio.language` value
    tts: str  # Doubao speech synthesis `explicit_language` value


# Languages supported by both Doubao speech recognition and speech synthesis.
LANGUAGES = {
    lang.code: lang
    for lang in [
        Language("en", "English", "en-US", "en"),
        Language("zh", "Chinese", "zh-CN", "zh-cn"),
        Language("de", "German", "de-DE", "de"),
        Language("fr", "French", "fr-FR", "fr"),
        Language("es", "Spanish", "es-MX", "es-mx"),
        Language("pt", "Portuguese", "pt-BR", "pt-br"),
        Language("it", "Italian", "it-IT", "it"),
        Language("ja", "Japanese", "ja-JP", "ja"),
        Language("ko", "Korean", "ko-KR", "ko"),
        Language("ru", "Russian", "ru-RU", "ru"),
        Language("ar", "Arabic", "ar-SA", "ar"),
        Language("th", "Thai", "th-TH", "th"),
        Language("vi", "Vietnamese", "vi-VN", "vi"),
        Language("id", "Indonesian", "id-ID", "id"),
        Language("ms", "Malay", "ms-MY", "ms"),
        Language("tr", "Turkish", "tr-TR", "tr"),
        Language("pl", "Polish", "pl-PL", "pl"),
        Language("nl", "Dutch", "nl-NL", "nl"),
        Language("uk", "Ukrainian", "uk-UA", "uk"),
        Language("ro", "Romanian", "ro-RO", "ro"),
        Language("el", "Greek", "el-GR", "el"),
    ]
}


@dataclass
class Settings:
    speech_api_key: str
    ark_api_key: str
    llm_model: str
    tts_voice: str
    tts_voices: dict  # per-language voice overrides, e.g. {"de": "..."}


def load_settings() -> Settings:
    _load_dotenv()
    voices = {
        code: os.environ[f"TTS_VOICE_{code.upper()}"]
        for code in LANGUAGES
        if os.environ.get(f"TTS_VOICE_{code.upper()}")
    }
    return Settings(
        speech_api_key=os.environ.get("VOLC_SPEECH_API_KEY", ""),
        ark_api_key=os.environ.get("ARK_API_KEY", ""),
        llm_model=os.environ.get("DOUBAO_MODEL", "doubao-seed-1-6-flash-250828"),
        tts_voice=os.environ.get("TTS_VOICE", "zh_female_vv_uranus_bigtts"),
        tts_voices=voices,
    )
