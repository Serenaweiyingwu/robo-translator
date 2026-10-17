"""The 小派+ body must send exactly the commands from Hightorque's ROS 2 doc (no robot needed)."""

from robo.hightorque import HightorqueRobot


class Recorder(HightorqueRobot):
    def __init__(self):
        super().__init__(mute=True, log=lambda *_: None)
        self.sent = []
        self.state_after = {"'default'": "init", "'standing'": "standby", "'toggle_policy'": "running"}
        self.current = "init"

    def ros(self, args):
        self.sent.append(args)
        if args.startswith("topic echo"):
            return f"current_mode: default_bt\ncurrent_state: {self.current}\ncurrent_policy: bfm\n"
        for key, state in self.state_after.items():
            if key in args:
                self.current = state
        return "response:\nhightorque_msgs.srv.X_Response(success=True, message='')\n"


def test_start_follows_the_doc_sequence():
    r = Recorder()
    r.start()
    calls = [c for c in r.sent if c.startswith("service call")]
    assert calls == [
        "service call /hightorque_controller/change_fsm_state hightorque_msgs/srv/ChangeState \"{states: ['default']}\"",
        "service call /hightorque_controller/change_state hightorque_msgs/srv/ChangeState \"{states: ['standing']}\"",
        "service call /hightorque_controller/change_state hightorque_msgs/srv/ChangeState \"{states: ['toggle_policy']}\"",
    ]


def test_gestures_map_to_waypoints_and_unknown_ones_are_skipped():
    r = Recorder()
    for g in ["wave", "nod", "handshake", "think", "cheer"]:
        r.gesture(g)
    r.wait_idle()
    assert r.sent == [
        f"service call /hightorque_controller/execute_waypoint hightorque_msgs/srv/ExecuteWaypoint \"{{action_name: '{w}'}}\""
        for w in ["hello", "woshou", "cheer"]
    ]


def test_facing_turns_on_cmd_vel_then_stops_and_only_when_needed():
    r = Recorder()
    r.face("owner")  # already facing the owner: no move
    r.face("guest")
    r.face("guest")
    r.wait_idle()
    assert len(r.sent) == 2
    assert r.sent[0].startswith("topic pub --times") and "/cmd_vel" in r.sent[0] and "z: 0.60" in r.sent[0]
    assert r.sent[1] == 'topic pub --once /cmd_vel geometry_msgs/msg/Twist "{}"'
