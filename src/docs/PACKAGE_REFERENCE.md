# Package Reference — berkeley_ros2_ws v2.5

## 1. `bhl_st3215_driver` — native hardware authority

**Version:** 0.2.7  
**Role:** Owns the physical UART and ST3215 bus. This is the only package that should convert canonical radians to servo steps or perform final raw-step clamping.

Main executable:

```bash
ros2 run bhl_st3215_driver bhl_st3215_driver_node
```

Primary launch:

```bash
ros2 launch bhl_st3215_driver bhl_st3215_driver.launch.py
```

Core functions:

- 50 Hz native bus worker on `/dev/ttyS3`, 1 Mbps by default;
- one 12-servo SyncWrite command path;
- one contiguous `0x38..0x46` feedback read per servo per sweep;
- rotating first-read servo index to distribute sample-age skew;
- canonical radian↔step conversion from `config/servo_map.yaml`;
- final radian and raw-step clamping;
- compact `/joint_states` publication with derived/filtered velocity;
- per-joint physical read-age publication;
- cycle-synchronous telemetry for actuator identification;
- low-rate diagnostics and error counters;
- guarded move-to-default, software pose override, current-pose hold;
- explicit all-servo torque disable and torque-enable-at-current-pose services;
- calibration, direct actuator identification, and standing-load tools.

Installed helper tools:

```text
print_default_pose_reference.py
capture_default_pose_calibration.py
apply_servo_calibration.py
verify_default_pose_calibration.py
default_pose_move_console.py
servo_identification_runner.py
standing_load_characterization_runner.py
```

Authoritative config files:

- `config/servo_driver.yaml` — bus timing, watchdog, write enable, topic/service names.
- `config/servo_map.yaml` — servo IDs, signs, calibrated centers, measured v2.5 limits, raw safe step ranges, training defaults.
- `config/track1_action_contract_v3.yaml` — mirrored Track 1 contract used by standing-load preflight audit.
- `config/standing_pose_library.yaml` — template/example pose-library structure.

## 2. `berkeley_biped_pkg` — policy inference and sim-to-real policy contract

**Version:** 0.2.0  
**Role:** Loads the ONNX policy, validates the 45-observation/12-action contract, gates inference on sensor freshness, builds the observation vector, clips outputs against the canonical hardware limits, and publishes `/desired_position`.

Main executable:

```bash
ros2 run berkeley_biped_pkg berkeley_biped_node
```

Primary launch:

```bash
ros2 launch berkeley_biped_pkg berkeley_biped_launch.py
```

That launch starts:

- `joy/joy_node`;
- `teleop_twist_joy/teleop_node` remapped to `/command_velocity`;
- `berkeley_biped_node`;
- `joystick_bridge/cmd_vel_to_file`;
- `pd_controller_pkg/pd_controller_node`.

Policy-node functions:

- resolves a paired ONNX artifact from `policy_latest.yaml` or an explicit override;
- verifies `policy_sha256` when present;
- validates ONNX input/output dimensions;
- builds the exact 45-element observation vector:
  - command velocity `[3]`,
  - base angular velocity `[3]`,
  - projected gravity `[3]`,
  - relative joint position `[12]`,
  - joint velocity `[12]`,
  - previous raw action `[12]`;
- checks IMU freshness, joint-state freshness, and physical feedback-age freshness;
- zeroes stale command velocity when configured rather than stopping balance inference;
- publishes readiness/status and detailed policy debug topics;
- maps policy action to target using the current policy YAML action scale and clips against `joint_map.yaml` limits.

Important configs:

- `src/configs/policy_latest.yaml` — current deployment policy metadata and paired ONNX path/checksum.
- `src/configs/policy_runtime.yaml` — freshness gates and IMU extrinsic transform.
- `src/configs/joint_map.yaml` — canonical policy order, defaults, v2.5 measured limits, servo metadata mirror.
- `src/configs/twist_mux.yaml` — keyboard/joystick priorities for the optional mux launch.
- `src/configs/joint_limits.yaml` — compatibility/documentation mirror only; not current runtime authority.

Current policy timing from `policy_latest.yaml`:

```text
policy_dt = 0.04 s  (25 Hz inference)
control_dt = 0.04 s
physics_dt = 0.005 s
observations = 45
actions = 12
```

## 3. `pd_controller_pkg` — downstream command shaping and optional outer loop

**Version:** 0.2.0  
**Role:** Receives policy/reference positions and emits the final canonical radian command stream consumed by the native ST3215 driver.

Executable:

```bash
ros2 run pd_controller_pkg pd_controller_node
```

Modes:

| Mode | Behavior |
|---|---|
| `safety_only` | sanitize → joint-limit clip → low-pass → velocity limit → acceleration limit → position target |
| `outer_pd` | velocity-form position feedback using measured `q` and `qdot`, then integrates bounded velocity to a position target |
| `outer_pid` | `outer_pd` plus integral state, clamp, and conditional anti-windup |

Control law for outer modes:

