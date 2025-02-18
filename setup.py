# Copyright (C) 2018 Jurriaan Bremer.
# This file is part of Roach - https://github.com/jbremer/roach.
# See the file 'docs/LICENSE.txt' for copying permission.

from setuptools import setup

setup(
    name="roach",
    version="1.0",
    author="Jurriaan Bremer",
    author_email="jbr@cuckoo.sh",
    packages=[
        "roach",
    ],
    entry_points={
        "console_scripts": [
            "roach = roach.main:main",
        ],
    },
    url="https://github.com/jbremer/roach",
    license="GPLv3",
    description="Cockroach is your primitive & immortal swiss army knife",
    include_package_data=True,
    install_requires=[
        "click>=8.1.2",
        "cryptography>=36.0.2",
        "pefile>=2021.9.3",
        "pycrypto"
    ],
    extras_require={
        ":sys_platform == 'win32'": [
            "capstone-windows==3.0.4",
        ],
        ":sys_platform == 'darwin'": [
            "capstone==3.0.5",
        ],
        ":sys_platform == 'linux2'": [
            "capstone==3.0.5",
        ],
        ":sys_platform == 'linux'": [
            "capstone==3.0.5",
        ],
        "dev": [
            "pytest==4.4.1",
            "mock==2.0.0",
            "capstone==3.0.5",
        ]
    },
)
