from setuptools import setup
import os
from glob import glob

package_name = 'berkeley_biped_pkg'


setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    data_files=[
    ('share/ament_index/resource_index/packages',
        ['resource/berkeley_biped_pkg']),
    ('share/berkeley_biped_pkg', ['package.xml']),
    ('share/berkeley_biped_pkg/launch', ['launch/berkeley_biped_launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Your Name',
    maintainer_email='you@example.com',
    description='Berkeley biped ROS2 control package with PD controller support',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'pd_controller_node = pd_controller_node:main',
        ],
    },

    extras_require={
        'cpu': ['onnxruntime'],
        'gpu': ['onnxruntime-gpu'],
    },
)
