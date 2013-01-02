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
import sys

from ifupdown_ng import args
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
		try:
			line = next(self.lines).lstrip().rstrip('\n')
			self.line_nr += 1
		except StopIteration:
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

	def _parse_option(self, ifile, first, rest):
		if first == 'script':
			if self.script:
				ifile.error("Duplicate 'script' option")
			self.script = rest
		elif first == 'map':
			self.script_input.append(rest)
		else:
			ifile.error("Invalid 'mapping' option: %s" % first)

		return self

	def should_map(self, config_name):
		for pattern in self.matches:
			if fnmatch.fnmatchcase(config_name, pattern):
				return True
		return False

	def perform_mapping(self, config_name):
		raise NotImplementedError()


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

	def _parse_option(self, ifile, first, rest):
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

	def load_interfaces_file(self, ifile):
		assert isinstance(ifile, InterfacesFile)
		assert not self.ifile_stack

		self.ifile_stack.append(ifile)
		self._process_interfaces_files()

	def _process_interfaces_files(self):
		block = None
		while self.ifile_stack:
			ifile = self.ifile_stack[-1]
			try:
				first, rest = next(ifile)
			except StopIteration:
				self.ifile_stack.pop()
				self.total_nr_errors += ifile.nr_errors
				self.total_nr_warnings += ifile.nr_warnings
				continue

			parse_funcname = '_parse_%s' % first
			if hasattr(self, parse_funcname):
				parse_func = getattr(self, parse_funcname)
			elif first.startswith('allow-'):
			 	parse_func = self._parse_auto
				first = first[6:]
			elif block:
				parse_func = block._parse_option.__func__
			else:
				ifile.error("Option not in a valid block: %s"
						% first)
				continue

			block = parse_func(block, ifile, first, rest)

	def _parse_source(self, block, ifile, first, rest):
		block = None
		included_ifiles = []
		for path in libc.wordexp(rest, libc.WRDE_NOCMD):
			try:
				included_ifiles.append(InterfacesFile(path))
			except EnvironmentError as e:
				ifile.error('%s: %s' % (e.strerror, path))

		## Since this is a stack, put them in reverse order
		self.ifile_stack.extend(reversed(included_ifiles))

		return block

	def _parse_auto(self, block, ifile, first, rest):
		block = None
		interfaces = rest.split()
		if not self.ALLOWED_GROUP_NAME_RE.match(first):
			ifile.error('Invalid statement: allow-%s' % first)
			return block
		if not interfaces:
			ifile.error('Empty "allow-*" or "auto" statement')
			return block

		group = self.allowed.setdefault(first, set())
		for ifname in interfaces:
			if ifile.validate_interface_name(ifname):
				group.add(ifname)
		return block

	def _parse_mapping(self, block, ifile, first, rest):
		block = None
		matches = rest.split()
		if not matches:
			ifile.error('Empty mapping statement')
			return block

		block = Mapping(matches)
		self.mappings.append(block)
		return block

	def _parse_iface(self, block, ifile, first, rest):
		block = None
		params = rest.split()
		if len(params) != 3:
			ifile.error('Wrong number of parameters to "iface"')
			return block

		block = InterfaceConfig(*params)
		if block in self.configs:
			ifile.error('Duplicate iface: %s', ' '.join(params))
		else:
			self.configs[block] = block
		return block

