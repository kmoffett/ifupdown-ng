#! /bin/sh

cd "$(dirname "$0")"

## First run it on non-module scripts with a disabled module regex
pylint --rcfile=pylintrc --module-rgx='.*' "$@"	\
	ifupdown-ng				\
	setup.py

## Now run it on the module directory
pylint --rcfile=pylintrc "$@"			\
	ifupdown_ng/				\
