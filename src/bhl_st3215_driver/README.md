# bhl_st3215_driver

Native ROS 2 Humble single-bus ST3215 driver for Berkeley-Humanoid-Lite on the Orange Pi 5 Max.

This first pass is designed around the measured direct-UART operating point:

- Orange Pi UART: `/dev/ttyS3`
- bus baud: `1,000,000`
- 12 ST3215 servos on one Seeed Bus Servo Driver Board
- 50 Hz whole-chain feedback sweep using one contiguous 0x38..0x46 read per servo
- 50 Hz 12-servo `SyncWritePosEx`
- one UART-owning worker thread
- rotating feedback scan start index
- per-joint monotonic sample timestamps and `/joint_feedback_age_ms`
- 50 Hz cycle-synchronous `/st3215_driver/telemetry` with command/write/sample timing
- direct load, voltage, temperature, status/moving, and current feedback in telemetry
- current ROS hardware interface preserved

## Preserved ROS interface

### Subscribed

`/servo_target_radians`

- type: `std_msgs/msg/Float64MultiArray`
- first 12 values are target joint positions in radians
- canonical policy/hardware order
- best effort, keep-last 1 subscription (matching micro-ROS v6.5.8)

### Published

`/joint_states`

- type: `sensor_msgs/msg/JointState`
- best effort sensor QoS
- default compact mode matches micro-ROS v6.5.8:
  - `name=[]`
  - `position[12]`
  - `velocity[12]`
  - `effort=[]`

`/joint_feedback_age_ms`

- type: `std_msgs/msg/UInt32MultiArray`
- best effort sensor QoS
- 12 values in canonical joint order
- each value is the age in milliseconds of the last successful physical read
- `UINT32_MAX` means no valid sample has been received


## Cycle-synchronous identification telemetry

`/st3215_driver/telemetry`

- type: `bhl_st3215_driver/msg/ServoTelemetry`
- best-effort QoS, nominally one message per completed 50 Hz native bus cycle
- each message is built from a coherent bus-cycle snapshot rather than joining independent ROS topics
- includes:
  - cycle index and steady-clock cycle start/end timestamps
  - command sequence, command-receipt timestamp, and command age
  - exact target radians plus quantized ST3215 target steps
  - SyncWrite attempted/ok state and exact steady-clock start/end timestamps
  - feedback sweep and cycle work durations
  - per-joint sample timestamps and feedback ages at cycle end
  - measured position and filtered velocity
  - raw position, raw speed, signed load, voltage, temperature, servo status, moving flag
  - raw current and decoded amperes (`6.5 mA/count`)

The STS3215 register window from `0x38` through `0x46` is read as one 15-byte
block per servo. That window includes position, speed, load, voltage, temperature,
status/moving information, and current. This avoids adding a second current-read
transaction for every servo.

`load_ratio` is the signed drive-output duty-cycle proxy from the servo, scaled by
`0.001`. It is **not electrical current**. Use `current_a` for direct current
feedback; the identification runner also reports the empirical absolute-load versus
absolute-current correlation for each run.

## Additional diagnostics

`/st3215_driver/diagnostics`

- type: `diagnostic_msgs/msg/DiagnosticArray`
- includes:
  - cycle rate
  - cycle work mean / p99 / max
  - feedback sweep mean / p99 / max
  - SyncWrite syscall mean / max
  - read RTT mean / p99 / max
  - read success and error counters
  - deadline miss and over-period counters
  - command age and watchdog state
  - per-joint feedback ages

Target conversion debug output:
`/servo_target_steps_debug`

- type: `std_msgs/msg/String`
- enabled by default at the diagnostics rate
- mirrors the latest received radians and their native ST3215 step conversion before writes are enabled

Optional compatibility/debug output:

`/st3215_feedback_debug`

Enable with `publish_legacy_debug_string: true`.

## Safety defaults

Physical writes are **disabled by default**.

The driver can be brought up in feedback-only mode first:

```bash
ros2 launch bhl_st3215_driver bhl_st3215_driver.launch.py \
  enable_writes:=false
```

Only after feedback, ages, signs, and target conversion have been verified should writes be enabled:

```bash
ros2 launch bhl_st3215_driver bhl_st3215_driver.launch.py \
  enable_writes:=true
```

The robot should be mechanically supported during initial write-enabled testing.

## Build

From the provided v2.4 source workspace, install dependencies and build:

```bash
cd ~/berkeley_ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --packages-select bhl_st3215_driver --symlink-install
source install/setup.bash
```

## First bring-up sequence

### 1. Feedback only

```bash
ros2 launch bhl_st3215_driver bhl_st3215_driver.launch.py \
  enable_writes:=false
```

Check:

```bash
ros2 topic hz /joint_states
ros2 topic hz /joint_feedback_age_ms
ros2 topic echo /joint_states --once
ros2 topic echo /joint_feedback_age_ms --once
ros2 topic echo /st3215_driver/diagnostics --once
ros2 topic hz /st3215_driver/telemetry
ros2 topic echo /st3215_driver/telemetry --once
```

