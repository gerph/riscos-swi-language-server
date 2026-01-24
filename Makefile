##
# Makefile for RISCOS SWI language server
#
# Remove stale .pyc files:
#	- `make clean`
#
# Build a package:
#	- `make package`
#     Ensure that project.config is updated.
#
# Run simple tests (not currently implemented)
#	- `make tests`
#

VERSION = $(shell eval "$$(tools/ci-vars)" ; echo $$CI_BRANCH_VERSION | sed -E -e 's/\.([a-zA-Z])/+\1/')

clean:
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -delete

.PHONY: setup.py

package: setup.py
	rm -rf dist
	python setup.py sdist

setup.py: project.config setup.py.template
	sed 's/version = ".*"/version = "${VERSION}"/' setup.py.template > setup.py || ( rm setup.py ; false )
