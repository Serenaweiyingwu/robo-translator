# Robo — notes for Claude sessions

Robo is a translator robot for **灵机一动 · Soul Hackathon** (organiser She Nicest). You say
"Robo, translate English to German"; it greets the other person and interprets both ways, with gestures.
Read this first, then `README.md`. Last updated 2026-10-17.

## Status (2026-10-17)

| Piece | State |
|---|---|
| Translator agent (`robo/agent.py`) | ✅ Works end to end on real Doubao (text mode, 8-turn en↔de↔ja test, ~1.5–2.7 s/turn) |
| Microphone mode | ⚠️ Not tried with a real voice yet; user is saving free quota (do one run when recording the demo) |
| 小派+ body (`robo/hightorque.py`) | ✅ Tested against the turtlesim stand-in only; real robot IP/login not yet known |
| Talking gestures | ⏳ Planned, see "Next" |
| Robot model | ⏳ Asked organisers (2026-10-17) for, in order: **① 维他动力 Vbot 大头 robot dog** ② **Hightorque Mini Pi Plus 基础款** ③ RoboParty RP1 (RP0 has no speaker). Code so far targets the Hightorque (ROS 2 docs) |

**Concept decided 2026-10-18: a "language guide dog"**, not a robot imitating a human interpreter. It trots
beside the owner, perks up when someone speaks, turns to them (DOA), and speaks for the owner with face/ear
expressions and head movement. Design gestures and persona for a dog: head nod/tilt/look, turn to speaker,
listening/thinking/speaking faces, follow. The Hightorque humanoid stays only as a fallback body.

**Vbot 大头 (维他动力 × 零零后科技)**, the current first choice, from press only (no developer docs seen yet):
autonomous "跟屁虫" following, depth stereo camera + 16-line LiDAR, face screen + speaker + lights for
expressions, ROS 2 interface with a GitHub guide (大头EDU edition, 128 TOPS; EDU can carry a back arm).
No arms otherwise, so body language = following, turning, face expressions. Ranked first because it can do the
"follows me" part; it drops if its interface doesn't expose following, speaker and face. A Vbot body would be a
new `Robot` subclass; the translator doesn't change.

Vbot developer facts (2026-10-18). The organiser sheet `~/Desktop/Vbot 烈变黑客松·硬件清单与使用教程.xlsx` has
only 3 links: vbot.cn/Detail (specs), forum.vbot.cn, github.com/VitaDynamics/vbot_ros2_msgs. Hardware is
exclusively assigned (独占分配). Support WeChat **towardsdawn** (note "shenicest参赛").
- Public msgs repo, **ROS 2 Humble**. Built on the Mac in `~/vbot_ws` with the `~/rp1-ros` pixi env
  (`pixi run --manifest-path ~/rp1-ros/pixi.toml ...`, same `-DPython_EXECUTABLE` flags); 15 pkgs, 89 interfaces.
