"""
ifupdown_ng.utils  -  Miscellaneous network interface helper functions
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

import re

###
## Define some helpers for operating on interface names
###

VALID_IFACE_NAME_RE = re.compile(r'^[A-Za-z0-9_-]+(:[A-Za-z0-9_-]+)?$')
def valid_interface_name(iface):
	"""Return True if an interface name is valid"""
	return bool(VALID_IFACE_NAME_RE.match(iface))

def interface_is_alias(iface):
	"""Return True if an interface name appears to be an alias"""
	return ':' in iface

def interface_device(iface):
	"""Return the physical device portion of an interface name"""
	return iface.split(':', 1)[0]
