from setuptools import setup, find_packages

setup(
    name='pyleary',
    version='0.1.0',
    packages=find_packages(),
    description='A simple Python package for my personal use',
    author='Matt Leary',
    url='https://github.com/mleary/pyleary',
    install_requires=['json', 'markdown', 'textwrap'],
)