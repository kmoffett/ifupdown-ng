"""
ifupdown_ng.script  -  Helper script environment and execution
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

import functools
import os
import pwd
import re
import subprocess
import sys

from ifupdown_ng.autogen.config import DEFAULT_PATH
from ifupdown_ng.commands import ARGS

## Most user-specified locale settings are safe to preserve, but a few cause
## issues with shell scripts and need to be overridden.
##
## This is a practical compromise to prevent breaking various bits of text
## parsing while still allowing useful localized error messages.
_TERM_OVERRIDE = {
	'LC_ALL': None,
	'LC_COLLATE': 'C',
	'LC_CTYPE': 'C',
	'LC_NUMERIC': 'C',
}
_TERM_VARS = frozenset((
	'LANG',
	'LC_ADDRESS',
	'LC_ALL',
	'LC_COLLATE',
	'LC_CTYPE',
	'LC_IDENTIFICATION',
	'LC_MEASUREMENT',
	'LC_MESSAGES',
	'LC_MONETARY',
	'LC_NAME',
	'LC_NUMERIC',
	'LC_PAPER',
	'LC_TELEPHONE',
	'LC_TIME',
	'TERM',
	'TERMCAP',
))

def _getpwuid_safe():
	uid = os.getuid()
	try:
		return pwd.getpwuid(uid)
	except KeyError:
		return (str(uid), 'x', uid, os.getgid(), '', '/', '/bin/sh')


class Environment(object):
	def __init__(self, context=None, cwd=None, path=None, pwent=None,
			term_env=None):
		## Initialize internal values as empty
		self._env = dict()
		self._cwd = None
		self._pwent = None

		## Now apply the various parameters
		self.context = context
		self.cwd = cwd
		self.path = path
		self.pwent = pwent
		self.term_env = term_env

	@property
	def cwd(self):
		return self._cwd

	@cwd.setter
	def cwd(self, value):
		self._cwd = value
		if value is None:
			self._env['PWD'] = os.getcwd()
		else:
			self._env['PWD'] = value

	@property
	def path(self):
		return self._env['PATH']

	@path.setter
	def path(self, value):
		if value is None:
			self._env['PATH'] = DEFAULT_PATH
		else:
			self._env['PATH'] = value

	@property
	def pwent(self):
		return tuple(self._pwent)

	@pwent.setter
	def pwent(self, pwent):
		if pwent is None:
			pwent = _getpwuid_safe()
		self._pwent = pwent
		self._env['LOGNAME']  = pwent[0]
		self._env['USER']     = pwent[0]
		self._env['USERNAME'] = pwent[0]
		self._env['HOME']     = pwent[5]
		self._env['SHELL']    = pwent[6]

	@property
	def term_env(self):
		result = {}
		for key, value in self._env:
			if key in _TERM_VARS:
				result[key] = value

	@term_env.setter
	def term_env(self, env):
		if env is None:
			env = sys.environ

		## First clear out any existing terminal/locale variables
		for old_key in self._env:
			if old_key in _TERM_VARS:
				del self._env[old_key]

		## Then copy over the input settings
		for key, value in env.iteritems():
			if key in _TERM_VARS and key not in _TERM_OVERRIDE:
				self._env[key] = value

		## Finally, apply the overrides
		for key, value in _TERM_OVERRIDE:
			if value is not None:
				self._env[key] = value

	def __getitem__(self, key):
		if key in self._env:
			return self._env[key]
		elif self.context:
			return self.context[key]
		else:
			raise KeyError()

	def __iter__(self):
		for key in self._env:
			yield key
		if self.context:
			for key in self.context:
				if key not in self._env:
					yield key

	def iteritems(self):
		for key, value in self._env.iteritems():
			yield (key, value)
		if self.context:
			for key, value in self.context.iteritems():
				if key not in self._env:
					yield (key, value)

	## Wrap various methods in 'subprocess' for convenience
	def _wrap_subprocess_func(func):
		@functools.wraps(func)
		def method(self, *args, **kwargs):
			kwargs['cwd'] = self._cwd
			kwargs['env'] = self
			func(*args, **kwargs)
		return method
	call         = _wrap_subprocess_func(subprocess.call)
	check_call   = _wrap_subprocess_func(subprocess.check_call)
	check_output = _wrap_subprocess_func(subprocess.check_output)
	Popen        = _wrap_subprocess_func(subprocess.Popen)
	del _wrap_subprocess_func


class Context(object):
	_PHASE_TO_MODE = {
		'pre-up':   'start',
		'up':       'start',
		'down':      'stop',
		'post-down': 'stop',
	}

	def __init__(self, phase):
		self._getenv = {
			'PHASE': str(phase),
			'MODE': self._PHASE_TO_MODE[phase],
			'VERBOSITY': '1' if ARGS.verbose else '0',
		}

	def __contains__(self, var):
		return var in self._getenv

	def __getitem__(self, var):
		item = self._getenv[var]
		return item() if callable(item) else item

	def __iter__(self):
		for env in self._getenv:
			yield env

	def iteritems(self):
		for env, value in self._getenv.iteritems():
			if callable(value):
				value = value()
			yield (env, value)


class GlobalContext(Context):
	def __init__(self, phase, allow_group):
		super(GlobalContext, self).__init__(phase)
		self._getenv['IFACE'] = '--all'
		self._getenv['LOGICAL'] = allow_group
		self._getenv['ADDRFAM'] = 'meta'
		self._getenv['METHOD'] = 'none'


class ConfigContext(Context):
	VALID_OPTION_KEY_RE = re.compile(r'^([a-z][a-z0-9-]*)$')
	VALID_OPTION_ENV_RE = re.compile(r'^IF_([A-Z][A-Z0-9_]*)$')

	def __init__(self, phase, iface, config):
		super(ConfigContext, self).__init__(phase)
		self._config = config
		self._getenv['IFACE']   = iface
		self._getenv['LOGICAL'] = lambda: self._config.name
		self._getenv['ADDRFAM'] = lambda: self._config.address_family
		self._getenv['METHOD']  = lambda: self._config.method

	@classmethod
	def env_to_option(cls, env):
		## Make sure to use locale-independent case conversion
		key = unicode(key)

		match = cls.VALID_OPTION_ENV_RE.match(key)
		if not match:
			raise KeyError("Invalid option env: %s" % env)
		return key[3:].lower().replace('_', '-')

	@classmethod
	def option_to_env(cls, key):
		## Make sure to use locale-independent case conversion
		key = unicode(key)

		match = cls.VALID_OPTION_KEY_RE.match(key)
		if not match:
			raise KeyError("Invalid option key: %s" % key)
		return 'IF_%s' % key.upper().replace('-', '_')

	def __contains__(self, env):
		if super(ConfigContext, self).__contains__(env):
			return True

		try:
			option = self.env_to_option(env)
		except KeyError:
			return False
		return option in self._config.options

	def __getitem__(self, env):
		try:
			return super(ConfigContext, self).__getitem__(env)
		except KeyError:
			option = self.env_to_option(env)
			return self._config.options[option]

	def __iter__(self):
		for env in super(ConfigContext, self).__iter__():
			yield env

		for option in self._config.options:
			yield self.option_to_env(option)

	def iteritems(self):
		for env, value in super(ConfigContext, self).iteritems():
			yield (env, value)

		for option, value in self._config.options.iteritems():
			yield (self.option_to_env(option), value)
