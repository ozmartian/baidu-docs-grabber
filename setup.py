#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#######################################################################
#
# baidu-grabber - convert and save Baidu Docs to PDF
#
# copyright © 2018 Pete Alexandrou
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#######################################################################

import os
import sys
from setuptools import setup

import baidugrabber


def get_deps():
    pyqt5_exists = False
    for syspath in sys.path:
        pyqt5_exists = os.path.exists(os.path.join(syspath, 'PyQt5'))
        if pyqt5_exists:
            break
    return ['PyQt5' if not pyqt5_exists else '']


setup(name=baidugrabber.__appname__,
      version=baidugrabber.__version__,
      author=baidugrabber.__author__,
      author_email=baidugrabber.__email__,
      description='Convert and save Baidu Docs to PDF',
      long_description='Convert and save documents from Baidu Docs (https://wenku.baidu.com) '
                       'to PDF for offline storage.',
      url=baidugrabber.__website__,
      license='GPLv3+',
      packages=['baidugrabber'],
      setup_requires=['setuptools'],
      install_requires=get_deps(),
      package_data={'baidugrabber': ['README.md', 'LICENSE']},
      entry_points={'gui_scripts': ['baidu-grabber = baidugrabber.__main__:main']},
      keywords='baidu-grabber baidu-docs baidu docs pdf',
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Environment :: MacOS X :: Cocoa',
          'Environment :: Win32 (MS Windows)',
          'Environment :: X11 Applications :: Qt',
          'Intended Audience :: End Users/Desktop',
          'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
          'Natural Language :: English',
          'Operating System :: OS Independent',
          'Topic :: Internet',
          'Programming Language :: Python :: 3 :: Only'
      ])
