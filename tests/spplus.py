from unittest import TestCase
import eopayment.spplus as spplus

class SPPlustTest(TestCase):
    ntkey = '58 6d fc 9c 34 91 9b 86 3f ' \
        'fd 64 63 c9 13 4a 26 ba 29 74 1e c7 e9 80 79'

    tests = [('x=coin', 'c04f8266d6ae3ce37551cce996c751be4a95d10a'),
             ('x=coin&y=toto', 'ef008e02f8dbf5e70e83da416b0b3a345db203de'),
             ('x=wdwd%20%3Fdfgfdgd&z=343&hmac=04233b78bb5aff332d920d4e89394f505ec58a2a', '04233b78bb5aff332d920d4e89394f505ec58a2a')]

    def test_spplus(self):
        payment = spplus.Payment({'cle': self.ntkey, 'siret': '00000000000001-01'})

        for query, result in self.tests:
            self.assertEqual(spplus.sign_ntkey_query(self.ntkey, query).lower(), result)
