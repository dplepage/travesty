#!/usr/bin/env python

from distutils.core import setup

setup(
    name='travesty',
    version='0.1.1',
    license='BSD',
    author="Daniel Lepage",
    author_email="dplepage@gmail.com",
    packages=['travesty','travesty.cantrips', 'travesty.document'],
    long_description="""
=======================================
 Travesty: Graph Traversal Dispatchers
=======================================

Travesty is a collection of tools for doing function dispatch based on a
graph.

A lot of these tools are specifically aimed at doing function dispatch based
on a type graph for some object type.

See README.rst for more info.

""",
    url='https://github.com/dplepage/travesty',
    install_requires=[
        'vertigo'
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 2",
    ]
)