#!/usr/bin/env python

'''
Setup script for eopayment
'''

import distutils
import distutils.core
import eopayment

distutils.core.setup(name='eopayment',
        version=eopayment.__version__,
        licence='GPLv3 or later',
        description='Common API to access online payment services',
        url='http://dev.entrouvert.org/projects/eopayment/',
        author="Entr'ouvert",
        auhtor_email="info@entrouvert.com",
        maintainer="Benjamin Dauvergne",
        maintainer_email="bdauvergne@entrouvert.com",
        packages=['eopayment'])
