#!/usr/bin/env python

import argparse
import os

from options import Options


def main():
    argparser = argparse.ArgumentParser(description="Dump a IMAP folder into .eml files")
    argparser.add_argument('-l', dest='local_folder', help="Local folder where to create the email folders")
    argparser.add_argument('-d', dest='days', help="Number of days back to get in the IMAP account", type=int)
    argparser.add_argument('-w', dest='wkhtmltopdf', help="The location of the wkhtmltopdf binary")
    argparser.add_argument('-a', dest='specific_account', help="Select a specific account to backup")
    argparser.add_argument('-j', dest='json', help="Output JSON")
    args = argparser.parse_args()
    options = Options(args)

    for account in options.accounts:

        print('{}/{} (on {})'.format(account.name, account.remote_folder, account.host))

        if account.remote_folder == "__ALL__":
            basedir = options.local_folder
            for folder_entry in account.get_folder_fist():
                folder_name = folder_entry.decode().replace("/", ".").split(' "." ')
                print("Saving folder: " + folder_name[1])
                account.remote_folder = folder_name[1]
                options.local_folder = os.path.join(basedir, account.remote_folder)
                account.safe_mails(options)
        else:
            account.safe_mails(options)


if __name__ == '__main__':
    main()
