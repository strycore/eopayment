Python module to interface with French's bank online credit card processing
services.

Services supported are:
	ATOS/SIP used by:
	BNP under the name Mercanet,
	Banque Populaire (before 2010/2011) under the name Cyberplus,
	CCF under the name Elysnet,
	HSBC under the name Elysnet,
	Crédit Agricole under the name e-Transactions,
	La Banque Postale under the name ScelliusNet,
	LCL under the name Sherlocks,
	Société Générale under the name Sogenactif
	and Crédit du Nord under the name Webaffaires,
	SystemPay by Banque Populaire (since 2010/2011)
	and SPPlus by Caisse d'épargne.

You can emit payment request under a simple API which takes as input a
dictionnary as configuration and an amount to pay. You get back a
transaction_id. Another unique API allows to handle the notifications coming
from those services, reporting whether the transaction was successful and which
one it was. The full content (which is specific to the service) is also
reported for logging purpose.

For SystemPay and SPPlus the module is totally independent from the respective
implementation distributed by the Bank, but for ATOS/SIPS the kit distributed
by the bank is also needed as the protocol created by ATOS is proprietary and
not documented.

The spplus module also depend upon the python Crypto library for DES decoding
of the merchant key.
