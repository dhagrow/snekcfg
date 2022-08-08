#!/usr/bin/env python

import os
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import snekcfg

BASE_DIR = os.path.dirname(__file__)
README_PATH = os.path.join(BASE_DIR, 'README.md')
DESCRIPTION = open(README_PATH).read()

setup(
    name='snekcfg',
    version=snekcfg.__version__,
    description='A minimalist wrapper for configparser.',
    long_description=DESCRIPTION,
    long_description_content_type='text/markdown',
    author=snekcfg.__author__,
    author_email='cymrow@gmail.com',
    url='https://github.com/dhagrow/snekcfg',
    py_modules=['snekcfg'],
    license=snekcfg.__license__,
    platforms='any',
    keywords=['config', 'configuration', 'configparser', 'options', 'settings'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Libraries',
        'Programming Language :: Python :: 3',
        ],
    )
