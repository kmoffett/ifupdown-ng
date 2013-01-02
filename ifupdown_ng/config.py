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

import os
import re
import subprocess
import sys

from ifupdown_ng import args
from ifupdown_ng import logging
from ifupdown_ng import utils
from ifupdown_ng.autogen.config import *

INTERFACES_FILE = os.path.join(CONFIG_DIR, 'interfaces')
def hook_dir(phase_name):
	return os.path.join(CONFIG_DIR, phase_name + '.d')

###
## InterfacesFile()  -  Parse an interfaces(5)-format file into statements
###
## Iterate over this object to parse a series of lines into discrete
## statements according to the interfaces(5) format.
##
## This ignores blank lines and comments and removes line continuations.
###
class InterfacesFile(object):
	def __init__(self, filename, lines=None):
		if lines is None:
			lines = open(filename, 'rU')

		self.filename = filename
		self.line_nr = 0
		self.lines = lines
		self.continued_line = None
		self.exhausted = False

		self.nr_errors = 0
		self.nr_warnings = 0

	def log(self, prefix, msg):
		sys.stderr.write("%s:%d: %s: %s\n" %
				(self.filename, self.line_nr, prefix, msg))

	def error(self, msg):
		self.nr_errors += 1
		self.log("error", msg)

	def warn(self, msg):
		self.nr_warnings += 1
		self.log("warning", msg)

	def validate_interface_name(self, ifname):
		if utils.valid_interface_name(ifname):
			return True

		self.error('Invalid interface name: %s' % ifname)
		return False

	## This object is its own iterator
	def __iter__(self):
		return self

	## Returns (first_word, rest_of_line) for each statement
	def next(self):
		result = None
		while result is None:
			result = self._handle_one_line()
		return result

	def _handle_one_line(self):
		if self.exhausted:
			raise StopIteration()

		try:
			try:
				line = next(self.lines).lstrip().rstrip('\n')
				self.line_nr += 1
			except EnvironmentError as e:
				self.error('Read error: %s' % e.strerror)
				raise StopIteration()
		except StopIteration:
			self.exhausted = True
			if self.continued_line is None:
				raise
			else:
				self.warn("Trailing backslash at EOF")
				line = ''

		if self.continued_line is not None:
			line = self.continued_line + ' ' + line
		elif line.startswith('#'):
			return None

		if line.endswith('\\') and not line.endswith('\\\\'):
			self.continued_line = line[0:-1].rstrip()
			return None

		self.continued_line = None
		if '#' in line:
			self.warn("Possible inline comment found")
			self.warn("Comments must be on separate lines")

		## Split on whitespace and return the statement
		fields = line.split(None, 1)
		if fields:
			return (fields[0], fields[1])


###
## Mapping()  -  Object representing an interface mapping script
###
## Members:
##   matches:       Set of all interface patterns to be mapped by this stanza
##   script:        Path to the script to actually perform the mapping
##   script_input:  Lines of input for the mapping script (without '\n')
###
class Mapping(object):
	def __init__(self, matches):
		self.matches = set(matches)
		self.script = None
		self.script_input = []

	def _parse_script(self, ifile, first, rest):
		if self.script:
			ifile.error("Duplicate 'script' option")
		self.script = rest
		return self

	def _parse_map(self, ifile, first, rest):
		self.script_input.append(rest + '\n')
		return self

	def _close_parsing(self, ifile):
		if not self.script:
			ifile.error("No 'script' option was specified")

	def should_map(self, config_name):
		for pattern in self.matches:
			if fnmatch.fnmatchcase(config_name, pattern):
				return True
		return False

	def perform_mapping(self, ifname):
		## FIXME(knuq): Set up and pass 'env='
		proc = subprocess.Popen((self.script, ifname),
				stdin=subprocess.PIPE,
				stdout=subprocess.PIPE)
		output = proc.communicate(input=''.join(self.script_input))

		## Ensure the mapping script completed successfully
		if proc.returncode < 0:
			logging.warn('Mapping script died with signal %d'
					% -proc.returncode)
			return None
		if proc.returncode > 0:
			logging.debug('Mapping script exited with code %d'
					% proc.returncode)
			return None
		if output[0] is None:
			logging.warn('Mapping script succeeded with no output')
			return None

		## Check that it produced a valid interface config name
		config_name = output[0].split('\n')[0]
		if utils.valid_interface_name(config_name):
			return ifname

		logging.error('Mapped %s to invalid interface config name: %s'
				% (ifname, config_name))
		return None


