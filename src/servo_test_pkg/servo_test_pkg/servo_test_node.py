#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float64MultiArray
from rclpy.qos import QoSProfile, QoSReliabilityPolicy
import yaml
import os
import numpy as np

class ServoTestNode(Node):
    def __init__(self):
        super().__init__('servo_test_node')

        # Declare and get parameter for starting pose
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

    def apply_pose(self, pose_name):
        if pose_name not in self.poses:
            self.get_logger().error(f"❌ Pose '{pose_name}' not found in YAML.")
            return

        pose = self.poses[pose_name]
        self.publish_positions(pose)
        self.get_logger().info(f"📤 Applied pose: '{pose_name}'")

    def publish_positions(self, positions):
        """Publish raw radians directly to /servo_position_speed."""
        msg = Float64MultiArray()
        msg.data = [float(val) for val in positions]
        self.pos_pub.publish(msg)
        self.get_logger().debug(f"📤 Published radians: {msg.data}")

    def command_callback(self, msg: String):
        command = msg.data.strip()
        if command in self.poses:
            self.apply_pose(command)
        elif command.startswith('servo_test:'):
            parts = command.split(':')
            if len(parts) == 4:
                try:
                    servo_index = int(parts[1])
                    min_angle = float(parts[2])
                    max_angle = float(parts[3])
                    self.sweep_servo(servo_index, min_angle, max_angle)
                except ValueError:
                    self.get_logger().error("❌ Invalid servo_test parameters")
            else:
                self.get_logger().error("❌ servo_test command format: servo_test:<index>:<min_rad>:<max_rad>")
        else:
            self.get_logger().warn(f"⚠️ Unknown command: '{command}'")

    def sweep_servo(self, servo_index, min_angle, max_angle):
        """Sweep a single servo back and forth within limits."""
        if servo_index < 0 or servo_index >= self.num_joints:
            self.get_logger().error("❌ Invalid servo index")
            return

        for angle in [min_angle, max_angle, min_angle]:
            positions = [0.0] * self.num_joints
            positions[servo_index] = angle
            self.publish_positions(positions)
            self.get_logger().info(f"🔄 Sweeping servo {servo_index} to {angle:.2f} rad")
            rclpy.spin_once(self, timeout_sec=1.5)  # Small delay between moves

def main(args=None):
    rclpy.init(args=args)
    node = ServoTestNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
