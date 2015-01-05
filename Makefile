# Note: for these to work, you need to install my nose variant:
# pip install git+ssh://git@github.com/dplepage/nose
#
# It fixes a bug where --doctest-options won't recognize options defined by
# other plugins

PACKAGE = travesty

WITH_DOCTEST = --with-doctest --doctest-extension=rst
WITH_COVERAGE = --with-coverage --cover-branches --cover-inclusive --cover-erase --cover-package=${PACKAGE}
FILES = ${PACKAGE}/ tests/ README*.rst
VERSION_FIX = --with-doctest-ignore-unicode --doctest-options='+IGNORE_EXCEPTION_DETAIL,+IGNORE_UNICODE'


smoke27:
	nosetests-2.7 -x ${WITH_DOCTEST} ${FILES} ${VERSION_FIX}

smoke34:
	nosetests-3.4 -x ${WITH_DOCTEST} ${FILES} ${VERSION_FIX}

test27:
	nosetests-2.7 ${WITH_DOCTEST} ${WITH_COVERAGE} ${FILES} ${VERSION_FIX}

test34:
	nosetests-3.4 ${WITH_DOCTEST} ${WITH_COVERAGE} ${FILES} ${VERSION_FIX}

html27: test27
	coverage-2.7 html --include='${PACKAGE}/*'

html34: test34
	coverage-3.4 html --include='${PACKAGE}/*'

html: html27
smoke: smoke27 smoke34
test: test27 test34

flakes:
	pyflakes .
