"""
ifupdown_ng.logging  -  Logging and error message functions
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

import sys

from ifupdown_ng import args

total_errors = 0
total_warnings = 0

def fatal(message):
	"""Display a fatal error message and exit"""
	sys.stderr.write('FATAL: %s\n' % message)
	sys.exit(1)

def error(message):
	"""Display a nonfatal error message"""
	global total_errors
	sys.stderr.write('ERROR: %s\n' % message)
	total_errors += 1

def warn(message):
	"""Display a warning message"""
	global total_warnings
	sys.stderr.write('WARNING: %s\n' % message)
	total_warnings += 1

def notice(message):
	"""Display an important notification message"""
	sys.stderr.write('NOTICE: %s\n' % message)

def info(message):
	"""Display an informational message"""
	sys.stderr.write('INFO: %s\n' % message)

def debug(message):
	"""Display a debug message if --verbose was passed"""
	if args.verbose:
		sys.stderr.write('DEBUG: %s\n' % message)
