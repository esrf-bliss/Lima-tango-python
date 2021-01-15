#!/usr/bin/env python

from setuptools import setup

packages = [
    'Lima.Server',
    'Lima.Server.plugins',
    'Lima.Server.camera'
]

console_scripts_entry_points = [
    "LimaCCDs = Lima.Server.LimaCCDs:main",
    "LimaViewer = Lima.Server.LimaViewer:main",
]

setup(name='Lima.Server',
    version='1.9.6',
    description='Python server for Lima cameras',
    url='https://gitlab.esrf.fr/limagroup/Lima-tango-python',
    packages=packages,
    entry_points={"console_scripts": console_scripts_entry_points},
)
