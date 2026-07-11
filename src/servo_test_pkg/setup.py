from setuptools import setup

package_name = 'servo_test_pkg'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/servo_test.launch.py']),
        ('share/' + package_name + '/config', ['config/servo_poses.yaml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='scott',
    maintainer_email='scott@example.com',
    description='Servo test package for biped robot',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'servo_test_node = servo_test_pkg.servo_test_node:main',
        ],
    },
)