- What Robo needs: `function_msgs/srv/ControlFollowing` (mode FOLLOWING=1 / ACCOMPANY=8 / COME_TO_ME=4),
  `SetFollowSpeed`; speaker `function_msgs/msg/AgentToSpeechAudioRaw` (16 kHz, 16-bit mono int16 PCM; ask
  Doubao TTS for 16000) or `SetSpeak` (HUMAN_VOICE text uses the dog's own TTS); `BaseAction`
  (ROTATE_IN_PLACE angle_rad, MOVE_HEAD pitch/yaw); `lowlevel_msg/msg/HeadCmd` (pitch/yaw deg + ms);
  mic `speech_msgs/msg/SpeechDogToPhone`; `speech_msgs/msg/WakeupInfo` has **DOA** (voice direction) to turn
  towards the speaker; `/speech/ChatTtsNotification` reports playback start/end.
- Only a few names are in the files (`/speech/ChatTtsNotification`, `/lightning/loc_cmd`, `/lightning/save_map`);
  get the rest with `ros2 topic list -t` / `ros2 service list -t` once on the dog's network.
- Forum: staff confirm raw mic audio + streaming playback were recently exposed; SSH `vbot@<ip from app>`
  (one version only accepted public keys); a user's SSH worked but "Zenoh communication refused", so the dog
  likely uses **rmw_zenoh**. Installed `ros-humble-rmw-zenoh-cpp` 0.1.8 in `~/rp1-ros` (has `rmw_zenohd`).
  The built-in agent can call custom MCP services (fallback path). Product page: 4-mic array, expression
  screen, ear lights, 14 joints (12 legs + likely 2 head), UWB module (following likely tracks a UWB tag).
- Asked support (WeChat draft in chat 2026-10-18): topic/service names, Zenoh router address/port +
  `ROS_DOMAIN_ID`, SSH access, how to silence the built-in agent while we stream audio, docs/examples.

## Deadlines

- **2026-10-22 12:00** — readiness submission: environment proof, agent name + description, progress, run proof
  (screenshot/recording), robot deployment plan. Results 22:00 same day.
- **2026-10-23** — on-robot day at 上海张江科学会堂: 09:30–12:00 deploy, 13:30–16:30 playground,
  16:30 optional 3–5 min stage demo. Robots are shared; changing the robot's low-level system,
  safety settings or hardware is not allowed without staff permission.

## How it works

- `robo/agent.py` — idle until an utterance starts with the wake word "Robo" (also 萝卜/罗博…).
  The LLM turns the command into start/stop/switch/repeat. Once a pair is set, each utterance is
  recognised in **both** languages in parallel and the LLM returns `{"spoken": <lang>, "translation"}`;
  direction comes from the detected language. (Asking the LLM "owner or guest?" was unreliable; don't go back.)
- `robo/doubao.py` — Doubao speech recognition, Ark LLM, Doubao TTS.
- `robo/robot.py` — `Robot` interface (`say`, `gesture`, `face`); `FakeRobot` prints and plays audio locally.
- `robo/hightorque.py` — `HightorqueRobot` runs `ros2` CLI commands over SSH (`HT_SSH=user@ip`) or locally
  (unset → `~/rp1-ros` turtlesim stand-in). Motion runs on a background queue so speech never waits.
- `sim/` — stand-in `hightorque_msgs` + `ht_mock` controller with the same services and state rules,
  driving turtlesim. `~/rp1-ros/src` is a symlink to `sim/`.

## Doubao / Volcengine (user's account, default project)

Keys live only in `.env` (gitignored via `.env*`, `!.env.example`). Never print or commit them; check the
history for the key strings before any push. If the user needs to paste a key, have them use:
`read -rs "K?Paste key: " && sed -i '' "s|^VAR=.*|VAR=$K|" ~/robo-translator/.env && unset K` (nano attempts
went wrong twice: once nothing saved, once a stray `".env "` file with a trailing space got committed locally).

- **Speech recognition**: fast endpoint `.../api/v3/auc/bigmodel/recognize/flash` with resource
  **`volc.seedasr.auc`** (model 2.0). The legacy `volc.bigasr.auc_turbo` is *not granted* to new accounts.
  Auto-detect covers only zh/en (+ dialects); every other language needs `audio.language` (e.g. `de-DE`).
  Streaming recognition 2.0 is zh/en only, so it can't hear German.
- **TTS**: `seed-tts-2.0`, voice `zh_female_vv_uranus_bigtts`, `explicit_language` per language. en + de verified.
- **LLM**: Ark, model **`doubao-seed-2-1-lite-260915`** (set in `.env` as `DOUBAO_MODEL`; the old default
  `doubao-seed-1-6-flash-250828` isn't available). `GET /api/v3/models` lists IDs.
- Free quotas: TTS 20,000 chars, each recognition service 20 h, LLM 500k tokens. The user is careful about
  usage: prefer offline tests and the turtlesim stand-in; ask before burning quota.

## Hightorque 小派+ control (from their DingTalk wiki "Hightorque高擎产品资料库" → 派加ROS2)

- Start-up: `/hightorque_controller/change_fsm_state` `{states: ['default']}` → `change_state`
  `{states: ['standing']}` → wait for `current_state: standby` → `change_state` `{states: ['toggle_policy']}`
  → `running`. Always confirm via `ros2 topic echo /hightorque_controller/state`; `success: true` only
  means "accepted".
- Gestures: `execute_waypoint` `hightorque_msgs/srv/ExecuteWaypoint "{action_name: 'cheer'}"`.
  `hello`, `woshou`, `cheer` are allowed while walking; `fuwo`, `yangwo`, `sitdown` only in standby.
- Walking/turning: `/cmd_vel` (`geometry_msgs/msg/Twist`) at ~50 Hz; stop by sending one zero Twist.
  Don't publish `/control_command` directly.
- `hightorque_msgs` is a **private** repo, so the Mac can't call these services itself; that's why Robo
  runs the CLI on the robot over SSH. The robot workspace path and ROS distro (Foxy vs Humble) are unknown;
  `HT_SETUP` overrides the default source commands.
- Older ROS 1 docs (`rostopic`, `/pi_plus_absolute` joint control) exist on the same wiki; ignore them for ROS 2.
- Hightorque's voice add-on (小智 / Xiaozhi) is flashed with Windows-only tools; speaker use is unconfirmed,
  so plan on a Bluetooth speaker.

### Event robot: Hightorque **Mini Pi Plus 基础款** (from organisers, 2026-10-17)

The organisers sent two Word docs (`~/Desktop/HT_SDK System描述和二次开发指南.docx`,
`~/Desktop/HT_机器人电机控制文档.docx`). They describe a **ROS 1** stack, which may not match the ROS 2
commands above:
- Control program `sim2real` (≥ 2.2.0) on a Lubancat (Rockchip, RKNN) board, user `hightorque`; status topic
  `/sim2real_master_node/mtr_state`; config in `~/.sim2real_info.json` → `pd.yaml` (`joint_names`);
  robot_type `S-12L8A0G2H0W`, action library under `/home/hightorque/action_library/`.
- States: INIT → STANDING → STANDBY → RUNNING; `RUNNING <-> TRAJ_SINGLE` plays one action (e.g. wave) and
  returns. The doc doesn't say how to trigger these without the gamepad (`/joy`).
- **Direct joint control**: `rostopic pub /pi_plus_absolute sensor_msgs/JointState` (or `/pi_plus_relative`),
  a standard message type, 50–200 Hz. While the policy runs, only motors it isn't using can be commanded,
  so arms/head should be free during walking.
- Joints: 12 leg + `l/r_shoulder_pitch`, `l/r_shoulder_roll`, `l/r_upper_arm`, `l/r_elbow`,
  `head_yaw`, `head_pitch`. **In the doc's sample all arm/head positions read 999.0**, so the 基础款 may have
  no arm/head motors. Unconfirmed.
- Asked the organisers: ROS 1 or 2? Arm/head motors on 基础款? How to stand/walk without the gamepad?
  Speaker: yes if hardware allows (ask how to play audio). New gestures via teach mode: yes if hardware allows.
- If arms exist, talking gestures = code-defined arm/head keyframes on `/pi_plus_absolute` (no teach mode
  needed), picked per sentence by the LLM gesture tag. If ROS 1, rewrite `HightorqueRobot` to run
  `rostopic`/`rosservice` over SSH (the SSH design still holds); the `sim/` stand-in is ROS 2 only.

## Mac ROS 2 setup (`~/rp1-ros`)

ROS 2 Humble via RoboStack + pixi (`~/.pixi/bin/pixi`, installed from the GitHub release because Homebrew
stalled on this network). Tasks: `pixi run build | turtle | controller`. Gotchas: CMake 4 can't find pixi's
Python without `-DPython_EXECUTABLE` (baked into the `build` task); macOS has no `timeout` command;
`ros2 topic pub --times` and `service call` wait forever if nothing is listening, so `HightorqueRobot.ros()`
times out after 20 s. Disk is tight (~16 GB free), so avoid an Ubuntu VM unless the organisers insist.

## Next

1. **Confirm the robot with the organisers**: model, IP/login for SSH, ROS distro, whether the speaker can play
   our audio, and whether we may record new gestures (teach mode, 示教) or send arm joint commands.
2. **Talking gestures** (agreed plan): add a `gesture` tag to the translation JSON (same LLM call, no extra
   cost), e.g. `beat`, `open_palms`, `point_guest`, `point_self`, `shrug`, `big`. Map tags to recorded
   waypoints when allowed; until then fall back to `hello`/`woshou`/`cheer` or skip. Test on turtlesim
   with stand-in moves in `sim/ht_mock`. Research models (EMAGE, DiffuseStyleGesture, Hightorque's
   GVHMR/GMR retargeting) are out of scope for a one-day deploy.
3. **Submission for 10-22**: environment screenshot (turtlesim + tests), one short real mic run recorded,
   deployment plan (SSH + ros2 CLI, commands above).
4. Optional: following the user (needs a camera feed; not available through the documented interface).

## Working with this user

- Never `git push` without an explicit "push". Committing locally is fine.
- Never enter passwords/keys yourself; the user signs in and pastes keys.
- They're often mid-workshop: keep updates short and give copy-paste commands.
