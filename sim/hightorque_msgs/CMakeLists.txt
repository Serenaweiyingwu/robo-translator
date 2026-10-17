# Stand-in for Hightorque's private hightorque_msgs, shaped after their ROS 2 docs, for testing on turtlesim.
cmake_minimum_required(VERSION 3.8)
project(hightorque_msgs)
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/ControllerState.msg"
  "srv/ChangeState.srv"
  "srv/SwitchPolicy.srv"
  "srv/Common.srv"
  "srv/ExecuteWaypoint.srv"
)
ament_package()
