PACKAGE = travesty

WITH_COVERAGE = --cov=${PACKAGE}
FILES = ${PACKAGE}/ tests/ README.md README2.rst

smoke:
	py.test -x ${FILES}

test:
	py.test ${WITH_COVERAGE} ${FILES}

html: test
	coverage html --include='${PACKAGE}/*'

flakes:
	pyflakes tests ${PACKAGE}
