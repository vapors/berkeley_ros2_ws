#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float64MultiArray
from rclpy.qos import QoSProfile, QoSReliabilityPolicy
import yaml
import os
import math
import numpy as np

class ServoTestNode(Node):
    def __init__(self):
        super().__init__('servo_test_node')

        # Parameter for starting pose
        self.declare_parameter('pose', 'neutral')
        self.starting_pose = self.get_parameter('pose').get_parameter_value().string_value

        # Load YAML config
        pkg_share_dir = os.path.join(
            os.getenv('HOME'),
            'berkeley_ros2_ws/src/servo_test_pkg/config'
        )
        yaml_file = os.path.join(pkg_share_dir, 'servo_poses.yaml')
        with open(yaml_file, 'r') as file:
            self.config = yaml.safe_load(file)

        self.poses = self.config['poses']
        self.joint_limits = self.config['limits']
        self.num_joints = len(self.joint_limits)

        # Publisher
        qos = QoSProfile(depth=10, reliability=QoSReliabilityPolicy.RELIABLE)
        self.pos_pub = self.create_publisher(Float64MultiArray, "/servo_position_speed", qos)

        # Subscriber
        self.command_sub = self.create_subscription(
            String, '/servo_test_command', self.command_callback, 10
        )

        self.get_logger().info(f"✅ ServoTestNode initialized with starting pose: '{self.starting_pose}'")

        # Apply starting pose
        self.apply_pose(self.starting_pose)

    def radians_to_st3215_pos(self, radians):
        """Convert radians to ST3215 steps (0–4095)."""
        steps_per_radian = (4095 / 2) / math.pi
        center = 2047
        pos_steps = radians * steps_per_radian + center
        return np.clip(pos_steps, 0, 4095).astype(int)

    def apply_pose(self, pose_name):
        if pose_name not in self.poses:
            self.get_logger().error(f"❌ Pose '{pose_name}' not found in YAML.")
            return

        pose = self.poses[pose_name]
        self.publish_positions_only(pose)
        self.get_logger().info(f"📤 Applied pose: '{pose_name}'")

    def publish_positions_only(self, positions):
        """Publish only positions (scaled) for testing."""
        scaled_positions = self.radians_to_st3215_pos(np.array(positions))
        msg = Float64MultiArray()
        msg.data = [float(pos) for pos in scaled_positions]  # ONLY positions
        self.pos_pub.publish(msg)
        self.get_logger().info(f"📤 Published test positions: {msg.data}")

    def command_callback(self, msg: String):
        command = msg.data.strip()
        if command in self.poses:
            self.apply_pose(command)
        else:
            self.get_logger().warn(f"⚠️ Unknown command: '{command}'")


def main(args=None):
    rclpy.init(args=args)
    node = ServoTestNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
