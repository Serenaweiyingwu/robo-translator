"""Hightorque 小派+ body, driven with the `ros2` command line.

Commands follow Hightorque's "ROS 2 上层控制基础逻辑" doc. They run over SSH on the robot (HT_SSH=user@ip),
where hightorque_msgs is installed, or locally against the turtlesim stand-in in rp1-ros (HT_SSH unset).
Speech plays on the laptop (or a Bluetooth speaker on the robot); only motion goes over ROS.
"""

import math
import os
import queue
import re
import shlex
import subprocess
import threading
import time

from .robot import FakeRobot

LOCAL_SETUP = 'cd ~/rp1-ros && eval "$(~/.pixi/bin/pixi shell-hook)" && source install/setup.bash'
ROBOT_SETUP = ("source /opt/ros/humble/setup.bash 2>/dev/null || source /opt/ros/foxy/setup.bash; "
               "for f in ~/*/install/setup.bash; do source $f; done")

# Robo's gestures -> Hightorque waypoints. Ones without a waypoint are skipped.
WAYPOINTS = {"wave": "hello", "handshake": "woshou", "cheer": "cheer"}
CONTROLLER = "/hightorque_controller"


class HightorqueRobot(FakeRobot):
    def __init__(self, mute: bool = False, log=print):
        super().__init__(mute=mute)
        self.log = log
        self.ssh = os.environ.get("HT_SSH", "")
        self.setup = os.environ.get("HT_SETUP", ROBOT_SETUP if self.ssh else LOCAL_SETUP)
        self.guest_angle = math.radians(float(os.environ.get("HT_GUEST_ANGLE", "60")))
        self.turn_speed = float(os.environ.get("HT_TURN_SPEED", "0.6"))  # rad/s
        self.facing = "owner"
        self.jobs = queue.Queue()
        threading.Thread(target=self._worker, daemon=True).start()

    # ---- Robot interface (non-blocking, run in order on a worker thread) ----

    def gesture(self, name: str) -> None:
        if name in WAYPOINTS:
            self.jobs.put(lambda: self.waypoint(WAYPOINTS[name]))

    def face(self, who: str) -> None:
        if who != self.facing:
            sign = 1 if who == "guest" else -1  # guest stands to the robot's left of the owner
            self.facing = who
            self.jobs.put(lambda: self.turn(sign * self.guest_angle))

    def wait_idle(self) -> None:
        self.jobs.join()

    # ---- ROS calls ----

    def start(self) -> None:
        """Bring the robot from power-on to walking-ready, checking state after each step as the doc says."""
        self.service("change_fsm_state", "ChangeState", "{states: ['default']}")
        self.wait_for("current_mode", "default_bt")
        self.service("change_state", "ChangeState", "{states: ['standing']}")
        self.wait_for("current_state", "standby", timeout=20)
        self.service("change_state", "ChangeState", "{states: ['toggle_policy']}")
        self.wait_for("current_state", "running", timeout=20)

    def waypoint(self, action: str) -> None:
        self.service("execute_waypoint", "ExecuteWaypoint", f"{{action_name: '{action}'}}")

    def turn(self, radians: float) -> None:
        speed = math.copysign(self.turn_speed, radians)
        pulses = max(1, round(abs(radians) / self.turn_speed * 50))  # /cmd_vel at 50 Hz, as the doc recommends
        self.ros(f'topic pub --times {pulses} --rate 50 /cmd_vel geometry_msgs/msg/Twist "{{angular: {{z: {speed:.2f}}}}}"')
        self.ros('topic pub --once /cmd_vel geometry_msgs/msg/Twist "{}"')  # explicit stop

    def service(self, name: str, srv: str, request: str) -> str:
        out = self.ros(f'service call {CONTROLLER}/{name} hightorque_msgs/srv/{srv} "{request}"')
        ok = "success=True" in out
        self.log(f"  [robot] {name} {request} -> {'ok' if ok else 'FAILED'}")
        if not ok:
            raise RuntimeError(f"{name} failed: {out.strip()[-300:]}")
        return out

    def state(self) -> dict:
        out = self.ros(f"topic echo --once {CONTROLLER}/state")
        return dict(re.findall(r"(\w+): (\w+)", out))

    def wait_for(self, field: str, value: str, timeout: float = 10) -> None:
        end = time.time() + timeout
        while time.time() < end:
            if self.state().get(field) == value:
                return
            time.sleep(0.5)
        raise RuntimeError(f"robot never reached {field}={value}")

    def ros(self, args: str) -> str:
        script = f"{{ {self.setup}; }} >/dev/null 2>&1; ros2 {args}"
        cmd = ["ssh", "-o", "BatchMode=yes", self.ssh, f"bash -lc {shlex.quote(script)}"] if self.ssh else ["bash", "-c", script]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        except subprocess.TimeoutExpired:  # e.g. the controller isn't running, so `service call` waits forever
            return f"timed out: ros2 {args}"
        return r.stdout + r.stderr

    def _worker(self) -> None:
        while True:
            job = self.jobs.get()
            try:
                job()
            except Exception as e:  # a failed gesture must never stop the translator
                self.log(f"  [robot] {e}")
            finally:
                self.jobs.task_done()
