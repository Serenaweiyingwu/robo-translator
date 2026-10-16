# Robo — a translator robot

Built for 灵机一动 · Soul Hackathon 2026, running on a RoboParty RP1.

Robo follows you around and interprets for you. Tell it who you're talking to and it translates both ways:

```
you:   "Robo, help me translate English to German now"
Robo:  "OK, English to German."              (to you)
Robo:  "Hallo! Ich übersetze für sie."        (turns to the guest, waves)
you:   "Where is the train station?"
Robo:  "Wo ist der Bahnhof?"                  (to the guest, nods)
guest: "Geradeaus, dann links."
Robo:  "Straight ahead, then left."           (to you)
you:   "Robo, stop"
```

Other commands: **"Robo, switch to French"**, **"Robo, repeat"**. Commands are understood by a language
model, so any phrasing works, in English or Chinese ("萝卜，帮我翻译成德语").

## How it works

```
mic ─► speech recognition (Doubao) ─► "Robo, ..."? ── yes ─► interpret command ─► confirm + greet guest
                                             │
                                             no ─► translate (Doubao LLM) ─► speech (Doubao TTS) ─► robot speaker + gesture
```

- **Listening for two languages at once.** Doubao speech recognition only auto-detects Chinese and English, so
  once a pair is set, each utterance is recognised as *both* languages in parallel. The language model sees both
  transcripts, works out which one is real (so it knows whether you or the guest spoke), and translates.
  No buttons, no "your turn" switching.
- **Body language.** Robo turns to whoever it's addressing, waves when it greets the guest, nods (or bows for
  Japanese/Korean) when it delivers a translation, and shrugs when something fails.
- **The robot is behind a small interface** (`robo/robot.py`: `say`, `gesture`, `face`). `FakeRobot` prints
  actions and plays audio on the laptop; the RP1 adapter replaces it on the day.

21 languages supported: English, Chinese, German, French, Spanish, Portuguese, Italian, Japanese, Korean,
Russian, Arabic, Thai, Vietnamese, Indonesian, Malay, Turkish, Polish, Dutch, Ukrainian, Romanian, Greek.

## Run it

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env            # add your Volcengine keys
.venv/bin/python -m robo        # microphone mode
.venv/bin/python -m robo --text # type instead of speaking
.venv/bin/pytest                # offline tests
```

You need a Volcengine account with:
- **豆包语音** API key, with `volc.bigasr.auc_turbo` (录音文件识别极速版) and `seed-tts-2.0` (语音合成 2.0) enabled
- **火山方舟** API key and a Doubao model (default `doubao-seed-1-6-flash-250828`)

Tip: wear a clip-on wireless mic. The venue is loud and the robot's motors are noisy.

## Deploying to RP1

Write an `RP1Robot(Robot)` class in `robo/robot.py` using the SDK provided at the event, and map:

| Robo needs | RP1 |
|---|---|
| `say(pcm, rate)` | robot speaker, or a Bluetooth speaker mounted on it |
| `gesture(name)` | arm/head motion presets (wave, nod, bow, shrug, listen, think) |
| `face(who)` | turn in place towards you / the guest |

Following you around depends on what the event SDK exposes (camera + velocity control → person following;
otherwise "come here" commands).