Expected nominal rates are about 50 Hz for `/joint_states`, `/joint_feedback_age_ms`, and `/st3215_driver/telemetry`.

### 2. Verify policy gate compatibility

With the driver in feedback-only mode and the IMU path available (or policy IMU override enabled), the existing `berkeley_biped_node` should be able to satisfy its joint-state and hardware-age freshness gates.

### 3. Write-enabled test

After confirming target conversion/signs and supporting the robot safely:

```bash
ros2 launch bhl_st3215_driver bhl_st3215_driver.launch.py \
  enable_writes:=true
```

The existing control chain remains:

```text
berkeley_biped_node
        |
        v
/desired_position
        |
        v
pd_controller_node
        |
        v
/servo_target_radians
        |
        v
bhl_st3215_driver
        |
        v
/dev/ttyS3 -> Seeed bus board -> ST3215 IDs 1..12
```

## Rotating read order

The default scan start advances by one joint each cycle:

```text
cycle 0: 1,2,3,...,12
cycle 1: 2,3,4,...,12,1
cycle 2: 3,4,5,...,1,2
...
```

This preserves canonical ROS array order while distributing:

- the post-SyncWrite first-read serialization delay
- first-to-last sample-age skew
- rare host-scheduling delays

across all joints instead of penalizing the same servo every cycle.

Disable with:

```yaml
rotate_read_order: false
```

## Velocity semantics

The driver reads the complete 15-byte feedback block from `0x38` through `0x46` in one transaction per servo. That block includes raw position and raw speed, while `/joint_states.velocity` intentionally preserves the current micro-ROS behavior:

- velocity is derived from position delta divided by each joint's actual monotonic sample interval
- first valid sample reports zero velocity
- low-pass filtering uses `velocity_filter_alpha`
- small values are zeroed by `velocity_deadband_rad_s`

Raw ST3215 speed is exposed directly in `/st3215_driver/telemetry` and retained in the optional legacy debug string.

## Scheduling

The bus worker uses an absolute monotonic 20 ms cadence. It does not use `tcdrain()` or serial `flush()` in the hot path.

Optional Linux tuning parameters are present but disabled by default:

```yaml
worker_cpu: -1
realtime_priority: 0
```

Collect a native C++ baseline before enabling CPU affinity or `SCHED_FIFO` priority.

## Important hardware-map note

`config/servo_map.yaml` mirrors the supplied micro-ROS v6.5.8 **compiled** `include/servo_map.h`, including these physical direction signs:

```text
IDs 1-4:   -1
IDs 5-10:  +1
IDs 11-12: -1
```

The current provisional `joint_map.yaml` files in the supplied workspace/firmware source still contain `servo_sign: 1` for every joint. Those YAML signs were therefore not used for native conversion in this package.

Before final deployment, the hardware map should be treated as the authoritative place for servo centers, signs, step limits, and later calibration offsets.

## Guarded move to the Isaac training default pose

The v2 workspace adds an explicit, opt-in service for moving the physical robot
from its measured pose to the 12-action training default pose:

```text
[0.0, 0.0, -0.1, 0.4, -0.3, 0.0,
 0.0, 0.0, -0.1, 0.4, -0.3, 0.0]
```

The values are stored as `training_default_rad` in `config/servo_map.yaml` and
were copied from the supplied Isaac Lab `env.yaml` initial joint state.

Safety behavior:

- the service is rejected when `writes_enabled=false`;
- the service is rejected until complete servo feedback exists;
- the ramp starts from measured physical joint positions;
- interpolation uses smoothstep over `default_pose_move_duration_sec`;
- external `/servo_target_radians` commands are ignored while the pose override
  is active;
- by default the driver continues holding the training pose after the ramp.

Start the ramp:

```bash
ros2 service call \
  /st3215_driver/move_to_default_pose \
  std_srvs/srv/Trigger '{}'
```

Before handing control back to the PD/policy path, align the controller state to
measured feedback:

```bash
ros2 service call \
  /pd_controller/reset_to_feedback \
  std_srvs/srv/Trigger '{}'
```

Then explicitly release the driver override:

```bash
ros2 service call \
  /st3215_driver/release_pose_override \
  std_srvs/srv/Trigger '{}'
```

Because release re-enables the live external target stream, keep the robot on
the secure hanging/support apparatus until the policy and controller command
path has been validated.


## Keyboard-abort console for the default-pose ramp

Version 0.2.1 adds a guarded software abort service:

```bash
ros2 service call \
  /st3215_driver/abort_pose_move \
  std_srvs/srv/Trigger '{}'
```

The abort behavior is:

1. request the 50 Hz pose-ramp thread to stop;
2. join the ramp thread so it cannot write another ramp target;
3. latch the latest complete measured servo pose as the new hold target when available;
4. keep `pose_override_active=true`, so external policy/PD targets remain blocked.

For an interactive move with a keyboard abort key, use:

```bash
ros2 run bhl_st3215_driver default_pose_move_console.py
```

Type `MOVE` to begin. During the ramp, any of these keys requests the abort service:

