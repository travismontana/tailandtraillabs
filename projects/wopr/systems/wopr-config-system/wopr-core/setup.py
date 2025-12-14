from setuptools import setup, find_packages

setup(
    name="wopr-core",
    version="0.1.0",
    description="Core library for WOPR - Tactical Wargaming Adjudication Tracker",
    author="Bob",
    author_email="bob@example.com",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
        "pyyaml>=6.0",
    ],
    python_requires=">=3.11",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
