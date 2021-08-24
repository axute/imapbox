#!/usr/bin/env python

import imaplib

from mailboxresource import MailboxClient


class Account:
    def __init__(self, name):
        self.name = name
        self.host = None
        self.port = 993
        self.remote_folder = 'INBOX'
        self.username = None
        self.password = None
        self.ssl = False

    def get_mailbox(self):
        if not self.ssl:
            mailbox = imaplib.IMAP4(self.host, self.port)
        else:
            mailbox = imaplib.IMAP4_SSL(self.host, self.port)
        mailbox.login(self.username, self.password)
        return mailbox

    def get_folder_fist(self):
        mailbox = self.get_mailbox()
        folder_list = mailbox.list()[1]
        mailbox.close()
        mailbox.logout()
        result = []
        try:
            folder_entry: bytes
            for folder_entry in folder_list:
                folder = folder_entry.decode().replace("/", ".").split(' "." ')[1]
                folder = folder.strip().replace('"', '').replace('\r', '').replace('\n', '')
                result.append(folder)
        except Exception as e:
            print("Couldn't clean folder list:")
            print(folder_list)
            print(e)

        return result

    def safe_mails(self, options):
        """
        :type options: options.Options
        """
        mailbox_client = MailboxClient(self, options)
        stats = mailbox_client.copy_mails()
        mailbox_client.cleanup()
        print('{} emails created, {} emails already exists'.format(stats[0], stats[1]))
