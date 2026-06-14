from setuptools import setup, find_packages

setup(
    name="onion-compress",
    version="0.1.0",
    description="Onion — Adaptive Layered Compression Engine",
    author="A. Hill",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "cryptography>=41.0",
    ],
    entry_points={
        "console_scripts": [
            "onion=ace.cli:main",
        ],
    },
)
