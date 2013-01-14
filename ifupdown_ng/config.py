"""
ifupdown_ng.config  -  interfaces(5) configuration parsing and operation
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

import fnmatch
import logging
import os
import re
import subprocess
import sys

from ifupdown_ng import utils
from ifupdown_ng.autogen.config import *
from ifupdown_ng.commands import ARGS

logger = logging.getLogger(__name__)

INTERFACES_FILE = os.path.join(CONFIG_DIR, 'interfaces')
def hook_dir(phase_name):
	"""Compute the hook-script directory for a particular phase."""
	return os.path.join(CONFIG_DIR, phase_name + '.d')

class FilePosition(object):
	"""Store the current file name and line number for later log messages

	This is a simple wrapper class which allows the current filename and
	line number to be output in diagnostic messages long after the file
	has been closed.

	Attributes:
		filename: Path to the interfaces(5) file
		line_nr: Current line number
	"""
	__slots__ = ('filename', 'line_nr')

	def __init__(self, filename, line_nr=0):
		"""Initializes a FilePosition object"""
		self.filename = filename
		self.line_nr = line_nr

	def copy(self):
		"""Clone a FilePosition object"""
		return self.__class__(self.filename, self.line_nr)

	def next_line(self):
		"""Move to the next line"""
		self.line_nr += 1

	def log(self, prefix, msg):
		"""Log a message with the current filename and line-number"""
		sys.stderr.write("%s:%d: %s: %s\n" %
				(self.filename, self.line_nr, prefix, msg))

class InterfacesFile(object):
	"""Parse an interfaces(5)-format file into single statements

	An iterator which yields individual statements from a file in the
	interfaces(5) format given a sequence of lines.

	This ignores blank lines and comments and removes backslash-newline
	line continuations, then splits the result into first-word and
	rest-of-line tokens.

	Attributes:
		lines: Iterator yielding a sequence of interfaces(5) lines
		autoclose: Automatically call 'lines.close()' when exhausted
		pos: The FilePosition object tracking the current line
		continued_line: Partially accumulated line continuation
		nr_errors: The total number of errors found in this file
		nr_warnings: The total number of warnings found in this file
	"""

	def __init__(self, filename, lines=None, autoclose=False):
		"""Initialze an InterfacesFile from a given file

		If the 'lines' iterator argument is not specified, then the
		file specified by 'filename' will be automatically opened for
		read access with universal newlines enabled.

		Arguments:
			filename: Path to the interfaces(5) file
			lines: Optional iterator yielding a sequence of lines
			autoclose: Boolean indicating to call 'lines.close()'
				when the 'lines' iterator is exhausted.  This
				will always be "True" if lines is unset.

		Raises:
		    OSError: If 'lines' is unspecified and 'open()' fails
		    IOError: If 'lines' is unspecified and 'open()' fails
		"""
		## Set up variables first so __del__ can run even if an
		## exception occurs in the open() call.
		self.lines = lines
		self.pos = FilePosition(filename)
		self.autoclose = autoclose
		self.continued_line = None

		self.nr_errors = 0
		self.nr_warnings = 0

		if self.lines is None:
			self.autoclose = True
			self.lines = open(filename, 'rU')

	def error(self, msg, pos=None):
		"""Report an error in the file"""
		self.nr_errors += 1
		if pos is None:
			pos = self.pos
		pos.log("error", msg)

	def warn(self, msg, pos=None):
		"""Report a warning in the file"""
		self.nr_warnings += 1
		if pos is None:
			pos = self.pos
		pos.log("warning", msg)

	def validate_interface_name(self, ifname):
		"""Report an error if an interface name is not valid"""
		if utils.valid_interface_name(ifname):
			return True

		self.error('Invalid interface name: %s' % ifname)
		return False

	def __iter__(self):
		"""Iterate over this object (it is already an iterator)"""
		return self

	def next(self):
		"""Return the next statement as (first_word, rest_of_line)"""
		result = None
		while result is None:
			result = self._handle_one_line()
		return result

	def _handle_one_line(self):
		"""Parse a single line and maybe return a completed statement

		Raises:
			StopIteration: If the input is exhausted and no more
				statements are available for read.
		Returns:
			A completed statement as (first_word, rest_of_line)
			if one is available, otherwise returns None if more
			work remains to be done.
		"""
		if self.lines is None:
			raise StopIteration()

		try:
			try:
				line = next(self.lines).lstrip().rstrip('\n')
				self.pos.next_line()
			except EnvironmentError as ex:
				self.error('Read error: %s' % ex.strerror)
				raise StopIteration()
		except StopIteration:
			if self.autoclose:
				self.lines.close()
			self.lines = None

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

	def __del__(self):
		"""Release resources held by this object"""
		if self.autoclose and self.lines is not None:
			self.lines.close()
		self.lines = None


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

	def _parse_script(self, ifile, _first, rest):
		if self.script:
			ifile.error("Duplicate 'script' option")
		self.script = rest
		return self

	def _parse_map(self, _ifile, _first, rest):
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
		proc = subprocess.Popen((self.script, ifname),
				stdin=subprocess.PIPE,
				stdout=subprocess.PIPE)
		output = proc.communicate(input=''.join(self.script_input))

		## Ensure the mapping script completed successfully
		if proc.returncode < 0:
			logger.warning('Mapping script died with signal %d'
					% -proc.returncode)
			return None
		if proc.returncode > 0:
			logger.debug('Mapping script exited with code %d'
					% proc.returncode)
			return None
		if output[0] is None:
			logger.warning('Mapping script succeeded with no output')
			return None

		## Check that it produced a valid interface config name
		config_name = output[0].split('\n')[0]
		if utils.valid_interface_name(config_name):
			return ifname

		logger.error('Mapped %s to invalid interface config name: %s'
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
		assert self.VALID_OPTION_RE.match(option)
		value = self.options[option]
		if option in self.MULTIVALUE_OPTIONS:
			assert isinstance(value, list)
		else:
			assert isinstance(value, basestring)
		return value

	def __setitem__(self, option, value):
		parse = self.VALID_OPTION_RE.match(option)
		assert parse
		assert isinstance(value, basestring)

		override_ok = not parse.group(2)
		option = parse.group(1)

		if option in self.MULTIVALUE_OPTIONS:
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
		self.mappings = []
		self.ifile_stack = []
		self.total_nr_errors = 0
		self.total_nr_warnings = 0

	def clear(self):
		self.allowed.clear()
		self.configs.clear()
		del self.mappings[:]
		del self.ifile_stack[:]
		self.total_nr_errors = 0
		self.total_nr_warnings = 0

	def log_total_errors(self):
		if self.total_nr_errors:
			logger.error('Broken config: %d errors and %d warnings' % (
					self.total_nr_errors,
					self.total_nr_warnings))
			return True
		elif self.total_nr_warnings:
			logger.warning('Unsafe config: %d warnings' %
					self.total_nr_warnings)
			return False
		else:
			return None

	def load_interfaces_file(self, ifile=None):
		assert not self.ifile_stack

		## Make sure we have an open interfaces file
		if ifile is None:
			ifile = ARGS.interfaces
		if not isinstance(ifile, InterfacesFile):
			try:
				ifile = InterfacesFile(ifile)
			except EnvironmentError as ex:
				logger.error('%s: %s' % (ex.strerror, ifile))
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

	def _parse_source(self, ifile, _first, rest):
		included_ifiles = []
		for path in libc.wordexp(rest, libc.WRDE_NOCMD):
			try:
				included_ifiles.append(InterfacesFile(path))
			except EnvironmentError as ex:
				ifile.error('%s: %s' % (ex.strerror, path))

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

	def _parse_mapping(self, ifile, _first, rest):
		matches = rest.split()
		if not matches:
			ifile.error('Empty mapping statement')
			return self

		stanza = Mapping(matches)
		self.mappings.append(stanza)
		return stanza

	def _parse_iface(self, ifile, _first, rest):
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

	def _option_parse(self, ifile, first, _rest):
		ifile.error("Option not in a valid stanza: %s" % first)
		return self
