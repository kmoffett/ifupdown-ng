"""
ifupdown_ng.commands.common  -  Common arguments for ifupdown-ng commands
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

import os.path

from ifupdown_ng import commands
from ifupdown_ng import config

## The base command-handler class from which all others are derived
class CommonCommandHandler(commands.CommandHandler):
	def __init__(self, command, **kwargs):
		## Initialize the superclass
		super(CommonCommandHandler, self).__init__(command, **kwargs)

		## Add common global options
		self.argp.add_argument('--allow', action='append', type=str,
			metavar='CLASS',
			help='Only process interfaces marked "allow-$CLASS"')

		self.argp.add_argument('-i', '--interfaces', type=str,
			default=config.INTERFACES_FILE,
			metavar='CONFIG-FILE',
			help='The interfaces(5) config file to load')

		self.argp.add_argument('-X', '--exclude', action='append',
			type=str, metavar='PATTERN',
			help='A glob pattern of interfaces to be ignored')

		self.argp.add_argument('-v', '--verbose', action='store_true',
			help='Print out what would happen before doing it')

		self.argp.add_argument('-o', '--option', action='append',
			type=str, metavar='OPTION=VALUE',
			help=('Set OPTION to VALUE as though in %s' %
				config.INTERFACES_FILE))

		self.argp.add_argument('--no-mappings', action='store_false',
			dest='mappings',
			help='Disable all mapping scripts')

		self.argp.add_argument('--no-scripts', action='store_false',
			dest='scripts',
			help=('Disable all hooks (in %s)' %
				os.path.join(config.CONFIG_DIR, 'if-*.d')))

	def execute(self):
		## Must be implemented by a subclass
		raise NotImplementedError()
