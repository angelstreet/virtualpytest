#!/usr/bin/env python3
"""Setup script for VirtualPyTest Backend Core"""

from setuptools import setup, find_packages

with open("requirements.txt", "r") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#") and not line.startswith("../")]

setup(
    name="virtualpytest-backend-core",
    version="1.0.0",
    description="Backend core service for VirtualPyTest - device controllers and business logic",
    packages=find_packages(),
    install_requires=requirements,
    python_requires=">=3.8",
    author="VirtualPyTest Team",
    package_dir={"": "."},
    include_package_data=True,
) 