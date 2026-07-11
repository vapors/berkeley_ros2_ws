#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float64MultiArray
import numpy as np
import onnxruntime as ort
import os

class SlimPolicyNode(Node):
    def __init__(self):
        super().__init__('berkeley_policy_play_node')
        self.get_logger().info("🟢 Slim Berkeley Policy Node Starting…")

        # Load ONNX policy
        policy_path = os.path.expanduser("~/berkeley_ros2_ws/src/berkeley_humanoid_lite/policies/policy.onnx")
        self.get_logger().info(f"📦 Loading policy from {policy_path}")
        self.ort_session = ort.InferenceSession(policy_path)

        # Initialize observation vector (45)
        self.obs = np.zeros((1, 45), dtype=np.float32)
        self.prev_actions = np.zeros(12, dtype=np.float32)

        # Subscribe to joystick command_velocity
        self.create_subscription(Twist, '/command_velocity', self.cmd_vel_callback, 10)

        # Publisher for desired joint positions
        self.position_pub = self.create_publisher(Float64MultiArray, '/desired_position', 10)

        # Timer to run policy at 250Hz
        self.create_timer(0.004, self.run_policy)

    def cmd_vel_callback(self, msg: Twist):
        # Update velocity_commands (first 3 obs)
        self.obs[0, :3] = [msg.linear.x, msg.linear.y, msg.angular.z]
        self.get_logger().debug(f"🎮 cmd_vel: {self.obs[0, :3]}")

    def run_policy(self):
        # Fill last 12 obs with previous actions
        self.obs[0, -12:] = self.prev_actions

        # Run ONNX inference
        actions = self.ort_session.run(None, {'obs': self.obs})[0][0]
        self.prev_actions = actions  # Store for next step

        # Publish joint positions
        msg = Float64MultiArray()
        msg.data = actions.tolist()
        self.position_pub.publish(msg)

        self.get_logger().debug(f"⚡ Published actions: {msg.data}")

def main(args=None):
    rclpy.init(args=args)
    node = SlimPolicyNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