- `SPACE`
- `q` / `Q`
- `a` / `A`
- `ESC`
- `Ctrl+C` also attempts an abort before exiting

**Important:** this is a software motion abort/hold. It is not a hardware power cut,
torque-disable circuit, or independent safety-rated emergency stop. Keep the robot
supported and keep the hardware power disconnect immediately available during commissioning.

Diagnostics now also include:

```text
pose_abort_count
```

## v2.2 calibration toolchain

Robot-specific horn and linkage calibration remains in `servo_map.yaml`; the
calibration tools do not rewrite ST3215 EEPROM center offsets.

The native driver publishes canonical-order raw hardware topics at the same
rate as `/joint_states`:

```text
/st3215_driver/raw_position_steps   std_msgs/msg/Int32MultiArray
/st3215_driver/raw_speed            std_msgs/msg/Int32MultiArray
```

Recommended calibration sequence:

```text
1. Mechanically place robot in the Isaac training-default pose.
2. Run print_default_pose_reference.py while indexing servo horns.
3. Launch driver feedback-only.
4. Run capture_default_pose_calibration.py.
5. Review center_step_proposal.yaml and servo_map.proposed.yaml.
6. Dry-run apply_servo_calibration.py, then re-run with --apply.
7. Rebuild/relaunch the driver.
8. Run verify_default_pose_calibration.py in feedback-only mode.
9. Enable writes and verify startup hold.
10. Run the guarded move_to_default_pose console with abort support.
11. Continue policy diagnostics and outer-PD tuning before releasing the policy.
```

Print the mechanical reference table:

```bash
ros2 run bhl_st3215_driver print_default_pose_reference.py
```

Capture a calibration proposal (read-only):

```bash
ros2 run bhl_st3215_driver capture_default_pose_calibration.py \
  --servo-map ~/berkeley_ros2_ws/src/bhl_st3215_driver/config/servo_map.yaml
```

Review and dry-run the application:

```bash
ros2 run bhl_st3215_driver apply_servo_calibration.py \
  calibration_reports/<timestamp>/center_step_proposal.yaml \
  --servo-map ~/berkeley_ros2_ws/src/bhl_st3215_driver/config/servo_map.yaml
```

Apply only after reviewing the diff:

```bash
ros2 run bhl_st3215_driver apply_servo_calibration.py \
  calibration_reports/<timestamp>/center_step_proposal.yaml \
  --servo-map ~/berkeley_ros2_ws/src/bhl_st3215_driver/config/servo_map.yaml \
  --apply
```

After rebuilding and relaunching feedback-only, verify the measured joint pose:

```bash
ros2 run bhl_st3215_driver verify_default_pose_calibration.py \
  --servo-map ~/berkeley_ros2_ws/src/bhl_st3215_driver/config/servo_map.yaml
```

The capture tool classifies corrections as fine software correction, mechanical
alignment review, mechanical re-index recommended, range conflict, or unstable
capture. The apply tool refuses blocking proposals by default and always writes
a timestamped backup before changing the source map.


## v2.4.2 fixed maximum-envelope identification profile

The v2.4.2 Track 1 baseline explicitly configures every ST3215 position SyncWrite with
`speed=0` and `acceleration=0`. The profile is fixed in `config/servo_map.yaml`; policy
and outer-PD outputs do not dynamically change these hardware profile fields in this
release. Diagnostics and cycle telemetry expose the resolved values so identification
reports remain self-describing.

For intentional profile-sensitivity experiments, use a separate servo-map configuration
and pass `--allow-nonmax-motion-profile` to the guarded identification runner. Do not mix
those results into the v2.4.2 Track 1 baseline without retaining the profile as metadata.

## v2.4.3 standing/crouch load characterization

The single-joint identification runner remains available unchanged. Whole-body loaded-pose work uses:

```bash
ros2 run bhl_st3215_driver standing_load_characterization_runner.py --help
```

### Capture a manually positioned pose with torque disabled

The robot must be mechanically supported before running capture mode.

```bash
ros2 run bhl_st3215_driver standing_load_characterization_runner.py \
  --mode capture_pose \
  --pose-name normal_stand \
  --base-com-height-mean-m 0.480 \
  --pose-library ~/.ros/bhl_standing_poses.yaml
```

Repeat for crouch poses after measuring each base-COM height. The capture mode stores the median measured 12-joint pose as `target_rad`.

### Evaluate standing/crouch poses

```bash
ros2 run bhl_st3215_driver standing_load_characterization_runner.py \
  --mode evaluate \
  --pose-library ~/.ros/bhl_standing_poses.yaml \
  --poses normal_stand,shallow_crouch,medium_crouch,deep_crouch \
  --crouch-speed-rad-s 0.20 \
  --stand-return-speed-rad-s 0.15 \
  --settle-sec 5 \
  --hold-sec 20 \
  --deep-hold-sec 8
```

By default the runner returns to the named standing pose between crouch poses. Use `--no-return-between-poses` for a direct pose-to-pose sequence.

The speed arguments limit the generated 50 Hz reference trajectory only. The ST3215 hardware motion profile remains fixed by the driver map.
