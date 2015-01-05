PACKAGE = travesty

WITH_DOCTEST = --with-doctest --doctest-extension=rst
WITH_COVERAGE = --with-coverage --cover-branches --cover-inclusive --cover-erase --cover-package=${PACKAGE}
FILES = ${PACKAGE}/ tests/ README*.rst
# Flags to make doctests work in python 2.X and python 3.X
VERSION_FIX = --with-doctest-ignore-unicode --doctest-options='+IGNORE_EXCEPTION_DETAIL,+IGNORE_UNICODE'

# Override to test a specific version, e.g. nosetests-2.7
NOSETESTS?=nosetests
COVERAGE?=coverage

smoke:
	${NOSETESTS} -x ${WITH_DOCTEST} ${FILES} ${VERSION_FIX}

test:
	${NOSETESTS} ${WITH_DOCTEST} ${WITH_COVERAGE} ${FILES} ${VERSION_FIX}

html: test
	${COVERAGE} html --include='${PACKAGE}/*'

flakes:
	pyflakes .
