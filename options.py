#!/usr/bin/env python

import getpass
import os

from six.moves import configparser

from account import Account


class Options:
    def __init__(self, args):
        self.args = args
        self.days = None
        self.local_folder = '.'
        self.wkhtmltopdf = None
        self.json = True
        self.accounts: [Account]
        self.accounts = []
        self.loadConfig()

    def loadConfig(self):
        config = configparser.ConfigParser(allow_no_value=True)
        config.read(['./config.cfg', '/etc/imapbox/config.cfg', os.path.expanduser('~/.config/imapbox/config.cfg'), './test/config.cfg'])
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
