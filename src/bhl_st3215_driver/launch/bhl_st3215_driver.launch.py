from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    package_share = FindPackageShare('bhl_st3215_driver')

    return LaunchDescription([
        DeclareLaunchArgument(
            'config',
            default_value=[package_share, '/config/servo_driver.yaml'],
            description='Driver ROS parameter YAML.',
        ),
        DeclareLaunchArgument(
            'servo_map',
            default_value=[package_share, '/config/servo_map.yaml'],
            description='Native ST3215 hardware map YAML.',
        ),
        DeclareLaunchArgument(
            'port',
            default_value='/dev/ttyS3',
            description='Orange Pi UART device.',
        ),
        DeclareLaunchArgument(
            'enable_writes',
            default_value='false',
            description='Enable physical 12-servo SyncWrite commands.',
        ),
        DeclareLaunchArgument(
            'default_pose_move_duration_sec',
            default_value='4.0',
            description='Duration of the guarded move to the training default pose.',
        ),
        Node(
            package='bhl_st3215_driver',
            executable='bhl_st3215_driver_node',
            name='bhl_st3215_driver',
            output='screen',
            parameters=[
                LaunchConfiguration('config'),
                {
                    'port': LaunchConfiguration('port'),
                    'joint_map_path': LaunchConfiguration('servo_map'),
                    'writes_enabled': ParameterValue(
                        LaunchConfiguration('enable_writes'), value_type=bool
                    ),
                    'default_pose_move_duration_sec': ParameterValue(
                        LaunchConfiguration('default_pose_move_duration_sec'), value_type=float
                    ),
                },
            ],
        ),
    ])
