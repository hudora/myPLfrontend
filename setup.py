#!/usr/bin/env python
# encoding: utf-8
"""myPLfrontend is xXXXx
"""

# setup.py
# Created by johan on 2009-10-29 for HUDORA.
# Copyright (c) 2009 HUDORA. All rights reserved.

__revision__ = '$Revision: 6862 $'

from setuptools import setup, find_packages

setup(name='myPLfrontend',
      maintainer='johan',
      # maintainer_email='xXXXx@hudora.de',
      version='1.0',
      description='xXXXx FILL IN HERE xXXXx',
      long_description=__doc__,
      classifiers=['License :: OSI Approved :: BSD License',
                   'Intended Audience :: Developers',
                   'Programming Language :: Python'],
      download_url='https://cybernetics.hudora.biz/nonpublic/eggs/',
      package_data={"myPLfrontend": ["templates/myPLfrontend/*.html", "reports/*.jrxml", "bin/*"]},
      packages=find_packages(),
      include_package_data=True,
      install_requires=['huTools', 'huDjango'],
      dependency_links = ['http://cybernetics.hudora.biz/dist/',
                          'http://cybernetics.hudora.biz/nonpublic/eggs/'],
)
