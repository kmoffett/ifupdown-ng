import argparse

from ifupdown_ng.commands import common

class IfUpDownCommandHandler(common.CommonCommandHandler):
	_COMMANDS = {
		'ifup': 'Bring up network interfaces',
		'ifdown': 'Take down network interfaces',
	}
	def __init__(self, command):
		## Initialize the parent class
		super(IfUpDownCommandHandler, self).__init__(command,
			usage='%(prog)s [<options>] (--all | <iface>...)')

		## Add state-mutation options
		self.argp.add_argument('-n', '--no-act', action='store_false',
			dest='act',
			help='Display commands but do not run them '
				'(NOTE: Does not disable mapping scripts)')

		self.argp.add_argument('--force', action='store_true',
			help='Run commands even if already up/down')

		## Add the interface list flags
		self.argp.add_argument('iface', type=str, nargs='*',
			help=argparse.SUPPRESS)

		self.argp.add_argument('-a', '--all', action='store_true',
			help='Process all interfaces marked "auto"')

	def execute(self):
		print "BLARG UPDOWN ME HARDER"
