import urlparse
import string
import subprocess
from decimal import Decimal
import logging
import os
import os.path

from common import PaymentCommon, HTML

'''
Payment backend module for the ATOS/SIPS system used by many Frenck banks.

It use the middleware given by the bank.

The necessary options are:

 - pathfile, to indicate the absolute path of the pathfile file given by the
   bank,
 - binpath, the path of the directory containing the request and response
   executables,

All the other needed parameters SHOULD already be set in the parmcom files
contained in the middleware distribution file.

'''

__all__ = [ 'Payment' ]

BINPATH  = 'binpath'
PATHFILE = 'pathfile'
REQUEST_VALID_PARAMS = ['merchant_id', 'merchant_country', 'amount',
    'currency_code', 'pathfile', 'normal_return_url', 'cancel_return_url',
    'automatic_response_url', 'language', 'payment_means', 'header_flag',
    'capture_day', 'capture_mode', 'bgcolor', 'block_align', 'block_order',
    'textcolor', 'receipt_complement', 'caddie', 'customer_id', 'customer_email',
    'customer_ip_address', 'data', 'return_context', 'target', 'order_id']
DATA = 'DATA'
PARAMS = 'params'

TRANSACTION_ID = 'transaction_id'
MERCHANT_ID = 'merchant_id'
RESPONSE_CODE = 'response_code'

DEFAULT_PARAMS = { 'merchant_id': '014213245611111',
        'merchant_country': 'fr',
        'currency_code': '978' }

LOGGER = logging.getLogger(__name__)

class Payment(PaymentCommon):
    def __init__(self, options):
        self.options = options
        LOGGER.debug('initializing sips payment class with %s' % options)

    def execute(self, executable, params):
        if PATHFILE in self.options:
            params[PATHFILE] = self.options[PATHFILE]
        executable = os.path.join(self.options[BINPATH], executable)
        args = [executable] + [ "%s=%s" % p for p in params.iteritems() ]
        LOGGER.debug('executing %s' % args)
        result, _ = subprocess.Popen(args, executable=executable,
                stdout=subprocess.PIPE, shell=True).communicate()
        result = result.split('!')
        LOGGER.debug('got response %s' % result)
        return result

    def get_request_params(self):
        params = DEFAULT_PARAMS.copy()
        params.update(self.options.get(PARAMS, {}))
        return params

    def request(self, amount, email=None, next_url=None):
        params = self.get_request_params()
        transaction_id = self.transaction_id(6, string.digits, 'sips',
                params[MERCHANT_ID])
        params[TRANSACTION_ID] = transaction_id
        params['amount'] = str(Decimal(amount)*100)
        if email:
            params['customer_email'] = email
        if next_url:
            params['normal_return_url'] = next_url
        code, error, form = self.execute('request', params)
        if int(code) == 0:
            return transaction_id, HTML, form
        else:
            raise RuntimeError('sips/request returned -1: %s' % error)

    def response(self, query_string):
        form = urlparse.parse_qs(query_string)
        params = {'message': form[DATA]}
        result = self.execute('response', params)
        d = dict([p.split('=',1) for p in result])
        LOGGER.debug('response contains fields %s' % d)
        return result.get(RESPONSE_CODE) == '00', form.get(TRANSACTION_ID), d
