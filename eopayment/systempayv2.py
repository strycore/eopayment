# -*- coding: utf-8 -*-

import datetime as dt
import hashlib
import logging
import string
import urlparse
import urllib
from decimal import Decimal
from gettext import gettext as _

from common import PaymentCommon, PaymentResponse, URL, PAID, ERROR
from cb import CB_RESPONSE_CODES

__all__ = ['Payment']

SERVICE_URL = "https://paiement.systempay.fr/vads-payment/"
LOGGER = logging.getLogger(__name__)
VADS_TRANS_DATE = 'vads_trans_date'
VADS_AUTH_NUMBER = 'vads_auth_number'
VADS_AUTH_RESULT = 'vads_auth_result'
VADS_RESULT = 'vads_result'
VADS_EXTRA_RESULT = 'vads_extra_result'
VADS_CUST_EMAIL = 'vads_cust_email'
VADS_URL_RETURN = 'vads_url_return'
VADS_AMOUNT = 'vads_amount'
VADS_SITE_ID = 'vads_site_id'
VADS_TRANS_ID = 'vads_trans_id'
SIGNATURE = 'signature'
VADS_TRANS_ID = 'vads_trans_id'


def isonow():
    return dt.datetime.now()  \
            .isoformat('T')   \
            .replace('-', '')  \
            .replace('T', '')  \
            .replace(':', '')[:14]


class Parameter:
    def __init__(self, name, ptype, code, max_length=None, length=None,
            needed=False, default=None, choices=None, description=None,
            help_text=None):
        self.name = name
        self.ptype = ptype
        self.code = code
        self.max_length = max_length
        self.length = length
        self.needed = needed
        self.default = default
        self.choices = choices
        self.description = description
        self.help_text = help_text

    def check_value(self, value):
        if self.length and len(str(value)) != self.length:
            return False
        if self.max_length and len(str(value)) > self.max_length:
            return False
        if self.choices and str(value) not in self.choices:
            return False
        if value == '':
            return True
        value = str(value).replace('.', '')
        if self.ptype == 'n':
            return value.isdigit()
        elif self.ptype == 'an':
            return value.isalnum()
        elif self.ptype == 'an-':
            return value.replace('-', '').isalnum()
        elif self.ptype == 'an;':
            return value.replace(';', '').isalnum()
        elif self.ptype == 'an@':
            return value.replace('@', '').isalnum()
        # elif self.ptype == 'ans':
        return True


