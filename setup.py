#!/usr/bin/env python

'''
Setup script for eopayment
'''

import distutils
import distutils.core
from glob import glob
from os.path import splitext, basename, join as pjoin
import os
import re
from unittest import TextTestRunner, TestLoader

class TestCommand(distutils.core.Command):
    user_options = [ ]

    def initialize_options(self):
        self._dir = os.getcwd()

    def finalize_options(self):
        pass

    def run(self):
        '''
        Finds all the tests modules in tests/, and runs them.
        '''
        testfiles = [ ]
        for t in glob(pjoin(self._dir, 'tests', '*.py')):
            if not t.endswith('__init__.py'):
                testfiles.append('.'.join(
                    ['tests', splitext(basename(t))[0]])
                )

        tests = TestLoader().loadTestsFromNames(testfiles)
        t = TextTestRunner(verbosity = 4)
        t.run(tests)

def get_version():
    text = file('eopayment/__init__.py').read()
    m = re.search("__version__ = ['\"](.*)['\"]", text)
    return m.group(1)

distutils.core.setup(name='eopayment',
        version=get_version(),
        license='GPLv3 or later',
        description='Common API to use all French online payment credit card processing services',
        long_description=
            "eopayment is a Python module to interface with French's bank credit card\n"
            "online payment services. Supported services are ATOS/SIP, SystemPay, and\n"
            "SPPLUS.",
        url='http://dev.entrouvert.org/projects/eopayment/',
        author="Entr'ouvert",
        author_email="info@entrouvert.com",
        maintainer="Benjamin Dauvergne",
        maintainer_email="bdauvergne@entrouvert.com",
        packages=['eopayment'],
        requires=[
            'pycrypto (>= 2.5)'
        ],
        cmdclass={'test': TestCommand})
