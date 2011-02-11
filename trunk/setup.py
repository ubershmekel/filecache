try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import os.path
import sys

import filecache
DOCUMENTATION = filecache.__doc__

VERSION = '0.62'

# generate .rst file with documentation
#open(os.path.join(os.path.dirname(__file__), 'documentation.rst'), 'w').write(DOCUMENTATION)

setup(
	name='filecache',
	packages=['filecache'],
	version=VERSION,
	author='ubershmekel',
	author_email='ubershmekel@gmail.com',
	url='http://code.google.com/p/filecache/',
	description='Persistent caching decorator',
	long_description=DOCUMENTATION,
	classifiers=[
		'Development Status :: 4 - Beta',
		'Intended Audience :: Developers',
		'License :: OSI Approved :: BSD License',
		'Operating System :: OS Independent',
		'Programming Language :: Python :: 2',
		'Programming Language :: Python :: 3',
		'Topic :: Utilities',
        'Topic :: Software Development :: Libraries :: Python Modules',
	]
)
