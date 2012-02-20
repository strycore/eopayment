# -*- coding: utf-8 -*-

import datetime as dt
import hashlib
import logging
import string
import urlparse
import urllib
from decimal import Decimal

from common import PaymentCommon, URL, PaymentResponse
from cb import CB_RESPONSE_CODES

__all__ = ['Payment']

PAYMENT_URL = "https://systempay.cyberpluspaiement.com/vads-payment/"
LOGGER = logging.getLogger(__name__)
SERVICE_URL = '???'
VADS_TRANS_DATE = 'vads_trans_date'
VADS_AUTH_NUMBER = 'vads_auth_number'
VADS_AUTH_RESULT = 'vads_auth_result'
VADS_RESULT = 'vads_result'
VADS_EXTRA_RESULT = 'vads_extra_result'
SIGNATURE = 'signature'
VADS_TRANS_ID = 'vads_trans_id'

def isonow():
    return dt.datetime.now()  \
            .isoformat('T')   \
            .replace('-','')  \
            .replace('T','')  \
            .replace(':','')[:14]

class Parameter:
    def __init__(self, name, ptype, code, max_length=None, length=None,
            needed=False, default=None, choices=None):
        self.name = name
        self.ptype = ptype
        self.code = code
        self.max_length = max_length
        self.length = length
        self.needed = needed
        self.default = default
        self.choices = choices

    def check_value(self, value):
        if self.length and len(str(value)) != self.length:
            return False
        if self.max_length and len(str(value)) > self.max_length:
            return False
        if self.choices and str(value) not in self.choices:
            return False
        if value == '':
            return True
        value = str(value).replace('.','')
        if self.ptype == 'n':
            return value.isdigit()
        elif self.ptype == 'an':
            return value.isalnum()
        elif self.ptype == 'an-':
            return value.replace('-','').isalnum()
        elif self.ptype == 'an;':
            return value.replace(';','').isalnum()
        elif self.ptype == 'an@':
            return value.replace('@','').isalnum()
        # elif self.ptype == 'ans':
        return True


PARAMETERS = [
        # amount as euro cents
        Parameter('vads_action_mode', None, 47, needed=True,
            default='INTERACTIVE', choices=('SILENT','INTERACTIVE')),
        Parameter('vads_amount', 'n', 9, max_length=12, needed=True),
        Parameter('vads_capture_delay', 'n', 6, max_length=3, default=''),
        Parameter('vads_contrib', 'ans', 31, max_length=255, default='eopayment'),
        # defaut currency = EURO, norme ISO4217
        Parameter('vads_currency', 'n', 10, length=3, default=978, needed=True),
        Parameter('vads_cust_address', 'an', 19, max_length=255),
        # code ISO 3166
        Parameter('vads_cust_country', 'a', 22, length=2, default='FR'),
        Parameter('vads_cust_email', 'an@', 15, max_length=127),
        Parameter('vads_cust_id', 'an', 16, max_length=63),
        Parameter('vads_cust_name', 'an', 18, max_length=127),
        Parameter('vads_cust_phone', 'an', 23, max_length=63),
        Parameter('vads_cust_title', 'an', 17, max_length=63),
        Parameter('vads_cust_city', 'an', 21, max_length=63),
        Parameter('vads_cust_zip', 'an', 20, max_length=63),
        # must be TEST or PRODUCTION
        Parameter('vads_ctx_mode', 'a', 11, needed=True),
        # ISO 639 code
        Parameter('vads_language', 'a', 12, length=2, default='fr'),
        Parameter('vads_order_id', 'an-', 13, max_length=32),
        Parameter('vads_order_info', 'an', 14, max_length=255),
        Parameter('vads_order_info2', 'an', 14, max_length=255),
        Parameter('vads_order_info3', 'an', 14, max_length=255),
        Parameter('vads_page_action', None, 46, needed=True, default='PAYMENT',
            choices=('PAYMENT',)),
        Parameter('vads_payment_cards', 'an;', 8, max_length=127, default=''),
        # must be SINGLE or MULTI with parameters
        Parameter('vads_payment_config', '', 07, default='SINGLE',
            choices=('SINGLE','MULTI'), needed=True),
        Parameter('vads_return_mode', None, 48, default='NONE',
            choices=('','NONE','POST','GET')),
        Parameter('signature', 'an', None, length=40),
        Parameter('vads_site_id', 'n', 02, length=8, needed=True),
        Parameter('vads_theme_config', 'ans', 32, max_length=255),
        Parameter(VADS_TRANS_DATE, 'n', 04, length=14, needed=True,
            default=isonow),
        Parameter('vads_trans_id', 'n', 03, length=6, needed=True),
        Parameter('vads_validation_mode', 'n', 5, max_length=1, choices=('', 0, 1),
            default=''),
        Parameter('vads_version', 'an', 01, default='V2', needed=True,
            choices=('V2',)),
        Parameter('vads_url_success', 'ans', 24, max_length=127),
        Parameter('vads_url_referral', 'ans', 26, max_length=127),
        Parameter('vads_url_refused', 'ans', 25, max_length=127),
        Parameter('vads_url_cancel', 'ans', 27, max_length=127),
        Parameter('vads_url_error', 'ans', 29, max_length=127),
        Parameter('vads_url_return', 'ans', 28, max_length=127),
        Parameter('vads_user_info', 'ans', 61, max_length=255),
        Parameter('vads_contracts', 'ans', 62, max_length=255),
]

