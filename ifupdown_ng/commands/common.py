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
