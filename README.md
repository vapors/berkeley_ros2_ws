# Berkeley ROS 2 Workspace v2.5 — Documentation Set

This documentation set was generated from the supplied `berkeley_ros2_ws_v2_5_src.zip` source archive.

- Source archive SHA-256: `f2326c6d8da475e6b6b26c3ad1ac7199a30249f28a63b1895a4edbc84311af93`
- Native ST3215 package version: `0.2.7`
- Primary deployment target: Orange Pi 5 Max, ROS 2 Humble, direct ST3215 bus on `/dev/ttyS3`

## Documents

1. [`BERKELEY_ROS2_WS_V2_5_REFERENCE.md`](/src/docs/BERKELEY_ROS2_WS_V2_5_REFERENCE.md) — consolidated architecture and package manual.
2. [`PACKAGE_REFERENCE.md`](PACKAGE_REFERENCE.md) — package-by-package purpose, nodes, launch files, and current status.
3. [`INTERFACES_AND_PARAMETERS.md`](INTERFACES_AND_PARAMETERS.md) — topics, services, launch switches, parameters, and script CLI options.
4. [`COMMAND_CHEATSHEET.md`](COMMAND_CHEATSHEET.md) — copy/paste shell commands for build, bring-up, calibration, policy, identification, and standing-load work.
5. [`WORKFLOWS.md`](WORKFLOWS.md) — recommended operational sequences and source-of-truth hierarchy.
6. [`KNOWN_LEGACY_AND_CAVEATS.md`](KNOWN_LEGACY_AND_CAVEATS.md) — components that are legacy, experimental, or not authoritative in v2.5.

Machine-readable appendices:

- `package_inventory.csv`
- `topic_service_matrix.csv`
- `parameter_reference.csv`
- `joint_contract_v2_5.csv`

## Primary control graph

```text
joy_node
   │ /joy
   ▼
teleop_twist_joy
   │ /command_velocity
   ▼
berkeley_biped_node ── ONNX inference + readiness gates
   │ /desired_position
   ▼
pd_controller_node ── safety_only | outer_pd | outer_pid
   │ /servo_target_radians
   ▼
bhl_st3215_driver ── final clamp + rad↔step conversion + bus I/O
   │ /dev/ttyS3 @ 1 Mbps
   ▼
Seeed bus board → ST3215 IDs 1..12

Feedback:
ST3215 → driver → /joint_states + /joint_feedback_age_ms + telemetry
IMU → /imu/data → policy node
```