AUTH_RESULT_MAP = CB_RESPONSE_CODES

RESULT_MAP = {
        '00': 'paiement réalisé avec succés',
        '02': 'le commerçant doit contacter la banque du porteur',
        '05': 'paiement refusé',
        '17': 'annulation client',
        '30': 'erreur de format',
        '96': 'erreur technique lors du paiement'
}

EXTRA_RESULT_MAP = {
        '': "Pas de contrôle effectué",
        '00': "Tous les contrôles se sont déroulés avec succés",
        '02': "La carte a dépassé l'encours autorisé",
        '03': "La carte appartient à la liste grise du commerçant",
        '04': "Le pays d'émission de la carte appartient à la liste grise du \
commerçant ou le pays d'émission de la carte n'appartient pas à la \
liste blanche du commerçant",
        '05': "L'addresse IP appartient à la liste grise du commerçant",
        '99': "Problème technique recontré par le serveur lors du traitement \
d'un des contrôles locaux",
}

def add_vads(kwargs):
    new_vargs={}
    for k, v in kwargs.iteritems():
        if k.startswith('vads_'):
            new_vargs[k] = v
        else:
            new_vargs['vads_'+k] = v
    return new_vargs

class Payment(PaymentCommon):
    ''' 
        ex.: Payment(secrets={'TEST': 'xxx', 'PRODUCTION': 'yyyy'}, site_id=123,
                ctx_mode='PRODUCTION')

    '''
    def __init__(self, options, logger=LOGGER):
        self.secrets = options.pop('secrets')
        options = add_vads(options)
        self.options = options

    def request(self, amount, email=None, next_url=None, logger=LOGGER):
        '''
           Create a dictionary to send a payment request to systempay the
           Credit Card payment server of the NATIXIS group
        '''
        kwargs = add_vads({'amount': amount})
        if Decimal(kwargs['vads_amount']) < 0:
            raise TypeError('amount must be an integer >= 0')
        if email:
            kwargs['vads_cust_email'] = email
        if next_url:
            kwargs['vads_url_return'] = next_url

        transaction_id = self.transaction_id(6,
                string.digits, 'systempay', self.options['vads_site_id'])
        kwargs['vads_trans_id'] = transaction_id
        fields = kwargs
        for parameter in PARAMETERS:
            name = parameter.name
            # import default parameters from configuration
            if name not in fields \
                    and name in self.options:
                fields[name] = self.options[name]
            # import default parameters from module
            if name not in fields and parameter.default is not None:
                if callable(parameter.default):
                    fields[name] = parameter.default()
                else:
                    fields[name] = parameter.default
            # raise error if needed parameters are absent
            if name not in fields and parameter.needed:
                raise ValueError('payment request is missing the %s parameter,\
parameters received: %s' % (name, kwargs))
            if name in fields \
                    and not parameter.check_value(fields[name]):
                        raise TypeError('%s value %s is not of the type %s' % (
                            name, fields[name],
                            parameter.ptype))
        fields[SIGNATURE] = self.signature(fields)
        url = '%s?%s' % (SERVICE_URL, urllib.urlencode(fields))
        transaction_id = '%s_%s' % (fields[VADS_TRANS_DATE], transaction_id)
        return transaction_id, URL, fields

    def response(self, query_string, logger=LOGGER):
        fields = urlparse.parse_qs(query_string)
        copy = fields.copy()
        bank_status = []
        if VADS_AUTH_RESULT in fields:
            v = copy[VADS_AUTH_RESULT]
            ctx = (v, AUTH_RESULT_MAP.get(v, 'Code inconnu'))
            copy[VADS_AUTH_RESULT] = '%s: %s' % ctx
            bank_status.append(copy[VADS_AUTH_RESULT])
        if VADS_RESULT in copy:
            v = copy[VADS_RESULT]
            ctx = (v, RESULT_MAP.get(v, 'Code inconnu'))
            copy[VADS_RESULT] = '%s: %s' % ctx
            bank_status.append(copy[VADS_RESULT])
            if v == '30':
                if VADS_EXTRA_RESULT in fields:
                    v = fields[VADS_EXTRA_RESULT]
                    if v.isdigit():
                        for parameter in PARAMETERS:
                            if int(v) == parameter.code:
                                s ='erreur dans le champ %s' % parameter.name
                                copy[VADS_EXTRA_RESULT] = s
                                bank_status.append(copy[VADS_EXTRA_RESULT])
            elif v in ('05', '00'):
                v = fields[VADS_EXTRA_RESULT]
                copy[VADS_EXTRA_RESULT] = '%s: %s' % (v,
                        EXTRA_RESULT_MAP.get(v, 'Code inconnu'))
                bank_status.append(copy[VADS_EXTRA_RESULT])
        logger.debug('checking systempay response on:')
        for key in sorted(fields.keys):
            logger.debug('  %s: %s' % (key, copy[key]))
        signature = self.signature(fields, logger)
        signature_result = signature == fields[SIGNATURE]
        if not signature_result:
            bank_status.append('invalid signature')
        result = fields[VADS_AUTH_RESULT] == '00'
        signed_result = signature_result and result
        logger.debug('signature check result: %s' % result)
        transaction_id = '%s_%s' % (copy[VADS_TRANS_DATE], copy[VADS_TRANS_ID])
        # the VADS_AUTH_NUMBER is the number to match payment in bank logs
        copy[self.BANK_ID] = copy.get(VADS_AUTH_NUMBER, '')
        response = PaymentResponse(
                result=result,
                signed_result=signed_result,
                bankd_data=copy,
                order_id=transaction_id,
                transaction_id=copy.get(VADS_AUTH_NUMBER),
                bank_status=' - '.join(bank_status))
        return response

    def signature(self, fields, logger):
        logger.debug('got fields %s to sign' % fields )
        ordered_keys = sorted([ key for key in fields.keys() if key.startswith('vads_') ])
        logger.debug('ordered keys %s' % ordered_keys)
        ordered_fields = [ str(fields[key]) for key in ordered_keys ]
        secret = self.secrets[fields['vads_ctx_mode']]
        signed_data = '+'.join(ordered_fields)
        logger.debug('generating signature on «%s»' % signed_data)
        sign = hashlib.sha1('%s+%s' % (signed_data, secret)).hexdigest()
        logger.debug('signature «%s»' % sign)
        return sign

if __name__ == '__main__':
    p = Payment(secrets={'TEST': '1234567890123456', 'PRODUCTION': 'yyy'}, site_id='00001234', ctx_mode='PRODUCTION')
    print p.request(amount=100, ctx_mode='TEST', site_id='12345678',
            trans_date='20090324122302', trans_id='122302',
            url_return='http://url.de.retour/retour.php')


