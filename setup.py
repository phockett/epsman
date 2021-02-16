# Quick testing for local installation.
# 14/12/20
#
# Minimal install from https://github.com/maet3608/minimal-setup-py/blob/master/setup.py
#
# See also D:\temp\epsmanHatch_141220\epsman for Hatch generated files
#
# And ubelt?

from setuptools import setup, find_packages

setup(
    name='epsman',
    version='0.0.1',
    url='https://github.com/phockett/epsman',
    author='Author Name',
    author_email='author@gmail.com',
    description='Description of my package',
    packages=find_packages(),
    install_requires=[]   # ['numpy >= 1.11.1', 'matplotlib >= 1.5.1'],
)
