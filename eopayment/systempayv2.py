# -*- coding: utf-8 -*-

import datetime as dt
import hashlib
import logging
import string
import urlparse
import urllib
from decimal import Decimal

from common import PaymentCommon, URL

__all__ = ['Payment']

PAYMENT_URL = "https://systempay.cyberpluspaiement.com/vads-payment/"
LOGGER = logging.getLogger(__name__)
SERVICE_URL = '???'
VADS_TRANS_DATE = 'vads_trans_date'
VADS_AUTH_NUMBER = 'vads_auth_number'

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

AUTH_RESULT_MAP = {
        '00': "transaction approuvée ou traitée avec succés",
        '02': "contacter l'émetteur de la carte",
        '03': "accepteur invalid",
        '04': "conserver la carte",
        '05': "ne pas honorer",
        '07': "conserver la carte, conditions spéciales",
        '08': "approuver aprés identification",
        '12': "transaction invalide",
        '13': "montant invalide",
        '14': "numéro de porteur invalide",
        '30': "erreur de format",
        '31': "identifiant de l'organisme acquéreur inconnu",
        '33': "date de validité de la carte dépassée",
        '34': "suspicion de fraude",
        '41': "carte perdue",
        '43': "carte volée",
        '51': "provision insuffisante",
        '54': "date de validité de la carte dépassée",
        '56': "carte absente du fichier",
        '57': "transaction non permise à ce porteur",
        '58': "transaction interdite au terminal",
        '59': "suspicion de fraude",
        '60': "l'accepteur de carte doit contacter l'acquéreur",
        '61': "montant de retrait hors limite",
        '63': "règles de sécurité non respectée",
        '68': "réponse non parvenu ou réçu trop tard",
        '90': "arrêt momentané du système",
        '91': "émetteur de carte inacessible",
        '96': "mauvais fonctionnement du système",
        '94': "transaction dupliquée",
        '97': "échéance de la temporisation de surveillance globale",
        '98': "serveur indisponible routage réseau demandé à nouveau",
        '99': "incident domain initiateur",
}

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
    def __init__(self, options):
        self.secrets = options.pop('secrets')
        options = add_vads(options)
        self.options = options

    def request(self, amount, email=None, next_url=None):
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
        fields['signature'] = self.signature(fields)
        url = '%s?%s' % (SERVICE_URL, urllib.urlencode(fields))
        transaction_id = '%s_%s' % (fields[VADS_TRANS_DATE], transaction_id)
        return transaction_id, URL, fields

    def response(self, query_string):
        fields = urlparse.parse_qs(query_string)
        copy = fields.copy()
        if 'vads_auth_result' in fields:
            v = copy['vads_auth_result']
            ctx = (v, AUTH_RESULT_MAP.get(v, 'Code inconnu'))
            copy['vads_auth_result'] = '%s: %s' % ctx
        if 'vads_result' in copy:
            v = copy['vads_result']
            ctx = (v, RESULT_MAP.get(v, 'Code inconnu'))
            copy['vads_result'] = '%s: %s' % ctx
            if v == '30':
                if 'vads_extra_result' in fields:
                    v = fields['vads_extra_result']
                    if v.isdigit():
                        for parameter in PARAMETERS:
                            if int(v) == parameter.code:
                                s ='erreur dans le champ %s' % parameter.name
                                fields['vads_extra_result'] = s
            elif v in ('05', '00'):
                v = fields['vads_extra_result']
                fields['vads_extra_result'] = '%s: %s' % (v,
                        EXTRA_RESULT_MAP.get(v, 'Code inconnu'))
        LOGGER.debug('checking systempay response on:')
        for key in sorted(fields.keys):
            LOGGER.debug('  %s: %s' % (key, copy[key]))
        signature = self.signature(fields)
        result = signature == fields['signature']
        LOGGER.debug('signature check result: %s' % result)
        transaction_id = '%s_%s' % (copy[VADS_TRANS_DATE], copy[VADS_TRANS_ID])
        # the VADS_AUTH_NUMBER is the number to match payment in bank logs
        copy[self.BANK_ID] = copy.get(copy[VADS_AUTH_NUMBER], '')
        return result, transaction_id, copy, None

    def signature(self, fields):
        LOGGER.debug('got fields %s to sign' % fields )
        ordered_keys = sorted([ key for key in fields.keys() if key.startswith('vads_') ])
        LOGGER.debug('ordered keys %s' % ordered_keys)
        ordered_fields = [ str(fields[key]) for key in ordered_keys ]
        secret = self.secrets[fields['vads_ctx_mode']]
        signed_data = '+'.join(ordered_fields)
        LOGGER.debug('generating signature on «%s»' % signed_data)
        sign = hashlib.sha1('%s+%s' % (signed_data, secret)).hexdigest()
        LOGGER.debug('signature «%s»' % sign)
        return sign

if __name__ == '__main__':
    p = Payment(secrets={'TEST': '1234567890123456', 'PRODUCTION': 'yyy'}, site_id='00001234', ctx_mode='PRODUCTION')
    print p.request(amount=100, ctx_mode='TEST', site_id='12345678',
            trans_date='20090324122302', trans_id='122302',
            url_return='http://url.de.retour/retour.php')