```text
error      = q_ref - q
vel_error  = qdot_ref - qdot
qdot_cmd   = Kp*error + Kd*vel_error + Ki*integral(error)
q_cmd_next = q_cmd_prev + bounded(qdot_cmd) * dt
```

The output is still a **position target**. `/pd_torque_debug` is compatibility/debug only and is not connected to the ST3215 command path.

## 4. `joystick_bridge` — command mirror for external/Isaac consumers

Executable:

```bash
ros2 run joystick_bridge cmd_vel_to_file
```

Function:

- subscribes `/command_velocity`;
- writes `linear.x linear.y angular.z` to `/tmp/joystick_cmd.txt` on every callback.

It is not part of the servo-control safety path.

## 5. `servo_test_pkg` — legacy test utility

Executable:

```bash
ros2 run servo_test_pkg servo_test_node
```

Current code can:

- publish named poses from `servo_poses.yaml`;
- accept `/servo_test_command` strings;
- perform a simple single-index sweep command.

**v2.5 status: legacy/not recommended for the native driver path.** It publishes `/servo_position_speed`, uses old limits, uses a hard-coded source-tree path, and the launch file passes `pose_name` while the node declares `pose`. Prefer `bhl_st3215_driver` calibration, identification, and standing-load tools.

## 6. `lilgreen_description` — ROS visualization/description package

Functions:

- Xacro/URDF robot description;
- meshes and RViz config;
- `display.launch.py` for `robot_state_publisher` + joint-state GUI + RViz;
- `gazebo.launch.py` for classic Gazebo spawning.

Commands:

```bash
ros2 launch lilgreen_description display.launch.py gui:=True
ros2 launch lilgreen_description gazebo.launch.py
```

**Important:** the URDF/Xacro limits are not the runtime v2.5 hardware authority. The active hardware-control limits are synchronized between `berkeley_biped_pkg/src/configs/joint_map.yaml` and `bhl_st3215_driver/config/servo_map.yaml`.

## 7. `teleop_twist_joy` — joystick-to-Twist translator

**Version:** 2.4.8.  
The project launch uses `config/shanwan.config.yaml` by default and remaps `/cmd_vel` to `/command_velocity`.

Project mapping:

```text
linear.x axis = 1, scale = 0.7
linear.y axis = 2, scale = 0.7
angular.yaw axis = 0, scale = 0.4
require_enable_button = false
```

## 8. Bundled joystick-driver source packages

The workspace vendors ROS joystick-driver sources:

- `joy` 3.3.0 — SDL2-based generic joystick/game-controller node; used by the primary launch.
- `joy_linux` 3.3.0 — Linux `/dev/input/js*` alternative; not used by the primary launch.
- `sdl2_vendor` 3.3.0 — SDL2 vendor dependency.
- `spacenav` 3.3.0 — 3Dconnexion SpaceNavigator support; not used by the biped launch.
- `wiimote` 3.3.0 and `wiimote_msgs` 3.3.0 — Wii controller support; not used by the biped launch.
- `ps3joy` — present but ignored by `AMENT_IGNORE`.
- `joystick_drivers` metapackage — present but ignored by `AMENT_IGNORE`.

## Canonical v2.5 joint contract

| Idx | Joint | ID | Sign | Center | q_default | Lower | Upper | Safe steps |
|---|---|---|---|---|---|---|---|---|
| 0 | leg_left_hip_roll_joint | 1 | -1 | 2041 | 0.000 | -0.695 | 0.781 | 1532..2494 |
| 1 | leg_left_hip_yaw_joint | 2 | -1 | 2027 | 0.000 | -0.089 | 0.644 | 1607..2085 |
| 2 | leg_left_hip_pitch_joint | 3 | -1 | 2110 | -0.100 | -1.922 | 0.681 | 1666..3363 |
| 3 | leg_left_knee_pitch_joint | 4 | -1 | 2051 | 0.400 | 0.135 | 2.235 | 594..1963 |
| 4 | leg_left_ankle_pitch_joint | 5 | 1 | 2024 | -0.300 | -0.810 | 0.710 | 1496..2487 |
| 5 | leg_left_ankle_roll_joint | 6 | 1 | 2021 | 0.000 | -0.514 | 0.913 | 1686..2616 |
| 6 | leg_right_hip_roll_joint | 7 | 1 | 2038 | 0.000 | -0.874 | 0.643 | 1468..2457 |
| 7 | leg_right_hip_yaw_joint | 8 | 1 | 2040 | 0.000 | -0.057 | 0.701 | 2003..2497 |
| 8 | leg_right_hip_pitch_joint | 9 | 1 | 2123 | -0.100 | -1.991 | 0.546 | 825..2479 |
| 9 | leg_right_knee_pitch_joint | 10 | 1 | 2051 | 0.400 | 0.172 | 2.241 | 2163..3512 |
| 10 | leg_right_ankle_pitch_joint | 11 | -1 | 2077 | -0.300 | -0.845 | 0.819 | 1543..2628 |
| 11 | leg_right_ankle_roll_joint | 12 | -1 | 2058 | 0.000 | -0.443 | 1.062 | 1366..2347 |
