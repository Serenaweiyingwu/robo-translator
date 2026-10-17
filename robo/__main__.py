"""Run Robo.

    python -m robo            # listen on the microphone
    python -m robo --text     # type instead of speaking (no microphone needed)
    python -m robo --mute     # don't play audio, just print
    python -m robo --robot hightorque               # drive the 小派+ (HT_SSH=user@ip) or the turtlesim stand-in
    python -m robo --robot hightorque --robot-check # start the robot and try each gesture, no Doubao calls
"""

import argparse
import sys

from .agent import Translator
from .config import load_settings
from .doubao import Doubao, DoubaoError
from .robot import FakeRobot


def main() -> None:
    p = argparse.ArgumentParser(prog="robo", description="Robo, the translator robot")
    p.add_argument("--text", action="store_true", help="type utterances instead of using the microphone")
    p.add_argument("--mute", action="store_true", help="don't play speech through the speaker")
    p.add_argument("--robot", choices=["fake", "hightorque"], default="fake", help="which body to drive")
    p.add_argument("--robot-check", action="store_true", help="start the robot and run each gesture (no Doubao calls)")
    args = p.parse_args()

    settings = load_settings()
    if args.robot == "hightorque":
        from .hightorque import HightorqueRobot

        body = HightorqueRobot(mute=args.mute)
        print("Starting the robot (default -> standing -> walking policy)...")
        body.start()
    else:
        body = FakeRobot(mute=args.mute)

    if args.robot_check:
        for step in ["wave", ("face", "guest"), "handshake", ("face", "owner"), "cheer"]:
            print(f"robot check: {step}")
            body.face(step[1]) if isinstance(step, tuple) else body.gesture(step)
        getattr(body, "wait_idle", lambda: None)()
        print("robot check done")
        return

    if not settings.speech_api_key or not settings.ark_api_key:
        sys.exit("Missing keys: copy .env.example to .env and fill in VOLC_SPEECH_API_KEY and ARK_API_KEY.")

    robo = Translator(Doubao(settings), body)
    print('Robo is awake. Say "Robo, translate English to German" to start, "Robo, stop" to end. Ctrl+C quits.')

    if args.text:
        print("Text mode: type what you or your guest would say.")
        next_input = lambda: robo.hear_text(input("> "))
    else:
        from .audio import Mic

        mic = Mic()
        print("Measuring room noise, stay quiet for a second...")
        mic.calibrate()
        print("Listening.")
        next_input = lambda: robo.hear_audio(mic.listen())

    while True:
        try:
            next_input()
        except (KeyboardInterrupt, EOFError):
            print("\nGood night, Robo.")
            return
        except DoubaoError as e:
            print(f"  [error] {e}")
            robo.robot.gesture("shrug")


if __name__ == "__main__":
    main()
