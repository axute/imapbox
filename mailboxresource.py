#!/usr/bin/env python
#-*- coding:utf-8 -*-

from __future__ import print_function

import imaplib, email
import re
import os
import hashlib
from message import Message
import datetime



class MailboxClient:
    """Operations on a mailbox"""

    def __init__(self, host, port, username, password, remote_folder, options):
        self.days = options['days']
        self.local_folder = options['local_folder']
        self.wkhtmltopdf = options['wkhtmltopdf']
        self.json = options['json']

        self.mailbox = imaplib.IMAP4_SSL(host, port)
        self.mailbox.login(username, password)
        typ, data = self.mailbox.select(remote_folder, readonly=True)
        if typ != 'OK':
            # Handle case where Exchange/Outlook uses '.' path separator when
            # reporting subfolders. Adjust to use '/' on remote.
            adjust_remote_folder = re.sub('\.', '/', remote_folder)
            typ, data = self.mailbox.select(adjust_remote_folder, readonly=True)
            if typ != 'OK':
                print("MailboxClient: Could not select remote folder '%s'" % remote_folder)
        print(f"{data} messages found.")

    def copy_emails(self):

        n_saved = 0
        n_exists = 0

        criterion = 'ALL'

        if self.days:
            date = (datetime.date.today() - datetime.timedelta(self.days)).strftime("%d-%b-%Y")
            criterion = '(SENTSINCE {date})'.format(date=date)

        # self.mailbox.select() already done in init
        typ, data = self.mailbox.search(None, criterion)
        for num in data[0].split():
            typ, data = self.mailbox.fetch(num, '(RFC822)')
            if self.saveEmail(data):
                n_saved += 1
            else:
                n_exists += 1

        return (n_saved, n_exists)

    def cleanup(self):
        self.mailbox.close()
        self.mailbox.logout()

    def saveEmail(self, data):
        for response_part in data:
            if isinstance(response_part, tuple):
                # parse a bytes email into a message object
                msg = email.message_from_bytes(response_part[1])
                # print (msg)
                # decode the email subject
                try:
                    subject = email.header.decode_header(msg["Subject"])[0][0]
                    if isinstance(subject, bytes):
                        # if it's a bytes, decode to str
                        subject = subject.decode()
                except:
                    #there may be no subject
                    subject=""

                local_date = datetime.datetime.fromtimestamp(email.utils.mktime_tz(email.utils.parsedate_tz(msg["Date"])))
                timestamp = local_date.strftime('%Y%m%d%H%M%S')
                year = local_date.strftime('%Y')
                directory = os.path.join(self.local_folder, year, timestamp+" "+subject[:50])
                directory = unidecode.unidecode(directory.strip())
                print(directory)
                if os.path.exists(directory):
                    return False
                os.makedirs(directory)

                try:
                    message = Message(directory, msg)
                    message.createRawFile(data[0][1])
                    if self.json == True:
                        message.createMetaFile()
                    message.extractAttachments()

                    if self.wkhtmltopdf:
                        message.createPdfFile(self.wkhtmltopdf)

                except Exception as e:
                    # ex: Unsupported charset on decode
                    print(directory)
                    if hasattr(e, 'strerror'):
                        print("MailboxClient.saveEmail() failed:", e.strerror)
                    else:
                        print("MailboxClient.saveEmail() failed")
                        print(e)

        return True

def save_emails(account, options):
    mailbox = MailboxClient(account['host'], account['port'], account['username'], account['password'], account['remote_folder'], options)
    stats = mailbox.copy_emails()
    mailbox.cleanup()
    print('{} emails created, {} emails already exists'.format(stats[0], stats[1]))

def get_folder_fist(account):
    if not account['ssl']:
        mailbox = imaplib.IMAP4(account['host'], account['port'])
    else:
        mailbox = imaplib.IMAP4_SSL(account['host'], account['port'])
    mailbox.login(account['username'], account['password'])
    folder_list = mailbox.list()[1]
    mailbox.logout()

    try:
        folder_list = [folder_entry.decode().replace("/",".").split(' "." ')[1].strip().replace('"','').replace('\r','').replace('\n','') for folder_entry in folder_list]
    except:
        print("Couldn't clean folder list:")
        print(folder_list)
    return folder_list
