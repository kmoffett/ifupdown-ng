#! /usr/bin/env python
"""
setup.py  -  Python package setup script
Copyright (C) 2012-2013  Kyle Moffett <kyle@moffetthome.net>

This program is free software; you can redistribute it and/or modify it
under the terms of version 2 of the GNU General Public License, as
published by the Free Software Foundation.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
for more details.

You should have received a copy of the GNU General Public License along
with this program; otherwise you can obtain it here:
  http://www.gnu.org/licenses/gpl-2.0.txt
"""

## Futureproofing boilerplate
from __future__ import absolute_import

## Check against our required python version
import sys
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
