"""
ifupdown_ng.parser  -  File parsing helpers
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

import logging

from ifupdown_ng import logfilter


## Each file parser gets a logger created with a unique name inside of this
## module's top-level logger.
LOGGER = logging.getLogger(__name__)

## Preferred format string for FileParser objects
DEFAULT_FORMAT_STRING = (
	'%(parser_file_name)s:%(parser_file_line)s: %(levelname)s: %(message)s'
)

## Default formatter/handler for new FileParser objects
DEFAULT_FORMATTER = logging.Formatter(fmt=DEFAULT_FORMAT_STRING)
DEFAULT_HANDLER = logging.StreamHandler()
DEFAULT_HANDLER.setFormatter(DEFAULT_FORMATTER)


class FilePosition(logging.LoggerAdapter):
	"""LoggerAdapter for injecting file-position data during file parsing

	This tracks a particular position in a file being parsed, allowing
	error messages to include this information for the user's benefit.

	It is intentionally lightweight so it can be cheaply copied.
	"""
	def __init__(self, file_parser, line_nr=0):
		super(FilePosition, self).__init__(file_parser.logger, {
			'parser_file_name': file_parser.filename,
			'parser_file_line': line_nr,
		})
		self.file_parser = file_parser

	def copy(self):
		"""Clone a FilePositionAdapater object"""
		return self.__class__(self.file_parser,
				self.extra['parser_file_line'])

	@property
	def filename(self):
		"""The name of the file being parsed"""
		return self.extra['parser_file_name']

	@property
	def line_nr(self):
		"""The current line of the file being parsed"""
		return self.extra['parser_file_line']

	def next_line(self):
		"""Move to the next line"""
		self.extra['parser_file_line'] += 1


class FileParser(object):
	"""State management for tracking the parsing of text files

	This is an abstract superclass that should be inherited from in order
	to implement a text-file parser with helpful logging.  It provides a
	convenient interface for opening the file and tracking which line you
	are on for useful error messages.

	Attributes:
		filename: The name of the file being parsed
		lines: Iterator yielding a sequence of lines
		autoclose: Automatically call 'lines.close()' when exhausted?
		_log_total: The LogCountFilter for this file's Logger
		logger: The Logger object for the parsing of this file
		pos: The FilePosition object tracking the current line
	"""
	_NEXT_LOGGER_ID = 0
	@classmethod
	def _new_logger(cls):
		res = LOGGER.getChild('FileParser.%d' % cls._NEXT_LOGGER_ID)
		cls._NEXT_LOGGER_ID += 1
		return res

	def __new__(cls, filename, lines=None, autoclose=False,
			handler=DEFAULT_HANDLER):
		"""Allocate a new FileParser

		This saves the constructor arguments for later setup by
		the __init__() function (which ignore its arguments).

		Additionally, the logger is created with a name unique to
		this python instance.

		See FileParser.__init__ for more details

		Arguments:
			filename: Path to the interfaces(5) file
			lines: Optional iterator yielding a sequence of lines
			autoclose: Boolean indicating to call 'lines.close()'
				when the 'lines' iterator is exhausted.  This
				will always be "True" if lines is unset.
			handler: Default log handler for parse errors and
				warnings.  Defaults to go to stderr.
		"""
		self = super(FileParser, cls).__new__(cls)
		self.logger = self._new_logger()
		self.logger.addHandler(handler)
		self.logger.propagate = False

		## Set up variables first so __del__ can run even if an
		## exception occurs in the open() call inside __init__.
		self.filename = filename
		self.lines = lines
		self.autoclose = autoclose
		self.pos = FilePosition(self)
		return self

	def __init__(self, *_unused_args, **_unused_kwargs):
		"""Initialze an FileParser from a given file

		If the 'lines' iterator argument was not specified to __new__,
		then the file specified by 'filename' will be automatically
		opened for read access with universal newlines enabled.

		Raises:
		    OSError: If 'lines' is unspecified and 'open()' fails
		    IOError: If 'lines' is unspecified and 'open()' fails
		"""
		## Keep track of how many errors/warnings we've seen
		self._log_total = logfilter.LogCount()
		self.logger.addFilter(self._log_total)

		## If all we got was a filename then open the input file
		if self.lines is None:
			self.autoclose = True
			self.lines = open(self.filename, 'rU')

	def __del__(self):
		"""Release resources held by this object"""
		if self.autoclose and self.lines is not None:
			self.lines.close()
		self.lines = None

	def _next_line(self):
		result = next(self.lines)
		self.pos.next_line()
		return result

	def reset_error_counters(self):
		elf._log_total.reset_nr_logs()

	@property
	def nr_errors(self):
		return self._log_total.nr_logs_above(logging.ERROR)

	@property
	def nr_warnings(self):
		return self._log_total.nr_logs(logging.WARNING)


	###
	## Define some simple convenience wrappers around the FilePosition
	## logging methods.
	###
	def debug(self, *args, **kwargs):
		return self.pos.debug(*args, **kwargs)

	def info(self, *args, **kwargs):
		return self.pos.info(*args, **kwargs)

	def warning(self, *args, **kwargs):
		return self.pos.warning(*args, **kwargs)

	def error(self, *args, **kwargs):
		return self.pos.error(*args, **kwargs)

	def critical(self, *args, **kwargs):
		return self.pos.critical(*args, **kwargs)
