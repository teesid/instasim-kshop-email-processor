#!/usr/bin/env python3

import csv
import time
from imapclient import IMAPClient
import os
import email
from email.header import decode_header
import zeep

DOUBLE_SIGINT_TIMEOUT = 5
HOST = 'imap.gmail.com'
USERNAME = os.environ.get('GMAIL_USER')
PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')
MAIL_FROM = os.environ.get('MAIL_FROM')
MAIL_TO = os.environ.get('MAIL_TO')
PROCESSED_LABEL = 'Processed'
GMAIL_FILTER = f'in:inbox from:{MAIL_FROM} deliveredto:{MAIL_TO} has:attachment filename:csv'
print(f"The gmail filter is '{GMAIL_FILTER}'")
MAGENTO_SOAP_WSDL = os.environ.get('MAGENTO_SOAP_WSDL')
MAGENTO_SOAP_USER = os.environ.get('MAGENTO_SOAP_USER')
MAGENTO_SOAP_API_KEY = os.environ.get('MAGENTO_SOAP_API_KEY')
_soapClient = None


def process_emails(client: IMAPClient, filter: str = ''):
    """Fetch new emails and download the csv file attached to it.
    """
    ids = client.gmail_search(filter)
    print('Processing emails ...')
    if ids:
        # fetch and parse the emails and see if there are any csv files attached to them
        for msgid, data in client.fetch(ids, ['RFC822']).items():
            msg = email.message_from_bytes(data[b'RFC822'])
            for part in msg.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                if part.get('Content-Disposition') is None:
                    continue
                filename = part.get_filename()
                if decode_header(filename)[0][1] is not None:
                    filename = decode_header(filename)[0][0].decode(decode_header(filename)[0][1])
                if not filename.endswith('.csv'):
                    continue
                print("Msg ID {msgid}, found csv file:", filename)
                process_kshop_csv(part.get_payload(decode=True))
                # Mark the emails as processed
                client.move([msgid], PROCESSED_LABEL)
    else:
        print('No new transactional emails found')

def process_kshop_csv(data: bytes):
    """Process the csv file from kshop and update the orders on Magento.
    """
    # We are only interested in line 6 to n-1 of the csv onwards
    lines = data.decode('utf-8').splitlines()[5:-1]
    # Use csv.DictReader to parse the csv file
    reader = csv.DictReader(lines)

    orderInfoList = []
    for row in reader:
        print('Converted data from:', row)
        orderInfo = {
            # Convert the trarnsaction id to order increment number
            # KPSORx20021182 -> OR-20021182
            # This is because the transaction id has to start with 'KPS' and '-' is not allowed in that field.
            'increment_id': row['Transaction ID'].replace('KPSORx', 'OR-'),
            'amount': row['Paid'],
            'comment': f"KShop: {row['Date Time']}, {row['Paid']}, {row['From Account']} ({row['Source of Fund']})"
        }
        print('->', orderInfo)
        orderInfoList.append(orderInfo)

    global _soapClient
    if not _soapClient:
        print('Initializing the SOAP client for the first time.  This could take a while.')
        from zeep.cache import SqliteCache
        from zeep.transports import Transport
        _soapClient = zeep.CachingClient(
            MAGENTO_SOAP_WSDL,
            transport=Transport(
                cache=SqliteCache(path='./zeep-cache.sqlite')
            )
        )
    # TODO:For now, we just simple mindedly re-log-in every time
    sessionId = _soapClient.service.login(username=MAGENTO_SOAP_USER, apiKey=MAGENTO_SOAP_API_KEY)
    print("Calling the kbankqrInvoiceMany() SOAP endpoint")
    result = _soapClient.service.kbankqrInvoiceMany(sessionId=sessionId, orderInfoList=orderInfoList)
    print("Result:", result)


def main():
    print('Connecting ...')
    client = IMAPClient(HOST)
    print('Connected.  Logging in ...')
    client.login(USERNAME, PASSWORD)
    print('Logged in, selecting INBOX ...')
    client.select_folder("INBOX")
    # Check if the PROCESSED_LABEL folder exists, if not, create it
    if not client.folder_exists(PROCESSED_LABEL):
        print(f'Creating folder {PROCESSED_LABEL} to move the processed emails to')
        client.create_folder(PROCESSED_LABEL)
    # Processing any new emails for the first time
    process_emails(client, GMAIL_FILTER)

    print("Connection is now in IDLE mode, send yourself an email or quit with ^c")

    do_break = False
    while True:
        client.idle()
        responses = None
        # Note that we do not loop forever to avoid the server closing the IDLE connection
        for _ in range(10):
            try:
                # Wait for up to 30 seconds for an IDLE response
                responses = client.idle_check(timeout=30)
                if responses:
                    print("Server sent:", responses)
                    break
            except KeyboardInterrupt:
                print(f'Got KeyboardInterrupt, do it again within {DOUBLE_SIGINT_TIMEOUT} seconds to exit ...')
                do_break = True
                break

        # We need to exit IDLE mode before we can do anything else
        client.idle_done()
        # We end up here either because 
        if do_break:
            # 1. we got a KeyboardInterrupt
            break
        elif responses:
            # 2. we got something from the server
            process_emails(client, GMAIL_FILTER)
        else:
            # 3. we tried idle_check enough rounds and got nothing
            pass

    client.logout()

if __name__ == '__main__':
    while True:
        try:
            main()
            # if we are here then we have the first SIGINT
            # now we wait for the second SIGINT
            time.sleep(DOUBLE_SIGINT_TIMEOUT)
        except KeyboardInterrupt:
            print('Got the 2nd KeyboardInterrupt, exiting ...')
            break
        except Exception as e:
            print(f'main() died with exception: {e}')
            print("Restarting main() in 5 seconds ...")
            time.sleep(5)

