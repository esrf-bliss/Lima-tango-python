#!/usr/bin/env python

from setuptools import setup

packages = [
    'lima.server',
    'lima.server.plugins',
    'lima.server.camera'
]

console_scripts_entry_points = [
    "LimaCCDs = lima.server.LimaCCDs:main",
    "LimaViewer = lima.server.LimaViewer:main",
]

setup(name='lima-tango-server',
    description='Python server for Lima cameras',
    url='https://gitlab.esrf.fr/limagroup/Lima-tango-python',
    packages=packages,
    entry_points={"console_scripts": console_scripts_entry_points},

    # For compatibility with older pip
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
)
