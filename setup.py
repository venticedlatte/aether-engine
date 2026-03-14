from setuptools import setup, find_packages

setup(
    name="aether",
    version="0.1.0",
    description="Coupled multiphysics engine for photonic ICs under extreme environments",
    author="Plover Studios",
    python_requires=">=3.9",
    packages=find_packages(),
    install_requires=["numpy>=1.21", "scipy>=1.7"],
    entry_points={"console_scripts": ["aether=aether.cli:main"]},
)
