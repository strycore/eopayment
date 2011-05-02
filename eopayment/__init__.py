# -*- coding: utf-8 -*-

import logging

from common import URL, HTML

__all__ = [ 'Payment', 'URL', 'HTML', '__version__', 'SIPS', 'SYSTEMPAY',
    'SPPLUS', 'DUMMY', 'get_backend' ]

__version__ = "0.0.1"

SIPS = 'sips'
SYSTEMPAY = 'systempayv2'
SPPLUS = 'spplus'
DUMMY = 'dummy'

def get_backend(kind):
    '''Resolve a backend name into a module object'''
    module = __import__(kind, globals(), locals(), [])
    return module.Payment

class Payment(object):
    '''
       Interface to credit card online payment servers of French banks. The
       only use case supported for now is a unique automatic payment.

           >>> from eopayment import Payment, SPPLUS
           >>> spplus_options = {
                   'cle': '58 6d fc 9c 34 91 9b 86 3f fd 64 ' +
                          '63 c9 13 4a 26 ba 29 74 1e c7 e9 80 79',
                   'siret': '00000000000001-01',
               }
           >>> p = Payment(kind=SPPLUS, options=spplus_options)
           >>> print p.request('10.00', email='bob@example.com',
                 next_url='https://my-site.com')
           ('ZYX0NIFcbZIDuiZfazQp', 1, 'https://www.spplus.net/paiement/init.do?devise=978&validite=23%2F04%2F2011&version=1&reference=ZYX0NIFcbZIDuiZfazQp&montant=10.00&siret=00000000000001-01&langue=FR&taxe=0.00&email=bob%40example.com&hmac=b43dce98f97e5d249ef96f7f31d962f8fa5636ff')

       Supported backend of French banks are:

        - sips, for BNP, Banque Populaire (before 2010), CCF, HSBC, Crédit
          Agricole, La Banque Postale, LCL, Société Générale and Crédit du
          Nord.
        - spplus for Caisse d'épargne
        - systempay for Banque Populaire (after 2010)

       For SIPs you also need the bank provided middleware especially the two
       executables, request and response, as the protocol from ATOS/SIPS is not
       documented. For the other backends the modules are autonomous.

       Each backend need some configuration parameters to be used, the
       description of the backend list those parameters. The description
       dictionary can be used to generate configuration forms.

           >>> d = eopayment.get_backend(SPPLUS).description
           >>> print d['caption']
           SSPPlus payment service of French bank Caisse d'epargne
           >>> print d['parameters'].keys()
           ('cle','siret')
           >>> print d['parameters']['cle']['caption']
           Secret Key

    '''

    def __init__(self, kind, options):
        self.kind = kind
        self.backend = get_backend(kind)(options)

    def request(self, amount, email=None, next_url=None):
        '''Request a payment to the payment backend.

          Arguments:
          amount -- the amount of money to ask
          email -- the email of the customer (optional)
          next_url -- the URL where the customer will be returned (optional),
          usually redundant with the hardwired settings in the bank
          configuration panel. At this url you must use the Payment.response
          method to analyze the bank returned values.

          It returns a triple of values, (transaction_id, kind, data):
            - the first gives a string value to later match the payment with
              the invoice,
            - kind gives the type of the third value, payment.URL or
              payment.HTML, 
            - the third is the URL or the HTML form to contact the payment
              server, which must be sent to the customer browser.

          kind of the third argument, it can be URL or HTML, the third is the
          corresponding value as string containing HTML or an URL

           >>> transaction_id, kind, data = processor.request('100.00')
           >>> # asociate transaction_id to invoice
           >>> invoice.add_transaction_id(transaction_id)
           >>> if kind == eopayment.URL:
                   # redirect the user to the URL in data
               elif kind == eopayment.HTML:
                   # present the form in HTML to the user

        '''
        return self.backend.request(amount, email=email, next_url=next_url)

    def response(self, query_string):
        '''
          Process a response from the Bank API. It must be used on the URL
          where the user browser of the payment server is going to post the
          result of the payment. Beware it can happen multiple times for the
          same payment, so you MUST support multiple notification of the same
          event, i.e. it should be idempotent. For example if you already
          validated some invoice, receiving a new payment notification for the
          same invoice should alter this state change.

          Beware that when notified directly by the bank (and not through the
          customer browser) no applicative session will exist, so you should
          not depend on it in your handler.

          Arguments:
          query_string -- the URL encoded form-data from a GET or a POST

          It returns a quadruplet of values:
          
             (result, transaction_id, bank_data, return_content)

           - result is a boolean stating whether the transaction worked, use it
             to decide whether to act on a valid payment,
           - the transaction_id return the same id than returned by request
             when requesting for the payment, use it to find the invoice or
             transaction which is linked to the payment,
           - bank_data is a dictionnary of the data sent by the bank, it should
             be logged for security reasons,
           - return_content, if not None you must return this content as the
             result of the HTTP request, it's used when the bank is calling
             your site as a web service.

        '''
        return self.backend.response(query_string)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    spplus_options = {
        'cle': '58 6d fc 9c 34 91 9b 86 3f fd 64 \
63 c9 13 4a 26 ba 29 74 1e c7 e9 80 79', 
        'siret': '00000000000001-01',
    }
    p = Payment(kind=SPPLUS, options=spplus_options)
    print p.request('10.00', email='bob@example.com',
            next_url='https://my-site.com')
    systempay_options = {
        'secrets': {
            'TEST': '1234567890123456', 
            'PRODUCTION': 'yyy'
        },
        'site_id': '00001234',
        'ctx_mode': 'PRODUCTION'
    }

    p = Payment(SYSTEMPAY, systempay_options)
    print p.request('10.00', email='bob@example.com',
            next_url='https://my-site.com')

    sips_options = { 'filepath': '/', 'binpath': './' }
    p = Payment(kind=SIPS, options=sips_options)
    print p.request('10.00', email='bob@example.com',
            next_url='https://my-site.com')
