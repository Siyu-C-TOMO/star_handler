from setuptools import setup, find_packages

setup(
    name="star_handler",
    version="2.0.0",
    author="Siyu Chen",
    description="A comprehensive toolkit for analyzing RELION STAR files",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.20.0",
        "pandas>=1.3.0",
        "matplotlib>=3.4.0",
        "scipy>=1.7.0",
        "starfile>=0.4.0",
        "requests>=2.25.0",
        "click>=8.0",
        "slack-bolt>=1.18.0"
    ],
    entry_points={
        "console_scripts": [
            "star-handler=star_handler.__main__:cli",
        ],
    },
)
