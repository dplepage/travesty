PACKAGE = travesty

WITH_COVERAGE = --cov=${PACKAGE}
FILES = ${PACKAGE}/ tests/ README*.rst

smoke27:
	py.test2.7 -x ${FILES}

smoke35:
	py.test3.5 -x ${FILES}

test27:
	py.test2.7 ${WITH_COVERAGE} ${FILES}

test35:
	py.test3.5 ${WITH_COVERAGE} ${FILES}

html27: test27
	coverage2.7 html --include='${PACKAGE}/*'

html35: test35
	coverage3.5 html --include='${PACKAGE}/*'

html: html27
smoke: smoke27 smoke35
test: test27 test35

flakes:
	pyflakes .
