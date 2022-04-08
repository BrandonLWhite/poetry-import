#!/usr/bin/env python

from setuptools import setup, find_packages

with open("requirements.txt") as infile:
    requires = list(map(lambda x: x.strip(), infile.readlines()))

setup_options = dict(
    name='some-test-lib',
    version='[SCM_VERSION]',
    description='Description goes here.',
    long_description='Long description goes here.',
    author='Some Services, Inc',
    url='https://github.com/some-services/some-test-lib',
    scripts=[],
    packages=find_packages(exclude=['tests*']),
    install_requires=requires)

setup(**setup_options)
