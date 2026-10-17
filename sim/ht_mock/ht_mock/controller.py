"""Stand-in for the Hightorque 小派+ controller, driving turtlesim instead of motors.

Same service and topic names as Hightorque's "ROS 2 上层控制基础逻辑" doc, and the same state rules:
  change_fsm_state ['default'] -> change_state ['standing'] -> STANDBY -> change_state ['toggle_policy'] -> RUNNING
/cmd_vel only moves the robot while RUNNING; fuwo/yangwo/sitdown only run in STANDBY.
"""

import math
from collections import deque

import rclpy
from geometry_msgs.msg import Twist
from hightorque_msgs.msg import ControllerState
from hightorque_msgs.srv import ChangeState, Common, ExecuteWaypoint, SwitchPolicy
from rclpy.node import Node

PARALLEL_WAYPOINTS = {"woshou", "cheer", "hello"}  # allowed while walking
STANDBY_WAYPOINTS = {"fuwo", "yangwo", "sitdown"}
TICK = 0.05


def twist(x=0.0, z=0.0):
    t = Twist()
    t.linear.x, t.angular.z = float(x), float(z)
    return t


# Each waypoint is a list of (forward speed, turn speed, seconds) segments the turtle plays out.
MOVES = {
    "hello": [(0, 3, 0.25), (0, -3, 0.5), (0, 3, 0.5), (0, -3, 0.25)],  # wiggle = wave
    "woshou": [(1.5, 0, 0.4), (-1.5, 0, 0.4)],  # step in and back = handshake
    "cheer": [(0, 2 * math.pi, 1.0)],  # full spin
    "fuwo": [(0, 0, 1.0)],
    "yangwo": [(0, 0, 1.0)],
    "sitdown": [(0, 0, 1.0)],
}


class MockController(Node):
    def __init__(self):
        super().__init__("hightorque_controller")
        self.mode, self.state, self.policy = "init", "init", "bfm"
        self.moves = deque()  # (Twist, seconds left)
        self.drive = self.create_publisher(Twist, "/turtle1/cmd_vel", 10)
        self.state_pub = self.create_publisher(ControllerState, "/hightorque_controller/state", 10)
        self.create_subscription(Twist, "/cmd_vel", self.on_cmd_vel, 10)
        p = "/hightorque_controller/"
        self.create_service(ChangeState, p + "change_fsm_state", self.on_fsm)
        self.create_service(ChangeState, p + "change_state", self.on_state)
        self.create_service(SwitchPolicy, p + "switch_policy", self.on_switch_policy)
        self.create_service(Common, p + "start_policy", lambda req, res: self.on_toggle(res, start=True))
        self.create_service(Common, p + "stop_policy", lambda req, res: self.on_toggle(res, start=False))
        self.create_service(ExecuteWaypoint, p + "execute_waypoint", self.on_waypoint)
        self.create_timer(TICK, self.tick)
        self.create_timer(0.2, self.publish_state)
        self.get_logger().info("mock Hightorque controller ready (state=init)")

    def reply(self, res, ok, msg):
        res.success, res.message = ok, msg
        self.get_logger().info(("OK: " if ok else "REJECTED: ") + msg)
        return res

    def on_fsm(self, req, res):
        if list(req.states) != ["default"]:
            return self.reply(res, False, f"unsupported fsm states {list(req.states)}")
        self.mode, self.state = "default_bt", "init"
        return self.reply(res, True, "mode default_bt")

    def on_state(self, req, res):
        target = list(req.states)[:1]
        if self.mode != "default_bt":
            return self.reply(res, False, "call change_fsm_state ['default'] first")
        if target == ["standing"]:
            self.state = "standby"  # the real robot passes through STANDING first
            return self.reply(res, True, "stood up -> standby")
        if target == ["toggle_policy"]:
            if self.state not in ("standby", "running"):
                return self.reply(res, False, f"cannot toggle policy from {self.state}")
            self.state = "running" if self.state == "standby" else "standby"
            return self.reply(res, True, f"policy toggled -> {self.state}")
        return self.reply(res, False, f"unsupported state {target}")

    def on_toggle(self, res, start):
        if self.state not in ("standby", "running"):
            return self.reply(res, False, f"not ready ({self.state})")
        self.state = "running" if start else "standby"
        return self.reply(res, True, self.state)

    def on_switch_policy(self, req, res):
        if self.state != "standby":
            return self.reply(res, False, "switch policy only in standby")
        self.policy = req.policy_name
        return self.reply(res, True, f"policy {self.policy}")

    def on_waypoint(self, req, res):
        name = req.action_name
        if name not in MOVES:
            return self.reply(res, False, f"unknown action {name!r}")
        if name in STANDBY_WAYPOINTS and self.state != "standby":
            return self.reply(res, False, f"{name} is standby_only (state={self.state})")
        if self.state not in ("standby", "running"):
            return self.reply(res, False, f"robot not standing (state={self.state})")
        for x, z, secs in MOVES[name]:
            self.moves.append([twist(x, z), secs])
        return self.reply(res, True, f"waypoint {name}")

    def on_cmd_vel(self, msg):
        if self.state != "running":
            self.get_logger().warn(f"/cmd_vel ignored: state={self.state} (needs running)", throttle_duration_sec=2.0)
            return
        if not self.moves:  # waypoints take priority over walking
            self.drive.publish(msg)

    def tick(self):
        if not self.moves:
            return
        move = self.moves[0]
        self.drive.publish(move[0])
        move[1] -= TICK
        if move[1] <= 0:
            self.moves.popleft()

    def publish_state(self):
        m = ControllerState()
        m.current_mode, m.current_state, m.current_policy = self.mode, self.state, self.policy
        self.state_pub.publish(m)


def main():
    rclpy.init()
    rclpy.spin(MockController())


if __name__ == "__main__":
    main()
