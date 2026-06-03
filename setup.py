# setup.py
from setuptools import find_packages, setup

setup(
    name="maya-ue5-environment-exporter",
    version="1.0.0",
    author="Your Name",
    description="A pipeline tool bridging Maya and UE5 for modular environment kits.",
    packages=find_packages(),  # Automatically finds the enviroment_exporter folder
    install_requires=[
        # List any external pip packages here.
        # (PySide6, Maya, and Unreal modules are assumed to be handled by the DCCs, so keep this blank for now)
    ],
    python_requires=">=3.7",
)
