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

class PaymentCommon(object):
    PATH = '/tmp'

    def __init__(self, options):
        LOGGER.debug('initializing with options %s' % options)
        for key, value in self.description['parameters'].iteritems():
            if 'default' in value:
                setattr(self, key, options.get(key, value['default']))
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
