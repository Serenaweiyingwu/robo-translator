"""The translator agent: wait for "Robo, ...", set up a language pair, then translate both ways."""

import json
import re
from concurrent.futures import ThreadPoolExecutor

from .config import LANGUAGES
from .doubao import TTS_SAMPLE_RATE
from .robot import Robot

# Speech recognition often hears "Robo" as one of these in Chinese.
WAKE = re.compile(r"^\W*(hey\W+|ok\W+)?(robo|robot|罗博|萝卜|罗波|肉包)", re.I)

LANG_LIST = ", ".join(f"{l.code}={l.name}" for l in LANGUAGES.values())

COMMAND_PROMPT = f"""You control Robo, a translator robot. The owner just said something addressed to Robo.
Supported languages: {LANG_LIST}.
Current session: {{session}}.
Return one JSON object:
{{{{"action": "start" | "stop" | "switch" | "repeat" | "none",
  "source": owner's language code (start only; if not stated, the language the owner is speaking now),
  "target": the other person's language code (start/switch),
  "confirm": a very short confirmation to the owner, in the owner's language,
  "greeting": for start/switch only: one short friendly sentence in the target language telling the other person you will translate for them}}}}
"start" = begin translating; "switch" = change the other person's language; "stop" = end; "repeat" = say the last translation again;
"none" = this was not a command (e.g. the owner just mentioned a robot in conversation).
If the requested language is not supported, use action "none" and say so in "confirm"."""

TRANSLATE_PROMPT = """You are a live interpreter between {src_name} ("{src}") and {tgt_name} ("{tgt}").
You get speech-recognition transcripts of ONE utterance, possibly decoded once per language; only the coherent
one is real. Work out which language was actually spoken, then translate it into the other one.
Fix obvious recognition errors. Keep the tone; be natural and brief, the way a human interpreter would speak.
Return one JSON object: {{"spoken": "{src}" | "{tgt}", "translation": "..."}}.
If there is no real speech, return {{"spoken": "none", "translation": ""}}."""


class Translator:
    def __init__(self, doubao, robot: Robot, log=print):
        self.ai = doubao
        self.robot = robot
        self.log = log
        self.source = None  # owner's language
        self.target = None  # guest's language
        self.last = None  # (pcm, rate) of the last thing Robo said

    @property
    def active(self) -> bool:
        return self.target is not None

    # ---- input ----

    def hear_audio(self, wav: bytes) -> None:
        """One utterance from the microphone."""
        langs = [self.source, self.target] if self.active else [None]  # None = auto (Chinese/English)
        with ThreadPoolExecutor(len(langs)) as pool:
            texts = list(pool.map(lambda lang: self.ai.transcribe(wav, lang), langs))
        self.hear(dict(zip(langs, texts)))

    def hear_text(self, text: str) -> None:
        """Typed input instead of the microphone (for testing without audio)."""
        self.hear({None: text})

    def hear(self, transcripts: dict) -> None:
        if not any(t.strip() for t in transcripts.values()):
            return
        owner_text = transcripts.get(self.source) or transcripts.get(None) or ""
        if WAKE.match(owner_text) and self.command(owner_text):
            return
        if self.active:
            self.translate(transcripts)
        else:
            self.log(f"  (not translating yet, heard: {owner_text!r} — say \"Robo, translate English to German\")")

    # ---- commands ----

    def command(self, text: str) -> bool:
        """Handle "Robo, ..." Returns False if it wasn't really a command."""
        self.log(f"you (command): {text}")
        self.robot.gesture("think")
        session = f"translating {self.source}->{self.target}" if self.active else "not translating"
        cmd = self.ai.chat_json(COMMAND_PROMPT.format(session=session), text)
        action = cmd.get("action", "none")
        self.log(f"  [agent] {json.dumps(cmd, ensure_ascii=False)}")

        if action in ("start", "switch"):
            source = cmd.get("source") if action == "start" else self.source
            target = cmd.get("target")
            if source not in LANGUAGES or target not in LANGUAGES:
                self._say_to("owner", cmd.get("confirm") or "Sorry, I can't speak that language yet.",
                             source if source in LANGUAGES else "en", gesture="shrug")
                return True
            self.source, self.target = source, target
            self._say_to("owner", cmd.get("confirm", "OK"), source, gesture="nod")
            if cmd.get("greeting"):
                self._say_to("guest", cmd["greeting"], target, gesture="wave")
            return True
        if action == "stop":
            self._say_to("owner", cmd.get("confirm", "OK"), self.source or "en", gesture="nod")
            self.source = self.target = None
            return True
        if action == "repeat":
            if self.last:
                self.robot.say(*self.last)
            return True
        if cmd.get("confirm") and not self.active:  # e.g. unsupported language
            self._say_to("owner", cmd["confirm"], "en" if self.source is None else self.source, gesture="shrug")
            return True
        return False  # not a command: translate it normally

    # ---- translation ----

    def translate(self, transcripts: dict) -> None:
        src, tgt = self.source, self.target
        prompt = TRANSLATE_PROMPT.format(src=src, tgt=tgt, src_name=LANGUAGES[src].name, tgt_name=LANGUAGES[tgt].name)
        shown = {(LANGUAGES[k].name if k else "transcript"): v for k, v in transcripts.items()}
        result = self.ai.chat_json(prompt, json.dumps(shown, ensure_ascii=False))
        spoken, text = result.get("spoken"), (result.get("translation") or "").strip()
        if spoken not in (src, tgt) or not text:
            return
        if spoken == src:  # you spoke, so the translation goes to the guest
            self.log(f"you → guest ({self.target}): {text}")
            self._say_to("guest", text, self.target, gesture=self._polite_gesture(self.target))
        else:
            self.log(f"guest → you ({self.source}): {text}")
            self._say_to("owner", text, self.source, gesture="nod")

    # ---- output ----

    def _say_to(self, who: str, text: str, lang: str, gesture: str | None = None) -> None:
        self.robot.face(who)
        if gesture:
            self.robot.gesture(gesture)
        self.log(f"Robo ({lang}): {text}")
        pcm = self.ai.speak(text, lang)
        self.last = (pcm, TTS_SAMPLE_RATE)
        self.robot.say(pcm, TTS_SAMPLE_RATE)
        self.robot.gesture("listen")

    @staticmethod
    def _polite_gesture(lang: str) -> str:
        return "bow" if lang in ("ja", "ko") else "nod"
