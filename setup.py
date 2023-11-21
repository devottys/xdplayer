#!/usr/bin/env python3

from setuptools import setup

__version__ = '1.0'

setup(name='xdplayer',
      version=__version__,
      description='play crosswords in the terminal',
      python_requires='>=3.8',
      scripts=['bin/xdplayer'],
      py_modules=['xdplayer'],
      package_data={'xdplayer': ['ddw/completed.ddw']},
      include_package_data=True,
      packages=['xdplayer'])
