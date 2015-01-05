#!/usr/bin/env python

from distutils.core import setup

setup(
    name='travesty',
    version='0.1.1',
    license='BSD',
    author="Daniel Lepage",
    author_email="dplepage@gmail.com",
    packages=['travesty','travesty.cantrips', 'travesty.document'],
    long_description=open('README.rst').read(),
    url='https://github.com/dplepage/travesty',
    install_requires=[
        'vertigo'
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 2",
    ]
)