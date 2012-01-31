#!/usr/bin/env python

'''
Setup script for eopayment
'''

import distutils
import distutils.core
import re

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
        ])
