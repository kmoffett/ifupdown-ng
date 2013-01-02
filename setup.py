#! /usr/bin/env python

import os.path
import sys

## Load version information from the same place everything else gets it
from ifupdown_ng.autogen import version

from setuptools import setup, find_packages
setup(
	name='ifupdown-ng',
	description='Next-generation network interface configuration tool',
	author='Kyle Moffett',
	author_email='kyle@moffetthome.net',
	license='GPLv2',

	version=version.VERSION,
	packages=find_packages(exclude=['ifupdown_ng.tests']),
	scripts=['ifupdown-ng'],
	test_suite='ifupdown_ng.tests',
)
