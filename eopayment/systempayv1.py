# -*- coding: utf-8 -*-

import datetime as dt
import hashlib
import logging

__all__ = ['Payment']

PAYMENT_URL = "https://systempay.cyberpluspaiement.com/vads-payment/"

def isonow():
    return dt.datetime.now()  \
            .isoformat('T')   \
            .replace('-','')  \
            .replace('T','')  \
            .replace(':','')[:14]

logger = logging.getLogger(__name__)

class Parameter:
    def __init__(self, name, ptype, code, max_length=None, length=None, needed=False,
            sign=False, default=None, choices=None):
        self.name = name
        self.ptype = ptype
        self.code = code
        self.max_length = max_length
        self.length = length
        self.needed = needed
        self.sign = sign
        self.default = default
        self.choices = choices

    def check_value(self, value):
        if self.length and len(str(value)) != self.length:
            return False
        if self.max_length and len(str(value)) > self.max_length:
            return False
        if value == '':
            return True
        if self.ptype == 'n':
            return str(value).isdigit()
        elif self.ptype == 'an':
            return str(value).isalnum()
        elif self.ptype == 'an-':
            return str(value).replace('-','').isalnum()
        elif self.ptype == 'an;':
            return str(value).replace(';','').isalnum()
        # elif self.ptype == 'ans':
        return True


PARAMETERS = [
        # amount as euro cents
        Parameter('amount', 'n', 9, max_length=12, needed=True, sign=True),
        Parameter('capture_delay', 'n', 6, max_length=3, needed=True,
            sign=True, default=''),
        Parameter('contrib', 'ans', 31, max_length=255, default='eopayment'),
        # defaut currency = EURO, norme ISO4217
        Parameter('currency', 'n', 10, length=3, default=978, needed=True,
            sign=True),
        Parameter('cust_address', 'an', 19, max_length=255),
        Parameter('cust_country', 'a', 22, length=2, default='FR'),
        Parameter('cust_email', 'an', 15, max_length=127),
        Parameter('cust_id', 'an', 16, max_length=63),
        Parameter('cust_name', 'an', 18, max_length=127),
        Parameter('cust_phone', 'an', 23, max_length=63),
        Parameter('cust_title', 'an', 17, max_length=63),
        Parameter('cust_city', 'an', 21, max_length=63),
        Parameter('cust_zip', 'an', 20, max_length=63),
        # must be TEST or PRODUCTION
        Parameter('ctx_mode', 'a', 11, needed=True, sign=True, default='TEST'),
        # ISO 639 code
        Parameter('language', 'a', 12, length=2, default='fr'),
        Parameter('order_id', 'an-', 13, max_length=32),
        Parameter('order_info', 'an', 14, max_length=255),
        Parameter('order_info2', 'an', 14, max_length=255),
        Parameter('order_info3', 'an', 14, max_length=255),
        Parameter('payment_cards', 'an;', 8, max_length=127, default='',
            needed=True, sign=True),
        # must be SINGLE or MULTI with parameters
        Parameter('payment_config', '', 07, default='SINGLE',
            choices=('SINGLE','MULTI'), needed=True, sign=True),
        Parameter('payment_src', 'a', 60, max_length=5, default='',
            choices=('', 'BO', 'MOTO', 'CC', 'OTHER')),
        Parameter('signature', 'an', None, length=40),
        Parameter('site_id', 'n', 02, length=8, needed=True, sign=True),
        Parameter('theme_config', 'ans', 32, max_length=255),
        Parameter('trans_date', 'n', 04, length=14, needed=True, sign=True,
            default=isonow),
        Parameter('trans_id', 'n', 03, length=6, needed=True, sign=True),
        Parameter('validation_mode', 'n', 5, max_length=1, choices=('', 0, 1),
            needed=True, sign=True, default=''),
        Parameter('version', 'an', 01, default='V1', needed=True, sign=True),
        Parameter('url_success', 'ans', 24, max_length=127),
        Parameter('url_referral', 'ans', 26, max_length=127),
        Parameter('url_refused', 'ans', 25, max_length=127),
        Parameter('url_cancel', 'ans', 27, max_length=127),
        Parameter('url_error', 'ans', 29, max_length=127),
        Parameter('url_return', 'ans', 28, max_length=127),
        Parameter('user_info', 'ans', 61, max_length=255),
        Parameter('contracts', 'ans', 62, max_length=255),
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

REQUEST_SIGNATURE_FIELDS = ['version', 'site_id', 'ctx_mode', 'trans_id', 'trans_date',
    'validation_mode', 'capture_delay', 'payment_config', 'payment_cards',
    'amount', 'currency'] 

RESPONSE_SIGNATURE_FIELDS = ['version', 'site_id', 'ctx_mode', 'trans_id',
    'trans_date', 'validation_mode', 'capture_delay', 'payment_config',
    'card_brand', 'card_number', 'amount', 'currency', 'auth_mode', 'auth_result',
    'auth_number', 'warranty_result', 'payment_certificate', 'result' ]

S2S_RESPONSE_SIGNATURE_FIELDS = RESPONSE_SIGNATURE_FIELDS + [ 'hash' ]

LOGGER = logging.getLogger(__name__)

class Payment:
    ''' 
        ex.: Payment(secrets={'TEST': 'xxx', 'PRODUCTION': 'yyyy'}, site_id=123,
                ctx_mode='PRODUCTION')

    '''
    def __init__(self, **kwargs):
        self.options = kwargs

    def request(self, amount, **kwargs, logger=LOGGER):
        '''
           Create a dictionnary to send a payment request to systempay the
           Credit Card payment server of the NATIXIS group
        '''
        if not isinstance(amount, int) or amount < 0:
            raise TypeError('amount must be an integerer >= 0')
        fields = { 'amount': amount }
        fields.update(kwargs)
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
        fields['signature'] = self.signature(fields, REQUEST_SIGNATURE_FIELDS)
        return fields

    def check_response(self, fields):
        signature = self.signature(fields, RESPONSE_SIGNATURE_FIELDS)
        return signature == fields['signature']

    def check_s2s_response(self, fields):
        signature = self.signature(fields, S2S_RESPONSE_SIGNATURE_FIELDS)
        return signature == fields['signature']

    def signature(self, fields, fields_to_sign):
        logging.debug('got fields %s to sign' % fields)
        secret = self.options['secrets'][fields['ctx_mode']]
        ordered_fields = [ str(fields[field]) for field in fields_to_sign]
        signed_data = '+'.join(ordered_fields)
        logger.debug('generating signature on «%s»' % signed_data)
        sign = hashlib.sha1('%s+%s' % (signed_data, secret)).hexdigest()
        logger.debug('signature «%s»' % sign)
        return sign

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    p = Payment(secrets={'TEST': '1234567890123456', 'PRODUCTION': 'yyy'}, site_id='00001234', ctx_mode='PRODUCTION')
    print p.request(100, ctx_mode='TEST', site_id='12345678',
            trans_date='20090324122302', trans_id='122302',
            url_return='http://url.de.retour/retour.php')


