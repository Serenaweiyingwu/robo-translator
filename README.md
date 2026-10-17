# Robo — a translator robot

Built for 灵机一动 · Soul Hackathon 2026, running on a Hightorque 小派+ (PiPlus).

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
- **豆包语音** API key, with 录音文件识别2.0 (`volc.seedasr.auc`) and 语音合成2.0 (`seed-tts-2.0`) activated
- **火山方舟** API key and a Doubao model (default `doubao-seed-1-6-flash-250828`)

Tip: wear a clip-on wireless mic. The venue is loud and the robot's motors are noisy.

## The robot: Hightorque 小派+

`robo/hightorque.py` drives the 小派+ with the commands from Hightorque's ROS 2 control doc:

| Robo | 小派+ |
|---|---|
| start-up | `change_fsm_state ['default']` → `change_state ['standing']` → `change_state ['toggle_policy']`, checking `/hightorque_controller/state` after each step |
| wave / handshake / cheer | `execute_waypoint` `hello` / `woshou` / `cheer` (allowed while walking) |
| turn to you / the guest | `/cmd_vel` at 50 Hz, then an explicit stop |
| speech | laptop or a Bluetooth speaker on the robot |

```bash
HT_SSH=user@robot-ip .venv/bin/python -m robo --robot hightorque --robot-check  # try the body, no Doubao calls
HT_SSH=user@robot-ip .venv/bin/python -m robo --robot hightorque                # translate with the robot
```

Commands run over SSH on the robot, where Hightorque's (private) `hightorque_msgs` is installed.
Gestures run on a background thread so Robo never waits for the robot before speaking.

### Testing without the robot

`sim/` has a stand-in controller with the same services and state rules, driving turtlesim:

```bash
cd ~/rp1-ros && pixi run build      # ROS 2 Humble via RoboStack; see sim/pixi.toml.example
pixi run turtle                      # terminal 1
pixi run controller                  # terminal 2
.venv/bin/python -m robo --robot hightorque --robot-check   # terminal 3, from this repo (HT_SSH unset = local)
```
