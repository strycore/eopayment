import urllib
import string
try:
    from cgi import parse_qs
except:
    from urlparse import parse_qs

from common import PaymentCommon, URL, PaymentResponse

__all__ = [ 'Payment' ]

SERVICE_URL = 'http://dummy-payment.demo.entrouvert.com/'
ALPHANUM = string.letters + string.digits

class Payment(PaymentCommon):
    '''
       Dummy implementation of the payment interface.

       It is used with a dummy implementation of a bank payment service that
       you can find on:

           http://dummy-payment.demo.entrouvert.com/

       You must pass the following keys inside the options dictionnary:
        - dummy_service_url, the URL of the dummy payment service, it defaults
          to the one operated by Entr'ouvert.
        - direct_notification_url: where to POST to notify the service of a
          payment
        - origin: a human string to display to the user about the origin of
          the request.
        - siret: an identifier for the eCommerce site, fake.
        - next_url: the return URL for the user (can be overriden on a per
          request basis).
    '''
    description = {
            'caption': 'Dummy payment backend',
            'parameters': {
                'dummy_service_url': {
                    'caption': 'URL of the dummy payment service',
                    'default': SERVICE_URL,
                    'type': str,
                },
                'direct_notification_url': {
                    'caption': 'direct notification url',
                    'type': str,
                },
                'origin': {
                    'caption': 'name of the requesting service, '
                               'to present in the user interface',
                    'type': str,

                },
                'siret': {
                    'caption': 'dummy siret parameter',
                    'type': str,
                },
                'next_url': {
                    'caption': 'Return URL for the user',
                    'type': str,
                },
                'consider_all_response_signed': {
                    'caption': 'All response will be considered as signed '
                         '(to test payment locally for example, as you '
                         'cannot received the signed callback)',
                    'type': bool,
                    'default': False,
                },
            }
    }

    def request(self, montant, email=None, next_url=None):
        transaction_id = self.transaction_id(30, ALPHANUM, 'dummy', self.siret)
        if self.next_url:
            next_url = self.next_url
        query = {
                'transaction_id': transaction_id,
                'siret': self.siret,
                'amount': montant,
                'email': email,
                'return_url': next_url or '',
                'direct_notification_url': self.direct_notification_url,
                'origin': self.origin
        }
        url = '%s?%s' % (SERVICE_URL, urllib.urlencode(query))
        return transaction_id, URL, url

    def response(self, query_string):
        form = parse_qs(query_string)
        transaction_id = form.get('transaction_id',[''])[0]
        form[self.BANK_ID] = transaction_id

        signed = 'signed' in form
        if signed:
            content = 'signature ok'
        else:
            content = None
        signed = signed and self.consider_all_response_signed
        result = 'ok' in form
        signed_result = result if signed else None

        response = PaymentResponse(result=result,
                signed_result=signed_result,
                bank_data=form,
                return_content=content,
                order_id=transaction_id,
                transaction_id=transaction_id,
                bank_status=form.get('reason'))
        return response

if __name__ == '__main__':
    options = {
            'direct_notification_url': 'http://example.com/direct_notification_url',
            'siret': '1234',
            'origin': 'Mairie de Perpette-les-oies'
    }
    p = Payment(options)
    retour = 'http://example.com/retour?amount=10.0&direct_notification_url=http%3A%2F%2Fexample.com%2Fdirect_notification_url&email=toto%40example.com&transaction_id=6Tfw2e1bPyYnz7CedZqvdHt7T9XX6T&return_url=http%3A%2F%2Fexample.com%2Fretour&nok=1'
    r = p.response(retour.split('?',1)[1])
    assert not r[0] 
    assert r[1] == '6Tfw2e1bPyYnz7CedZqvdHt7T9XX6T'
    assert r[3] is None
    retour = 'http://example.com/retour?amount=10.0&direct_notification_url=http%3A%2F%2Fexample.com%2Fdirect_notification_url&email=toto%40example.com&transaction_id=6Tfw2e1bPyYnz7CedZqvdHt7T9XX6T&return_url=http%3A%2F%2Fexample.com%2Fretour&ok=1&signed=1'
    r = p.response(retour.split('?',1)[1])
    assert r[0] 
    assert r[1] == '6Tfw2e1bPyYnz7CedZqvdHt7T9XX6T'
    assert r[3] == 'signature ok'


