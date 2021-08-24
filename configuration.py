#!/usr/bin/env python
# -*- coding: utf-8 -*-

import imaplib
import getpass
import os

from six.moves import configparser


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


class Options:
    def __init__(self, args):
        self.args = args
        self.days = int(os.getenv('IMAPBOX_DAYS', None)) if os.getenv('IMAPBOX_DAYS') else None
        self.local_folder = os.getenv('IMAPBOX_LOCAL_FOLDER', '.')
        self.wkhtmltopdf = os.getenv('IMAPBOX_WKHTMLTOPDF', None)
        self.json = bool(os.getenv('IMAPBOX_JSON')) if os.getenv('IMAPBOX_JSON') else True
        self.accounts: [Account]
        self.accounts = []
        self.load_config()

    def load_config(self):
        config = configparser.ConfigParser(allow_no_value=True)
        config.read([
            './config.cfg',
            './test/config.cfg',
            os.path.expanduser('~/.config/imapbox/config.cfg'),
            '/etc/imapbox/config.cfg',
            os.path.join(self.local_folder, 'config.cfg'),
        ])
        if config.has_section('imapbox'):
            if config.has_option('imapbox', 'days'):
                self.days = config.getint('imapbox', 'days')

            if config.has_option('imapbox', 'local_folder'):
                self.local_folder = os.path.expanduser(config.get('imapbox', 'local_folder'))

            if config.has_option('imapbox', 'wkhtmltopdf'):
                self.wkhtmltopdf = os.path.expanduser(config.get('imapbox', 'wkhtmltopdf'))

            if config.has_option('imapbox', 'json'):
                self.json = os.path.expanduser(config.get('imapbox', 'json'))
        for section in config.sections():

            if 'imapbox' == section:
                continue

            if self.args.specific_account and (self.args.specific_account != section):
                continue
            account = Account(section)

            if config.has_option(section, 'host'):
                account.host = config.get(section, 'host')

            if config.has_option(section, 'username'):
                account.username = config.get(section, 'username')

            if config.has_option(section, 'port'):
                account.port = config.get(section, 'port')

            if config.has_option(section, 'password'):
                account.password = config.get(section, 'password')
            else:
                prompt = ('Password for ' + account.username + ':' + account.host + ': ')
                account.password = getpass.getpass(prompt=prompt)

            if config.has_option(section, 'ssl'):
                if config.get(section, 'ssl').lower() == "true":
                    account.ssl = True

            if config.has_option(section, 'remote_folder'):
                account.remote_folder = config.get(section, 'remote_folder')

            if account.host is None or account.username is None or account.password is None:
                print('missing host/username/password for '+section)
                continue

            self.accounts.append(account)

        if self.args.local_folder:
            self.local_folder = self.args.local_folder

        if self.args.days:
            self.days = self.args.days

        if self.args.wkhtmltopdf:
            self.wkhtmltopdf = self.args.wkhtmltopdf

        if self.args.json:
            self.json = self.args.json

        print('days: {}, local_folder: {}, wkhtmltopdf: {}, json: {}'.format(self.days, self.local_folder, self.wkhtmltopdf, self.json))
