from setuptools import setup, find_packages

setup(
    name="wopr-core",
    version="0.1.0",
    description="Core library for WOPR - Tactical Wargaming Adjudication Tracker",
    author="Bob",
    packages=find_packages(),
    install_requires=[
        # Minimal dependencies - consumers add what they need
    ],
    python_requires=">=3.11",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.11",
    ],
)