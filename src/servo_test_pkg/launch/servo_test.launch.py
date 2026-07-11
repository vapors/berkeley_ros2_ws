from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='servo_test_pkg',
            executable='servo_test_node',
            name='servo_test_node',
            output='screen',
            parameters=[{
                'pose_name': 'neutral'
            }]
        )
    ])
