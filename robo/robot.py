"""The robot body. FakeRobot prints what the robot would do; swap in the real RP1 calls on the day.

Keep this interface small: the translator only needs a voice and a few gestures.
"""


class Robot:
    def say(self, pcm: bytes, rate: int) -> None:
        raise NotImplementedError

    def gesture(self, name: str) -> None:
        """name is one of: wave, handshake, cheer, nod, bow, shrug, listen, think."""
        raise NotImplementedError

    def face(self, who: str) -> None:
        """Turn towards 'owner' (you) or 'guest' (the person you're talking to)."""
        raise NotImplementedError


class FakeRobot(Robot):
    def __init__(self, mute: bool = False):
        self.mute = mute

    def say(self, pcm: bytes, rate: int) -> None:
        if not self.mute and pcm:
            from . import audio

            audio.play(pcm, rate)

    def gesture(self, name: str) -> None:
        print(f"  [robot] gesture: {name}")

    def face(self, who: str) -> None:
        print(f"  [robot] turns to face the {who}")
