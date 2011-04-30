import urllib
import string
try:
    from cgi import parse_qs
except:
    from urlparse import parse_qs

from common import PaymentCommon, URL

__all__ = [ 'Payment' ]

SERVICE_URL = 'http://dummy-payment.demo.entrouvert.com/'
ALPHANUM = string.letters + string.digits

class Payment(PaymentCommon):
    description = {
            'caption': 'Dummy payment backend',
            'parameters': {
                'direct_notification_url': {
                    'caption': 'direct notification url',
                },
                'siret': {
                    'caption': 'dummy siret parameter',
                },
            }
    }

    def __init__(self, options):
        self.direct_notification_url = options['direct_notification_url']
        self.siret = options['siret']

    def request(self, montant, email=None, next_url=None):
        transaction_id = self.transaction_id(30, ALPHANUM, 'dummy', self.siret)
        query = {
                'transaction_id': transaction_id,
                'amount': montant,
                'email': email,
                'return_url': next_url or '',
                'direct_notification_url': self.direct_notification_url
        }
        url = '%s?%s' % (SERVICE_URL, urllib.urlencode(query))
        return transaction_id, URL, url

    def response(self, query_string):
        form = parse_qs(query_string)
        transaction_id = form.get('transaction_id',[''])[0]

        if 'signed' in form:
            content = 'signature ok'
        else:
            content = None
        return 'ok' in form and transaction_id and True, transaction_id, form, content

if __name__ == '__main__':
    options = {
            'direct_notification_url': 'http://example.com/direct_notification_url',
            'siret': '1234'
    }
    p = Payment(options)
    print p.request(10.00, email='toto@example.com', next_url='http://example.com/retour')
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


