"""Agent flow tests with a scripted stand-in for Doubao, so they run offline."""

from robo.agent import WAKE, Translator


class FakeDoubao:
    def __init__(self, replies):
        self.replies = list(replies)  # language-model replies, in order
        self.spoken = []  # (text, lang)

    def chat_json(self, system, user):
        return self.replies.pop(0)

    def speak(self, text, lang):
        self.spoken.append((text, lang))
        return b"pcm"

    def transcribe(self, wav, lang):
        return {None: "Robo, translate English to German", "en": "hello", "de": "hallo"}[lang]


class SilentRobot:
    def __init__(self):
        self.actions = []

    def say(self, pcm, rate):
        self.actions.append("say")

    def gesture(self, name):
        self.actions.append(name)

    def face(self, who):
        self.actions.append(f"face {who}")


def make(replies):
    ai, robot = FakeDoubao(replies), SilentRobot()
    return Translator(ai, robot, log=lambda *_: None), ai, robot


START = {"action": "start", "source": "en", "target": "de", "confirm": "OK, English to German.",
         "greeting": "Hallo! Ich übersetze für sie."}


def test_wake_word():
    assert WAKE.match("Robo, translate to German")
    assert WAKE.match("hey robo stop")
    assert WAKE.match("萝卜，帮我翻译成德语")
    assert not WAKE.match("I like this robot")


def test_ignores_speech_until_started():
    robo, ai, _ = make([])
    robo.hear_text("hello there")
    assert not robo.active and ai.spoken == []


def test_start_confirms_then_greets_guest():
    robo, ai, robot = make([START])
    robo.hear_text("Robo, help me translate English to German now")
    assert (robo.source, robo.target) == ("en", "de")
    assert ai.spoken == [("OK, English to German.", "en"), ("Hallo! Ich übersetze für sie.", "de")]
    assert "face guest" in robot.actions


def test_translates_both_ways():
    robo, ai, _ = make([START, {"spoken": "en", "translation": "Wo ist der Bahnhof?"},
                        {"spoken": "de", "translation": "Go straight ahead."}])
    robo.hear_text("Robo, translate English to German")
    robo.hear_text("Where is the train station?")
    robo.hear_text("Geradeaus.")
    assert ai.spoken[-2:] == [("Wo ist der Bahnhof?", "de"), ("Go straight ahead.", "en")]


def test_listens_in_both_languages_once_started():
    robo, ai, _ = make([START, {"spoken": "en", "translation": "Hallo"}])
    robo.hear_audio(b"wav")  # idle: auto-detect hears the start command
    seen = []
    ai.chat_json = lambda system, user: seen.append(user) or {"spoken": "en", "translation": "Hallo"}
    robo.hear_audio(b"wav")  # active: decoded as English and as German
    assert '"English": "hello"' in seen[0] and '"German": "hallo"' in seen[0]


def test_not_a_command_is_translated():
    robo, ai, _ = make([START, {"action": "none"}, {"spoken": "en", "translation": "Roboter sind toll"}])
    robo.hear_text("Robo, translate English to German")
    robo.hear_text("Robots are great")
    assert ai.spoken[-1] == ("Roboter sind toll", "de")


def test_stop():
    robo, ai, _ = make([START, {"action": "stop", "confirm": "Stopped."}])
    robo.hear_text("Robo, translate English to German")
    robo.hear_text("Robo, stop")
    assert not robo.active and ai.spoken[-1] == ("Stopped.", "en")
