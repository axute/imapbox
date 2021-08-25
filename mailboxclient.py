#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import argparse
import datetime
import os
import re

from configuration import Options, Account
from message import Message


class MailboxClient:
    """Operations on a mailbox"""

    def __init__(self, account: Account, options: Options):
        self.options = options
        self.account = account
        self.mailbox = account.get_mailbox()
        typ, data = self.mailbox.select(account.remote_folder, readonly=True)
        if typ != 'OK':
            # Handle case where Exchange/Outlook uses '.' path separator when
            # reporting subfolders. Adjust to use '/' on remote.
            adjust_remote_folder = re.sub('\\.', '/', account.remote_folder)
            typ, data = self.mailbox.select(adjust_remote_folder, readonly=True)
            if typ != 'OK':
                print("MailboxClient: Could not select remote folder '%s'" % account.remote_folder)
        print(f"{data} messages found.")

    def copy_mails(self):

        n_saved = 0
        n_exists = 0

        criterion = 'ALL'

        if self.options.days:
            date = (datetime.date.today() - datetime.timedelta(self.options.days)).strftime("%d-%b-%Y")
            criterion = '(SENTSINCE {date})'.format(date=date)

        # self.mailbox.select() already done in init
        typ, data = self.mailbox.search(None, criterion)
        for num in data[0].split():
            typ, data = self.mailbox.fetch(num, '(RFC822)')
            if self.save_mail(data):
                n_saved += 1
            else:
                n_exists += 1

        return n_saved, n_exists

    def cleanup(self):
        try:
            self.mailbox.close()
        except Exception as e:
            print(e)
        self.mailbox.logout()

    def save_mail(self, data):
        for response_part in data:
            if isinstance(response_part, tuple):
                try:
                    message = Message(response_part[1], self.options.local_folder)
                    if message.exists:
                        return False
                    message.create_file_raw()
                    message.create_file_text()
                    message.create_file_html()
                    message.create_file_attachments()
                    if self.options.json:
                        message.create_file_json()

                    if self.options.wkhtmltopdf:
                        message.create_file_pdf(self.options.wkhtmltopdf)

                except Exception as e:
                    print("MailboxClient.saveEmail() failed")
                    print(e)

        return True


class Exporter:
    def run(self):
        argparser = argparse.ArgumentParser(description="Dump a IMAP folder into .eml files")
        argparser.add_argument('-l', dest='local_folder', help="Local folder where to create the email folders")
        argparser.add_argument('-d', dest='days', help="Number of days back to get in the IMAP account", type=int)
        argparser.add_argument('-w', dest='wkhtmltopdf', help="The location of the wkhtmltopdf binary")
        argparser.add_argument('-a', dest='specific_account', help="Select a specific account to backup")
        argparser.add_argument('-j', dest='json', help="Output JSON", type=bool)
        argparser.add_argument('-s', dest='local_subfolder', help="Create local subfolder like online", type=bool)
        args = argparser.parse_args()
        options = Options(args)
        account: Account
        for account in options.accounts:

            print('{}/{} (on {})'.format(account.name, account.remote_folder, account.host))

            if account.remote_folder == "__ALL__":
                basedir = options.local_folder
                for folder_name in account.get_folder_fist():
                    print("Saving folder: " + folder_name)
                    account.remote_folder = folder_name
                    if options.local_subfolder:
                        options.local_folder = os.path.join(basedir, folder_name)
                    self.safe_mails(account, options)
                options.local_folder = basedir
                account.remote_folder = "__ALL__"
            else:
                self.safe_mails(account, options)

    def safe_mails(self, account, options):
        mailbox_client = MailboxClient(account, options)
        stats = mailbox_client.copy_mails()
        mailbox_client.cleanup()
        print('{} emails created, {} emails already exists'.format(stats[0], stats[1]))