###
## InterfaceConfig()  -  Object representing an interface configuration
###
## Members:
##   blah: blah
###
class InterfaceConfig(object):
	## Certain options are multivalued, so we iterate over them specially
	MULTIVALUE_OPTIONS = frozenset(('pre-up', 'up', 'down', 'post-down'))
	VALID_OPTION_RE = re.compile(r'^([a-z][a-z0-9-]*)$')
	LEGACY_OPTION_SYNONYMS = {
		'post-up': 'up',
		'pre-down': 'down',
	}

	def __init__(self, config_name, address_family, method):
		self.name = config_name
		self.address_family = address_family #_data[address_family]
		self.method = method #_data[method]

		self.automatic = True
		self.options = dict()

	def __hash__(self):
		return hash((self.name, self.address_family, self.method))

	def __eq__(self, other):
		return other == (self.name, self.address_family, self.method)

	def _option_parse(self, ifile, first, rest):
		if not rest:
			ifile.warn('Option is empty: %s' % first)

		if first in self.LEGACY_OPTION_SYNONYMS:
			ifile.warn('Option "%s" is deprecated, please use'
					' "%s" instead' % (first,
					self.LEGACY_OPTION_SYNONYMS[first]))
			first = self.LEGACY_OPTION_SYNONYMS[first]

		if first in self.MULTIVALUE_OPTIONS:
			self.options.setdefault(first, []).append(rest)
		elif first not in self.options:
			self.options[first] = rest
		else:
			ifile.error('Duplicate option: %s' % first)
		return self

	def _close_parsing(self, ifile):
		## FIXME: Add validation here
		pass

	def __iter__(self):
		return self.options.__iter__()

	def iteritems(self):
		for option in self.options:
			yield (option, self[option])

	def __getitem__(self, option):
		assert self.VALID_OPTIONS_RE.match(option)
		value = self.options[option]
		if option in self.MULTIVALUED_OPTIONS:
			assert isinstance(value, list)
		else:
			assert isinstance(value, basestring)
		return value

	def __setitem__(self, option, value):
		parse = self.VALID_OPTIONS_RE.match(option)
		assert parse
		assert isinstance(value, basestring)

		override_ok = not parse.group(2)
		option = parse.group(1)

		if option in self.MULTIVALUED_OPTIONS:
			self.options.setdefault(option, []).append(value)
		elif option not in self.options or override_ok:
			self.options[option] = value


