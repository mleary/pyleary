from pathlib import Path

from setuptools import find_packages, setup

HERE = Path(__file__).parent
README = HERE / "README.md"
LONG_DESCRIPTION = (
    README.read_text(encoding="utf-8") if README.exists() else "Minimal GitHub downloader."
)

setup(
    name="pyleary",
    version="0.0.1",
    description="Minimal GitHub downloader.",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    author="Matt Leary",
    url="https://github.com/mleary/pyleary",
    license="MIT",
    packages=find_packages(),
    install_requires=["requests>=2.31.0"],
    python_requires=">=3.12",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
    ],
)
