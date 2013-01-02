#! /usr/bin/env python

import os.path
import sys

## Check against our required python version
if sys.version_info < (2, 7, 0):
	sys.stderr.write('ifupdown-ng requires Python 2.7 or newer\n')
	sys.exit(255)

## Load version information from the same place everything else gets it
from ifupdown_ng.autogen import version

from setuptools import setup, find_packages
setup(
	name='ifupdown-ng',
	description='Next-generation network interface configuration tool',
	url='http://github.com/kmoffett/ifupdown-ng',
	author='Kyle Moffett',
	author_email='kyle@moffetthome.net',
	license='GPLv2',

	version=version.VERSION,
	packages=find_packages(exclude=['ifupdown_ng.tests']),
	scripts=['ifupdown-ng'],
	test_suite='ifupdown_ng.tests',
)
