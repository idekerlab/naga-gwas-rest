#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

import os
import re
from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

with open(os.path.join('nbgwas_rest', '__init__.py')) as ver_file:
    for line in ver_file:
        if line.startswith('__version__'):
            version=re.sub("'", "", line[line.index("'"):])

requirements = [
    'argparse',
    'networkx==1.11', #ndex2 requires networks 1.11
    'ndex2==3.0.0a1',
    'naga-gwas==0.4.1',
    'numpy',
    'flask',
    'flask-restplus',
    'python-daemon'
]

setup_requirements = [ ]

test_requirements = [
    'argparse',
    'networkx==1.11', #ndex2 requires networks 1.11
    'ndex2==3.0.0a1',
    'flask',
    'flask-restplus',
    'unittest2'
]

setup(
    author="Chris Churas",
    author_email='churas.camera@gmail.com',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description="REST service for Network Assisted Genomic Analysis (NAGA)",
    install_requires=requirements,
    license="BSD license",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='naga-gwas-rest',
    name='naga-gwas-rest',
    packages=find_packages(include=['nbgwas_rest']),
    scripts=['nbgwas_rest/naga_taskrunner.py'],
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/idekerlab/naga-gwas-rest',
    version=version,
    zip_safe=False,
)
