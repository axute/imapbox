#!/usr/bin/env python

from __future__ import print_function

import datetime
import re

from message import Message


class MailboxClient:
    """Operations on a mailbox"""

    def __init__(self, account, options):
        """
        :type account: account.Account
        :type options: options.Options
        """
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
        self.mailbox.close()
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
