"""
ifupdown_ng.logfilter  -  Log filtering helpers
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

class LogCount(logging.Filter):
	"""Logging Filter for counting messages of each log-level

	This filter objet keeps track of how many messages of each log-level
	have been processed by its attached logger object.

	Attributes:
		_nr_logs: Dict of message counts, indexed by level-nr
	"""
	def __init__(self):
		super(LogCount, self).__init__()
		self._nr_logs = dict()

	def clear_nr_logs(self):
		self._nr_logs.clear()

	def nr_logs(self, log_level_nr):
		return self._nr_logs.get(log_level_nr, 0)

	def nr_logs_above(self, log_level_nr):
		total = 0
		for lvl, nr_logs in self._nr_logs.iteritems():
			if lvl >= log_level_nr:
				total += nr_logs
		return total

	def filter(self, record):
		self._nr_logs.setdefault(record.levelno, 0)
		self._nr_logs[record.levelno] += 1
		return True
