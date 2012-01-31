from decimal import Decimal
import binascii
import hmac
import hashlib
import urlparse
import urllib
import string
import datetime as dt
import logging
import re

import Crypto.Cipher.DES
from common import PaymentCommon, URL

__all__ = ['Payment']

KEY_DES_KEY = '\x45\x1f\xba\x4f\x4c\x3f\xd4\x97'
IV = '\x30\x78\x30\x62\x2c\x30\x78\x30'
REFERENCE = 'reference'
ETAT = 'etat'
ETAT_PAIEMENT_ACCEPTE = '1'
SPCHECKOK = 'spcheckok'
LOGGER = logging.getLogger(__name__)
REFSFP = 'refsfp'

def decrypt_ntkey(ntkey):
    key = binascii.unhexlify(ntkey.replace(' ',''))
    return decrypt_key(key)

def decrypt_key(key):
    CIPHER = Crypto.Cipher.DES.new(KEY_DES_KEY, Crypto.Cipher.DES.MODE_CBC, IV)
    return CIPHER.decrypt(key)

def sign_ntkey_query(ntkey, query):
    key = decrypt_ntkey(ntkey)
    data_to_sign = ''.join(y for x,y in urlparse.parse_qsl(query, True))
    return hmac.new(key[:20], data_to_sign, hashlib.sha1).hexdigest().upper()

PAIEMENT_FIELDS = [ 'siret', REFERENCE, 'langue', 'devise', 'montant',
    'taxe', 'validite' ]

def sign_url_paiement(ntkey, query):
    if '?' in query:
        query = query[query.index('?')+1:]
    key = decrypt_ntkey(ntkey)
    data = urlparse.parse_qs(query, True)
    fields = [data.get(field,[''])[0] for field in PAIEMENT_FIELDS]
    data_to_sign = ''.join(fields)
    return hmac.new(key[:20], data_to_sign, hashlib.sha1).hexdigest().upper()

ALPHANUM = string.letters + string.digits
SERVICE_URL = "https://www.spplus.net/paiement/init.do"
LOGGER = logging.getLogger(__name__)

class Payment(PaymentCommon):
    description = {
            'caption': "SPPlus payment service of French bank Caisse d'epargne",
            'parameters': {
                'cle': {
                    'caption': 'Secret key, a 40 digits hexadecimal number',
                    'regexp': re.compile('^ *((?:[a-fA-F0-9] *){40}) *$')
                },
                'siret': {
                    'caption': 'Siret of the entreprise augmented with the '
                        'site number, example: 00000000000001-01',
                    'regexp': re.compile('^ *(\d{14}-\d{2}) *$')
                },
                'langue': {
                    'caption': 'Language of the customers',
                    'default': 'FR',
                },
                'taxe': {
                    'caption': 'Taxes',
                    'default': '0.00'
                },
                'modalite': {
                    'caption': '1x, 2x, 3x, xx, nx (if multiple separated by "/")',
                    'default': '1x',
                },
                'moyen': {
                    'caption': 'AUR, AMX, CBS, CGA, '
                        'CHK, DIN, PRE (if multiple separate by "/")',
                    'default': 'CBS',
                },
            }
    }
    devise = '978'

    def request(self, montant, email=None, next_url=None):
        LOGGER.debug('requesting spplus payment with montant %s email=%s and \
next_url=%s' % (montant, email, next_url))
        reference = self.transaction_id(20, ALPHANUM, 'spplus', self.siret)
        validite = dt.date.today()+dt.timedelta(days=1)
        validite = validite.strftime('%d/%m/%Y')
        fields = { 'siret': self.siret,
                'devise': self.devise,
                'langue': self.langue,
                'taxe': self.taxe,
                'montant': str(Decimal(montant)),
                REFERENCE: reference,
                'validite': validite,
                'version': '1',
                'modalite': self.modalite,
                'moyen': self.moyen }
        if email:
            fields['email'] = email
        if next_url:
            if (not next_url.startswith('http://') \
                    and not next_url.startswith('https://')) \
                       or '?' in next_url:
                   raise ValueError('next_url must be an absolute URL without parameters')
            fields['urlretour'] = next_url
        LOGGER.debug('sending fields %s' % fields)
        query = urllib.urlencode(fields)
        url = '%s?%s&hmac=%s' % (SERVICE_URL, query, sign_url_paiement(self.cle,
            query))
        LOGGER.debug('full url %s' % url)
        return reference, URL, url

    def response(self, query_string):
        form = urlparse.parse_qs(query_string)
        LOGGER.debug('received query_string %s' % query_string)
        LOGGER.debug('parsed as %s' % form)
        reference = form.get(REFERENCE)
        if not 'hmac' in form:
            return form.get('etat') == 1, reference, form, None
        else:
            try:
                signed_data, signature = query_string.rsplit('&', 1)
                _, hmac = signature.split('=', 1)
                LOGGER.debug('got signature %s' % hmac)
                computed_hmac = sign_ntkey_query(self.cle, signed_data)
                LOGGER.debug('computed signature %s' % hmac)
                result = hmac==computed_hmac \
                        and form.get(ETAT) == ETAT_PAIEMENT_ACCEPTE
                form[self.BANK_ID] = form.get(REFSFP, '')
                return result, reference, form, SPCHECKOK
            except ValueError:
                return False, reference, form, SPCHECKOK

if __name__ == '__main__':
    import sys

    ntkey = '58 6d fc 9c 34 91 9b 86 3f fd 64 63 c9 13 4a 26 ba 29 74 1e c7 e9 80 79'
    if len(sys.argv) == 2:
        print sign_url_paiement(ntkey, sys.argv[1])
        print sign_ntkey_query(ntkey, sys.argv[1])
    elif len(sys.argv) > 2:
        print sign_url_paiement(sys.argv[1], sys.argv[2])
        print sign_ntkey_query(sys.argv[1], sys.argv[2])
