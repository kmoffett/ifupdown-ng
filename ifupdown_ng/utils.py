###
## Define some helpers for operating on interface names
###

import re

VALID_IFACE_NAME_RE = re.compile(r'^[A-Za-z0-9_-]+(:[A-Za-z0-9_-]+)?$')
def valid_interface_name(iface):
	return bool(VALID_IFACE_NAME_RE.match(iface))

def interface_is_alias(iface):
	return ':' in iface

def interface_device(iface):
	return iface.split(':', 1)[0]
