from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    # Locate shared package directories
    pd_pkg_share = FindPackageShare('pd_controller_pkg')
    teleop_pkg_share = FindPackageShare('teleop_twist_joy')
    biped_pkg_share = FindPackageShare('berkeley_biped_pkg')

    # Declare launch arguments
    return LaunchDescription([
        DeclareLaunchArgument(
            'pd_config',
            default_value=[pd_pkg_share, '/config/pd_config.yaml'],
            description='Path to the PD controller parameter file'
        ),


        # 📝 Launch argument for teleop_twist_joy config
        DeclareLaunchArgument(
            'teleop_config',
            #default_value=os.path.join(
            #    FindPackageShare('teleop_twist_joy').perform(None),
            #    'config', 'ps3.config.yaml'  # Or xbox.config.yaml if using Xbox controller
            #),
            default_value=[teleop_pkg_share, '/config/shanwan.config.yaml'],
            description='Path to teleop_twist_joy YAML config'
        ),

        # 🕹️ Launch the joystick node
        Node(
            package='joy',
            executable='joy_node',
            name='joy_node',
            output='screen'
        ),
        
        # 🎮 teleop_twist_joy (joystick → velocity commands)
        Node(
            package='teleop_twist_joy',
            executable='teleop_node',
            name='teleop_twist_joy_node',
            output='screen',
            #parameters=[teleop_config],
            parameters=[LaunchConfiguration('teleop_config')],
            remappings=[('/cmd_vel', '/command_velocity')],


        ),
        # 🤖 Launch the main biped node
        Node(
            package='berkeley_biped_pkg',
            executable='berkeley_biped_node',
            name='berkeley_biped_node',
            output='screen'
        ),
        
        Node(
            package='joystick_bridge',
            executable='cmd_vel_to_file',
            name='cmd_vel_to_file_node',
            output='screen'
        ),
        # 🧠 Launch the PD controller with parameters
        #Node(
        #    package='pd_controller_pkg',
        #    executable='pd_controller_node',
        #    name='pd_controller_node',
        #    output='screen',
        #    parameters=[LaunchConfiguration('pd_config')]
        #)
    ])