PARAMETERS = [
        # amount as euro cents
        Parameter('vads_action_mode', None, 47, needed=True,
            default='INTERACTIVE', choices=('SILENT', 'INTERACTIVE')),
        Parameter('vads_amount', 'n', 9, max_length=12, needed=True),
        Parameter('vads_capture_delay', 'n', 6, max_length=3, default=''),
        Parameter('vads_contrib', 'ans', 31, max_length=255,
                  default='eopayment'),
        # defaut currency = EURO, norme ISO4217
        Parameter('vads_currency', 'n', 10, length=3, default=978,
                  needed=True),
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
        Parameter('vads_ctx_mode', 'a', 11, needed=True, choices=('TEST',
            'PRODUCTION'), default='TEST'),
        # ISO 639 code
        Parameter('vads_language', 'a', 12, length=2, default='fr'),
        Parameter('vads_order_id', 'an-', 13, max_length=32),
        Parameter('vads_order_info', 'an', 14, max_length=255,
            description=_(u"Complément d'information 1")),
        Parameter('vads_order_info2', 'an', 14, max_length=255,
            description=_(u"Complément d'information 2")),
        Parameter('vads_order_info3', 'an', 14, max_length=255,
            description=_(u"Complément d'information 3")),
        Parameter('vads_page_action', None, 46, needed=True, default='PAYMENT',
            choices=('PAYMENT',)),
        Parameter('vads_payment_cards', 'an;', 8, max_length=127, default='',
            description=_(u'Liste des cartes de paiement acceptées'),
            help_text=_(u'vide ou des valeurs sépareés par un point-virgule parmi '
            'AMEX, AURORE-MULTI, BUYSTER, CB, COFINOGA, E-CARTEBLEUE, '
            'MASTERCARD, JCB, MAESTRO, ONEY, ONEY_SANDBOX, PAYPAL, '
            'PAYPAL_SB, PAYSAFECARD, VISA')),
        # must be SINGLE or MULTI with parameters
        Parameter('vads_payment_config', '', 07, default='SINGLE',
            choices=('SINGLE', 'MULTI'), needed=True),
        Parameter('vads_return_mode', None, 48, default='GET',
            choices=('', 'NONE', 'POST', 'GET')),
        Parameter('signature', 'an', None, length=40),
        Parameter('vads_site_id', 'n', 02, length=8, needed=True,
            description=_(u'Identifiant de la boutique')),
        Parameter('vads_theme_config', 'ans', 32, max_length=255),
        Parameter(VADS_TRANS_DATE, 'n', 04, length=14, needed=True,
            default=isonow),
        Parameter('vads_trans_id', 'n', 03, length=6, needed=True),
        Parameter('vads_validation_mode', 'n', 5, max_length=1,
                  choices=('', 0, 1), default=''),
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
PARAMETER_MAP = dict(((parameter.name,
                       parameter) for parameter in PARAMETERS))

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
    new_vargs = {}
    for k, v in kwargs.iteritems():
        if k.startswith('vads_'):
            new_vargs[k] = v
        else:
            new_vargs['vads_' + k] = v
    return new_vargs


def check_vads(kwargs, exclude=[]):
    for parameter in PARAMETERS:
        name = parameter.name
        if name not in kwargs and name not in exclude and parameter.needed:
            raise ValueError('parameter %s must be defined' % name)
        if name in kwargs and not parameter.check_value(kwargs[name]):
            raise ValueError('parameter %s value %s is not of the type %s' % (
                name, kwargs[name],
                parameter.ptype))


class Payment(PaymentCommon):
    '''
        Produce request for and verify response from the SystemPay payment
        gateway.

            >>> gw =Payment(dict(secret_test='xxx', secret_production='yyyy',
                                 site_id=123, ctx_mode='PRODUCTION'))
            >>> print gw.request(100)
            ('20120525093304_188620',
            'https://paiement.systempay.fr/vads-payment/?vads_url_return=http%3A%2F%2Furl.de.retour%2Fretour.php&vads_cust_country=FR&vads_site_id=93413345&vads_payment_config=SINGLE&vads_trans_id=188620&vads_action_mode=INTERACTIVE&vads_contrib=eopayment&vads_page_action=PAYMENT&vads_trans_date=20120525093304&vads_ctx_mode=TEST&vads_validation_mode=&vads_version=V2&vads_payment_cards=&signature=5d412498ab523627ec5730a09118f75afa602af5&vads_language=fr&vads_capture_delay=&vads_currency=978&vads_amount=100&vads_return_mode=NONE',
            {'vads_url_return': 'http://url.de.retour/retour.php',
            'vads_cust_country': 'FR', 'vads_site_id': '93413345',
            'vads_payment_config': 'SINGLE', 'vads_trans_id': '188620',
            'vads_action_mode': 'INTERACTIVE', 'vads_contrib': 'eopayment',
            'vads_page_action': 'PAYMENT', 'vads_trans_date': '20120525093304',
            'vads_ctx_mode': 'TEST', 'vads_validation_mode': '',
            'vads_version': 'V2', 'vads_payment_cards': '', 'signature':
            '5d412498ab523627ec5730a09118f75afa602af5', 'vads_language': 'fr',
            'vads_capture_delay': '', 'vads_currency': 978, 'vads_amount': 100,
            'vads_return_mode': 'NONE'})

    '''
    description = {
        'caption': 'SystemPay, système de paiment du groupe BPCE',
        'parameters': [
            {'name': 'service_url',
                'default': SERVICE_URL,
                'caption': _(u'URL du service de paiment'),
                'help_text': _(u'ne pas modifier si vous ne savez pas'),
                'validation': lambda x: x.startswith('http'),
                'required': True, },
            {'name': 'secret_test',
                'caption': _(u'Secret pour la configuration de TEST'),
                'validation': str.isdigit,
                'required': True, },
            {'name': 'secret_production',
                'caption': _(u'Secret pour la configuration de PRODUCTION'),
                'validation': str.isdigit, },
        ]
    }

    for name in ('vads_ctx_mode', VADS_SITE_ID, 'vads_order_info',
                 'vads_order_info2', 'vads_order_info3',
                 'vads_payment_cards', 'vads_payment_config'):
        parameter = PARAMETER_MAP[name]
        x = {'name': name,
             'caption': parameter.description or name,
             'validation': parameter.check_value,
             'default': parameter.default,
             'required': parameter.needed,
             'help_text': parameter.help_text,
             'max_length': parameter.max_length}
        description['parameters'].append(x)

    def __init__(self, options, logger=LOGGER):
        self.service_url = options.pop('service_url', SERVICE_URL)
        self.secret_test = options.pop('secret_test')
        self.secret_production = options.pop('secret_production', None)
        options = add_vads(options)
        self.options = options
        self.logger = logger

    def request(self, amount, email=None, next_url=None, **kwargs):
        '''
           Create a dictionary to send a payment request to systempay the
           Credit Card payment server of the NATIXIS group
        '''
        self.logger.debug('%s amount %s email %s next_url %s, kwargs: %s',
                __name__, amount, email, next_url, kwargs)
        # amount unit is cents
        amount = 100 * amount
        kwargs.update(add_vads({'amount': amount}))
        if Decimal(kwargs[VADS_AMOUNT]) < 0:
            raise ValueError('amount must be an integer >= 0')
        if email:
            kwargs[VADS_CUST_EMAIL] = email
        if next_url:
            kwargs[VADS_URL_RETURN] = next_url

        transaction_id = self.transaction_id(6,
                string.digits, 'systempay', self.options[VADS_SITE_ID])
        kwargs[VADS_TRANS_ID] = transaction_id
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
        check_vads(fields)
        fields[SIGNATURE] = self.signature(fields)
        self.logger.debug('%s request contains fields: %s', __name__, fields)
        url = '%s?%s' % (SERVICE_URL, urllib.urlencode(fields))
        self.logger.debug('%s return url %s', __name__, url)
        transaction_id = '%s_%s' % (fields[VADS_TRANS_DATE], transaction_id)
        self.logger.debug('%s transaction id: %s', __name__, transaction_id)
        return transaction_id, URL, url

    def response(self, query_string):
        fields = urlparse.parse_qs(query_string, True)
        for key, value in fields.iteritems():
            fields[key] = value[0]
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
                                s = 'erreur dans le champ %s' % parameter.name
                                copy[VADS_EXTRA_RESULT] = s
                                bank_status.append(copy[VADS_EXTRA_RESULT])
            elif v in ('05', '00'):
                if VADS_EXTRA_RESULT in fields:
                    v = fields[VADS_EXTRA_RESULT]
                    copy[VADS_EXTRA_RESULT] = '%s: %s' % (v,
                            EXTRA_RESULT_MAP.get(v, 'Code inconnu'))
                    bank_status.append(copy[VADS_EXTRA_RESULT])
        self.logger.debug('checking systempay response on:')
        for key in sorted(fields.keys()):
            self.logger.debug('  %s: %s' % (key, copy[key]))
        signature = self.signature(fields)
        signature_result = signature == fields[SIGNATURE]
        self.logger.debug('signature check: %s <!> %s', signature,
                fields[SIGNATURE])
        if not signature_result:
            bank_status.append('invalid signature')

        if fields[VADS_AUTH_RESULT] == '00':
            result = PAID
        else:
            result = ERROR
        transaction_id = '%s_%s' % (copy[VADS_TRANS_DATE], copy[VADS_TRANS_ID])
        # the VADS_AUTH_NUMBER is the number to match payment in bank logs
        copy[self.BANK_ID] = copy.get(VADS_AUTH_NUMBER, '')
        response = PaymentResponse(
                result=result,
                signed=signature_result,
                bank_data=copy,
                order_id=transaction_id,
                transaction_id=copy.get(VADS_AUTH_NUMBER),
                bank_status=' - '.join(bank_status))
        return response

    def signature(self, fields):
        self.logger.debug('got fields %s to sign' % fields)
        ordered_keys = sorted([key for key in fields.keys() if key.startswith('vads_')])
        self.logger.debug('ordered keys %s' % ordered_keys)
        ordered_fields = [str(fields[key]) for key in ordered_keys]
        secret = getattr(self, 'secret_%s' % fields['vads_ctx_mode'].lower())
        signed_data = '+'.join(ordered_fields)
        signed_data = '%s+%s' % (signed_data, secret)
        self.logger.debug('generating signature on «%s»' % signed_data)
        sign = hashlib.sha1(signed_data).hexdigest()
        self.logger.debug('signature «%s»' % sign)
        return sign

if __name__ == '__main__':
    p = Payment(dict(
        secret_test='2662931409789978',
        site_id='93413345',
        ctx_mode='TEST'))
    print p.request(100, vads_url_return='http://url.de.retour/retour.php')
    qs = 'vads_amount=100&vads_auth_mode=FULL&vads_auth_number=767712&vads_auth_result=00&vads_capture_delay=0&vads_card_brand=CB&vads_card_number=497010XXXXXX0000&vads_payment_certificate=9da32cc109882089e1b3fb80888ebbef072f70b7&vads_ctx_mode=TEST&vads_currency=978&vads_effective_amount=100&vads_site_id=93413345&vads_trans_date=20120529132547&vads_trans_id=620594&vads_validation_mode=0&vads_version=V2&vads_warranty_result=NO&vads_payment_src=&vads_order_id=---&vads_cust_country=FR&vads_contrib=eopayment&vads_contract_used=2334233&vads_expiry_month=6&vads_expiry_year=2013&vads_pays_ip=FR&vads_identifier=&vads_subscription=&vads_threeds_enrolled=&vads_threeds_cavv=&vads_threeds_eci=&vads_threeds_xid=&vads_threeds_cavvAlgorithm=&vads_threeds_status=&vads_threeds_sign_valid=&vads_threeds_error_code=&vads_threeds_exit_status=&vads_result=00&vads_extra_result=&vads_card_country=FR&vads_language=fr&vads_action_mode=INTERACTIVE&vads_page_action=PAYMENT&vads_payment_config=SINGLE&signature=9c4f2bf905bb06b008b07090905adf36638d8ece&'
    response = p.response(qs)
    assert response.signed and response.result