###
## SystemConfig()  -  Load and operate on an interfaces(5) file.
###
## Members:
##   allowed: Dict mapping from an allow-group name to a set of interfaces
##   configs: Dict mapping from a named interface config to its data
##   mappings: ???
##
##   ifile_stack: The current stack of interfaces(5) files being parsed
##   total_nr_errors: The total number of errors from all loaded files
##   total_nr_warnings: The total number of warnings from all loaded files
###
class SystemConfig(object):
	ALLOWED_GROUP_NAME_RE = re.compile(r'^[a-z]+$')

	def __init__(self):
		self.allowed = dict()
		self.configs = dict()
		self.mappings = dict()
		self.ifile_stack = []
		self.total_nr_errors = 0
		self.total_nr_warnings = 0

	def clear(self):
		self.allowed.clear()
		self.configs.clear()
		self.mappings.clear()
		self.ifile_stack.clear()
		self.total_nr_errors = 0
		self.total_nr_warnings = 0

	def log_total_errors(self, warn=logging.warn, error=logging.error):
		if self.total_nr_errors:
			error('Broken config: %d errors and %d warnings' % (
					self.total_nr_errors,
					self.total_nr_warnings))
			return True
		elif self.total_nr_warnings:
			warn('Unsafe config: %d warnings' %
					self.total_nr_warnings)
			return False
		else:
			return None

	def load_interfaces_file(self, ifile=None):
		assert not self.ifile_stack

		## Make sure we have an open interfaces file
		if ifile is None:
			ifile = args.interfaces
		if not isinstance(ifile, InterfacesFile):
			try:
				ifile = InterfacesFile(ifile)
			except EnvironmentError as e:
				logging.error('%s: %s' % (e.strerror, ifile))
				self.total_nr_errors += 1
				return self

		self.ifile_stack.append(ifile)
		self._process_interfaces_files()
		return self

	def _process_interfaces_files(self):
		stanza = self
		while self.ifile_stack:
			ifile = self.ifile_stack[-1]
			try:
				first, rest = next(ifile)
			except StopIteration:
				self.ifile_stack.pop()
				self.total_nr_errors += ifile.nr_errors
				self.total_nr_warnings += ifile.nr_warnings
				stanza._close_parsing(ifile)
				stanza = self
				continue

			if first.startswith('allow-'):
				parse_funcname = '_parse_auto'
			else:
				parse_funcname = '_parse_%s' % first

			if hasattr(self, parse_funcname):
				stanza._close_parsing(ifile)
				stanza = self

			if hasattr(stanza, parse_funcname):
				parse_func = getattr(stanza, parse_funcname)
			elif hasattr(stanza, '_option_parse'):
				parse_func = stanza._option_parse
			else:
				ifile.error('Invalid option in this stanza: %s'
						% first)
				continue

			stanza = parse_func(ifile, first, rest)

		stanza._close_parsing(ifile)

	def _close_parsing(self, ifile):
		pass

	def _parse_source(self, ifile, first, rest):
		included_ifiles = []
		for path in libc.wordexp(rest, libc.WRDE_NOCMD):
			try:
				included_ifiles.append(InterfacesFile(path))
			except EnvironmentError as e:
				ifile.error('%s: %s' % (e.strerror, path))

		## Since this is a stack, put them in reverse order
		self.ifile_stack.extend(reversed(included_ifiles))
		return self

	def _parse_auto(self, ifile, first, rest):
		if first.startswith('allow-'):
			group_name = first[6:]
		else:
			group_name = first

		interfaces = rest.split()
		if not self.ALLOWED_GROUP_NAME_RE.match(group_name):
			ifile.error('Invalid statement: %s' % first)
			return self
		if not interfaces:
			ifile.error('Empty "%s" statement' % first)
			return self

		group = self.allowed.setdefault(group_name, set())
		for ifname in interfaces:
			if ifile.validate_interface_name(ifname):
				group.add(ifname)
		return self

	def _parse_mapping(self, ifile, first, rest):
		matches = rest.split()
		if not matches:
			ifile.error('Empty mapping statement')
			return self

		stanza = Mapping(matches)
		self.mappings.append(stanza)
		return stanza

	def _parse_iface(self, ifile, first, rest):
		valid = True

		## Parse apart the parameters
		params = rest.split()
		if len(params) != 3:
			ifile.error('Wrong number of parameters to "iface"')
			valid = False

		config_name    = params.pop(0) if params else ''
		address_family = params.pop(0) if params else ''
		method         = params.pop(0) if params else ''

		if not ifile.validate_interface_name(config_name):
			valid = False

		stanza = InterfaceConfig(config_name, address_family, method)
		if stanza in self.configs:
			ifile.error('Duplicate iface: %s', ' '.join(params))
			valid = False

		if valid:
			self.configs[stanza] = stanza

		return stanza

	def _option_parse(self, ifile, first, rest):
		ifile.error("Option not in a valid stanza: %s" % first)
		return self
