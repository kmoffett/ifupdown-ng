import argparse

from ifupdown_ng import args
from ifupdown_ng.commands import common

class IfQueryCommandHandler(common.CommonCommandHandler):
	_COMMANDS = {
		'ifquery': 'Display network interface configuration and state',
	}
	def __init__(self, command):
		## Initialize the parent class
		super(IfQueryCommandHandler, self).__init__(command,
			usage='%(prog)s [<options>] (--all | <iface>...)\n'
			'       %(prog)s --list')

		## Add the mode and interface list flags
		self.argp.add_argument('-l', '--list', action='store_true',
			help='List all matching known interfaces')

		self.argp.add_argument('-a', '--all', action='store_true',
			help='Display all interfaces marked "auto"')

		self.argp.add_argument('iface', type=str, nargs='*',
			help=argparse.SUPPRESS)

	def execute(self):
		args.no_act = True
		print "BLARG QUERY ME HARDER"
