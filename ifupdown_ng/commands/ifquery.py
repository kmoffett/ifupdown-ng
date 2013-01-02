###
## ifupdown-ng  -  Next-generation network interface configuration tool
## Copyright (C) 2012-2013  Kyle Moffett <kyle@moffetthome.net>
##
## This program is free software; you can redistribute it and/or modify it
## under the terms of version 2 of the GNU General Public License, as
## published by the Free Software Foundation.
##
## This program is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
## or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
## for more details.
##
## You should have received a copy of the GNU General Public License along
## with this program; otherwise you can obtain it here:
##   http://www.gnu.org/licenses/gpl-2.0.txt
###

import argparse

from ifupdown_ng import args
from ifupdown_ng import config
from ifupdown_ng import logging
from ifupdown_ng.commands import common

class IfQueryCommandHandler(common.CommonCommandHandler):
	_COMMANDS = {
		'ifquery': 'Display network interface configuration and state',
	}
	def __init__(self, command):
		## Initialize the parent class
		super(IfQueryCommandHandler, self).__init__(command,
			usage='%(prog)s [<options>] <iface>...\n'
			'       %(prog)s [<options>] --list')

		## Add the mode and interface list flags
		self.argp.add_argument('-l', '--list', action='store_true',
			help='List all matching known interfaces')

		self.argp.add_argument('iface', type=str, nargs='*',
			help=argparse.SUPPRESS)

	def execute(self):
		## Do not run any commands in this mode
		args.no_act = True

		## Check for nonsensical option combinations
		if not args.list and not args.iface:
			self.argp.error('No interfaces specified in query')
		if args.list and args.iface:
			self.argp.error('Both --list and interfaces given')

		## Load the configuration
		sysconfig = config.SystemConfig()
		sysconfig.load_interfaces_file()
		sysconfig.log_total_errors(error=logging.fatal)

		## Figure out what to do based on arguments
		if args.list:
			print "FIXME: LIST INTERFACES"
		else:
			ifaces = ', '.join(args.iface)
			print "FIXME: QUERY INTERFACES: %s" % ifaces
