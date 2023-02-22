#!/usr/bin/env python3

from zeep import CachingClient
from zeep.cache import SqliteCache
from zeep.transports import Transport
import os

USER = os.environ['MAGENTO_SOAP_USER']
API_KEY = os.environ['MAGENTO_SOAP_API_KEY']
MAGENTO_SOAP_WSDL = os.environ.get('MAGENTO_SOAP_WSDL')

client = CachingClient(
    MAGENTO_SOAP_WSDL,
    transport=Transport(
        cache=SqliteCache(path='./zeep-cache.sqlite')
    )
)
# client.set_ns_prefix(None, 'urn:Magento')
token = client.service.login(username=USER, apiKey=API_KEY)
result = client.service.kbankqrInvoiceMany(
    token,
    orderInfoList=[
        {'increment_id':'OR-20021207', 'amount': '10.00', 'comment':'comment jaa'},
        {'increment_id':'OR-20021206', 'amount': '10.00', 'comment':'comment jaa'},
        {'increment_id':'OR-20021205', 'amount': '10.00', 'comment':'comment jaa'}
    ]
)
print(result)
