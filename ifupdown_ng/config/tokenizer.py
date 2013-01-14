"""
ifupdown_ng.config.tokenizer  -  interfaces(5) config file tokenization
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

from ifupdown_ng import parser
from ifupdown_ng import utils
from ifupdown_ng.commands import ARGS

class InterfacesFile(parser.FileParser):
	"""Parse an interfaces(5)-format file into single statements

	An iterator which yields individual statements from a file in the
	interfaces(5) format given a sequence of lines.

	This ignores blank lines and comments and removes backslash-newline
	line continuations, then splits the result into first-word and
	rest-of-line tokens.

	Attributes:
		continued_line: Partially accumulated line continuation
	"""

	def __init__(self, *args, **kwargs):
		super(InterfacesFile, self).__init__(*args, **kwargs)
		self.continued_line = None

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
				line = self._next_line().lstrip().rstrip('\n')
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
				self.warning("Trailing backslash at EOF")
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
			self.warning("Possible inline comment found")
			self.warning("Comments must be on separate lines")

		## Split on whitespace and return the statement
		fields = line.split(None, 1)
		if fields:
			return (fields[0], fields[1])
