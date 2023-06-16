#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Jeff Hammel <jhammel@openplans.org>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

from setuptools import setup, find_packages

version = '1.6.0'

setup(name='TracBackport',
      version=version,
      description="Support Legacy features for trac 1.6.",
      long_description="""Support Legacy features for trac 1.6.
                       """,
      classifiers=[],
      keywords='Trac backport legacy deprecated',
      author='Ivan Zakrevsky',
      author_email='ivzak@yandex.ru',
      url='https://github.com/emacsway/TracBackportPlugin',
      license='BSD 3-Clause',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      package_data={'trachours': ['templates/*', 'templates/genshi/*']},
      zip_safe=False,
      install_requires=['Trac', 'Genshi'],
      entry_points="""
      [trac.plugins]
      tracbackport = tracbackport
      """,
      )
