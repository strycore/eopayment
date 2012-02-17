import os.path
import os
import random
import logging
from datetime import date

__all__ = [ 'PaymentCommon', 'URL', 'HTML', 'RANDOM' ]


LOGGER = logging.getLogger(__name__)
RANDOM = random.SystemRandom()

URL = 1
HTML = 2

class PaymentResponse(object):
    '''Holds a generic view on the result of payment transaction response.

       result -- holds the declarative result of the transaction, does not use
       it to validate the payment in your backoffice, it's just for informing
       the user that all is well.
       signed_result -- holds the signed result of the transaction, when it is
       not None, it contains the result of the transaction as asserted by the
       bank with an electronic signature.
       bank_data -- a dictionnary containing some data depending on the bank,
       you have to log it for audit purpose.
       return_content -- when handling a response in a callback endpoint, i.e.
       a response transmitted directly from the bank to the merchant website,
       you usually have to confirm good reception of the message by returning a
       properly formatted response, this is it.
       bank_status -- if result is False, it contains the reason
       order_id -- the id given by the merchant in the payment request
       transaction_id -- the id assigned by the bank to this transaction, it
       could be the one sent by the merchant in the request, but it is usually
       an identifier internal to the bank.
    '''

    def __init__(self, result=None, signed_result=None, bank_data=dict(),
            return_content=None, bank_status='', transaction_id='',
            order_id=''):
        self.result = result
        self.signed_result = signed_result
        self.bank_data = bank_data
        self.return_content = return_content
        self.bank_status = bank_status
        self.transaction_id = transaction_id
        self.order_id = order_id

class PaymentCommon(object):
    PATH = '/tmp'
    BANK_ID = '__bank_id'

    def __init__(self, options):
        LOGGER.debug('initializing with options %s' % options)
        for key, value in self.description['parameters'].iteritems():
            if 'default' in value:
                setattr(self, key, options.get(key, None) or value['default'])
            else:
                setattr(self, key, options.get(key))

    def transaction_id(self, length, choices, *prefixes):
        while True:
            parts = [RANDOM.choice(choices) for x in range(length)]
            id = ''.join(parts)
            name = '%s_%s_%s' % (str(date.today()), '-'.join(prefixes), str(id))
            try:
                fd=os.open(os.path.join(self.PATH, name), os.O_CREAT|os.O_EXCL)
            except:
                raise
            else:
                os.close(fd)
                return id
