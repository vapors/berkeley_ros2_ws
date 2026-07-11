# Known Legacy Components and Caveats — v2.5

This file is intentionally candid about components that exist in the source tree but should not be treated as authoritative for current hardware deployment.

## 1. `servo_test_pkg` is legacy for v2.5

Reasons:

- publishes `/servo_position_speed`, while the native v2.5 driver consumes `/servo_target_radians`;
- `servo_poses.yaml` still contains older limit values;
- source code locates config through a hard-coded `~/berkeley_ros2_ws/src/...` path rather than package share;
- launch file passes parameter `pose_name`, while the node declares parameter `pose`.

Use native-driver tools instead:

```text
print_default_pose_reference.py
default_pose_move_console.py
servo_identification_runner.py
standing_load_characterization_runner.py
```

## 2. `biped_teleop_mux.launch.py` is optional/legacy

The primary supported launch is:

```bash
ros2 launch berkeley_biped_pkg berkeley_biped_launch.py
```

`biped_teleop_mux.launch.py` additionally assumes `teleop_twist_keyboard`, `twist_mux`, an X11/xterm environment, and uses a path-expression style that has not been validated as part of the v2.5 hardware path. Treat it as experimental until separately tested.

## 3. URDF/Xacro limits are not synchronized runtime safety limits

`lilgreen_description/urdf/lilgreen.xacro` still contains older articulation limits. In the current hardware path:

```text
policy/PD clamp: berkeley_biped_pkg/src/configs/joint_map.yaml
final hardware clamp: bhl_st3215_driver/config/servo_map.yaml
```

Do not assume URDF limits represent the v2.5 measured hardware contract.

## 4. `joint_limits.yaml` is a mirror only

Runtime `berkeley_biped_node` and `pd_controller_pkg` load limits from `joint_map.yaml`. The native driver loads `servo_map.yaml`.

## 5. The current packaged policy is still the current snapshot, not the upcoming Track 1 policy

The workspace source includes `policy_latest.yaml` and a paired current ONNX artifact. When the new Track 1 policy arrives:

- keep policy YAML and ONNX together;
- preserve/update the relative ONNX path;
- preserve or update the SHA-256 pairing field;
- verify the 45→12 ONNX shape contract unless the policy interface intentionally changes;
- run policy debug with driver pose override active before releasing commands.

## 6. Policy rate and bus/control rate differ

Current policy YAML uses `policy_dt=0.04 s` (25 Hz). The native driver and PD controller default to 50 Hz. This is intentional in the current snapshot: the downstream controller can shape/hold between policy updates.

## 7. `joystick_bridge` is not a safety or command source

It mirrors `/command_velocity` into `/tmp/joystick_cmd.txt` for external consumers. It does not command the servo bus.

## 8. `/joy` subscription inside `berkeley_biped_node` is compatibility-only

The callback intentionally performs no command processing. `/command_velocity` is canonical.

## 9. `hold_current_pose` and `abort_pose_move` are software holds, not safety-rated E-stops

The code asserts a software pose override and holds measured or last-safe command targets. Keep a physical power disconnect available during commissioning.

## 10. Torque-off capture requires mechanical support

`/st3215_driver/disable_torque_all` intentionally removes servo holding torque. Pose capture assumes the robot is mechanically supported while the operator positions the mechanism.

## 11. Standing-load IMU logging depends on actual `/imu/data` availability and QoS compatibility

The standing-load runner subscribes to `/imu/data`, but prior datasets showed NaN IMU fields. Before relying on body-level balance metrics, verify the runner receives valid IMU samples in the same ROS domain and middleware environment.

## 12. Vendor joystick packages are bundled source dependencies

`joy`, `joy_linux`, `sdl2_vendor`, `spacenav`, `wiimote`, and `wiimote_msgs` are upstream-style packages. Only `joy` is in the primary biped launch path. `ps3joy` and the joystick-drivers metapackage are ignored by `AMENT_IGNORE`.
