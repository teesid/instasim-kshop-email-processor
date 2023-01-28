#!/bin/bash

source .env
poetry run python3 -m imapclient.interact -H "imap.gmail.com" -u "$GMAIL_USER" -p "$GMAIL_APP_PASSWORD"