#!/usr/bin/env python
# encoding: utf-8
"""myPLfrontend is the frontend to the kernelE WMS
"""

# setup.py
# Created by j.otten@hudora.de on 2009-10-29 for HUDORA.
# Copyright (c) 2009 HUDORA. All rights reserved.

__revision__ = '$Revision: 6862 $'

from setuptools import setup, find_packages

setup(name='myPLfrontend',
      maintainer='j.otten@hudora.de',
      # maintainer_email='xXXXx@hudora.de',
      version='1.0p3',
      description='Web-Frontend to the kernelE WMS',
      long_description=__doc__,
      classifiers=['License :: OSI Approved :: BSD License',
                   'Intended Audience :: Developers',
                   'Programming Language :: Python'],
      download_url='https://cybernetics.hudora.biz/nonpublic/eggs/',
      package_data={"myPLfrontend": ["templates/myplfrontend/*.html", "reports/*.jrxml", "bin/*"]},
      packages=find_packages(),
      include_package_data=True,
      install_requires=['huTools', 'huDjango'],
      dependency_links = ['http://cybernetics.hudora.biz/dist/',
                          'http://cybernetics.hudora.biz/nonpublic/eggs/'],
)
