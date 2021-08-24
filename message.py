#!/usr/bin/env python

import datetime
import email
from email.errors import HeaderParseError
from email.utils import parseaddr
from email.header import decode_header
import re
import os
import json
import io
import mimetypes
import chardet
import html
import time
import pkgutil

import unidecode

# import pdfkit if its loader is available
has_pdfkit = pkgutil.find_loader('pdfkit') is not None
if has_pdfkit:
    import pdfkit

# email address REGEX matching the RFC 2822 spec
# from perlfaq9
#    my $atom       = qr{[a-zA-Z0-9_!#\$\%&'*+/=?\^`{}~|\-]+};
#    my $dot_atom   = qr{$atom(?:\.$atom)*};
#    my $quoted     = qr{"(?:\\[^\r\n]|[^\\"])*"};
#    my $local      = qr{(?:$dot_atom|$quoted)};
#    my $domain_lit = qr{\[(?:\\\S|[\x21-\x5a\x5e-\x7e])*\]};
#    my $domain     = qr{(?:$dot_atom|$domain_lit)};
#    my $addr_spec  = qr{$local\@$domain};
#
# Python translation

atom_rfc2822 = r"[a-zA-Z0-9_!#\$\%&'*+/=?\^`{}~|\-]+"
atom_posfix_restricted = r"[a-zA-Z0-9_#\$&'*+/=?\^`{}~|\-]+"  # without '!' and '%'
atom = atom_rfc2822
dot_atom = atom + r"(?:\." + atom + ")*"
quoted = r'"(?:\\[^\r\n]|[^\\"])*"'
local = "(?:" + dot_atom + "|" + quoted + ")"
domain_lit = r"\[(?:\\\S|[\x21-\x5a\x5e-\x7e])*\]"
domain = "(?:" + dot_atom + "|" + domain_lit + ")"
addr_spec = local + "\\@" + domain

email_address_re = re.compile('^' + addr_spec + '$')


class Message:
    """Operation on a message"""

    def __init__(self, raw, parent_directory):
        self.exists = True
        self.raw = raw
        self.msg = email.message_from_bytes(raw)
        self.parts = self.get_parts()
        self.from_ = self.get_addresses('from')
        self.from_ = ('', '') if not self.from_ else self.from_[0]
        self.tos = self.get_addresses('to')
        self.ccs = self.get_addresses('cc')
        self.subject = self.get_header(self.msg.get('Subject', ''))
        self.text_content = self.get_content_text()
        self.html_content = self.get_content_html()
        self.directory = self.get_target_directory(parent_directory)
        self.file_eml = os.path.join(self.directory, 'message.eml')
        self.file_json = os.path.join(self.directory, 'message.json')
        self.file_txt = os.path.join(self.directory, 'message.txt')
        self.file_html = os.path.join(self.directory, 'message.html')
        self.file_pdf = os.path.join(self.directory, 'message.pdf')

    def get_target_directory(self, parent_directory):
        local_date = datetime.datetime.fromtimestamp(email.utils.mktime_tz(email.utils.parsedate_tz(self.msg["Date"])))
        timestamp = local_date.strftime('%Y%m%d%H%M%S')
        year = local_date.strftime('%Y')
        from_ = self.from_[0] if self.from_[0] != '' else self.from_[1]
        directory = os.path.join(parent_directory, year, timestamp+"_"+re.sub('[^\\w_\\d.\\-]', '', from_.replace('@', '_at_').replace(' ', '_')))
        directory = unidecode.unidecode(directory.strip())
        if not os.path.exists(directory):
            self.exists = False
            os.makedirs(directory)
        return directory

    def get_header(self, header_text):
        """Decode header_text if needed"""
        try:
            headers = decode_header(header_text)
        except HeaderParseError:
            # This already append in email.base64mime.decode()
            # instead return a sanitized ascii string
            return header_text.encode('ascii', 'replace').decode('ascii')
        else:
            result = []
            for i, (text, charset) in enumerate(headers):
                result.append(str(text, charset) if charset else str(text))
            return u"".join(result)

    def get_addresses(self, prop):
        """retrieve From:, To: and Cc: addresses"""
        addrs = email.utils.getaddresses(self.msg.get_all(prop, []))
        for i, (name, addr) in enumerate(addrs):
            if not name and addr:
                # only one string! Is it the address or is it the name ?
                # use the same for both and see later
                name = addr

            try:
                # address must be ascii only
                addr = addr.encode('ascii')
            except UnicodeError:
                addr = ''
            else:
                # address must match adress regex
                if not email_address_re.match(addr.decode("utf-8")):
                    addr = ''
            if not isinstance(addr, str):
                # Python 2 imaplib returns a bytearray,
                # Python 3 imaplib returns a str.
                addrs[i] = (self.get_header(name), addr.decode("utf-8"))
        return addrs

    def normalize_date(self, datestr):
        if not datestr:
            print("No date for '%s'. Using Unix Epoch instead." % self.directory)
            datestr = "Thu, 1 Jan 1970 00:00:00 +0000"
        t = email.utils.parsedate_tz(datestr)
        timeval = time.mktime(t[:-1])
        date = email.utils.formatdate(timeval, True)
        utc = time.gmtime(email.utils.mktime_tz(t))
        rfc2822 = '{} {:+03d}00'.format(date[:-6], t[9] // 3600)
        iso8601 = time.strftime('%Y%m%dT%H%M%SZ', utc)

        return rfc2822, iso8601

    def create_file_json(self):

        parts = self.get_parts()
        attachments = []
        for afile in parts['files']:
            attachments.append(afile[1])

        rfc2822, iso8601 = self.normalize_date(self.msg['Date'])

        with io.open(self.file_json, 'w', encoding='utf8') as json_file:
            data = json.dumps({
                'Id': self.msg['Message-Id'],
                'Subject': self.subject,
                'From': self.from_,
                'To': self.tos,
                'Cc': self.ccs,
                'Date': rfc2822,
                'Utc': iso8601,
                'Attachments': attachments,
                'WithHtml': len(self.html_content) > 0,
                'WithText': len(self.text_content) > 0,
                'Body': self.text_content
            }, indent=4, ensure_ascii=False)

            json_file.write(data)

            json_file.close()

    def create_file_raw(self):
        f = open(self.file_eml, 'wb')
        f.write(self.raw)
        f.close()

    def get_part_charset(self, part):
        if part.get_content_charset() is None:
            try:
                return chardet.detect(part.as_bytes())['encoding']
            except UnicodeEncodeError:
                string = part.as_string()
                array = bytearray(string, 'utf-8')
                return chardet.detect(array)['encoding']
        return part.get_content_charset()

    def get_content_text(self):
        text_content = ''
        for part in self.parts['text']:
            raw_content = part.get_payload(decode=True)
            charset = self.get_part_charset(part)
            text_content += raw_content.decode(charset, "replace")

        return text_content

    def create_file_text(self):
        if self.text_content != '':
            with open(self.file_txt, 'wb') as fp:
                fp.write(bytearray(self.text_content, 'utf-8'))

    def get_content_html(self):
        html_content = ''

        for part in self.parts['html']:
            raw_content = part.get_payload(decode=True)
            charset = self.get_part_charset(part)
            html_content += raw_content.decode(charset, "replace")

        m = re.search('<body[^>]*>(.+)</body>', html_content, re.S | re.I)
        if m is not None:
            html_content = m.group(1)

        return html_content

    def create_file_html(self):
        if self.html_content != '':
            utf8_content = self.html_content
            for img in self.parts['embed_images']:
                pattern = 'src=["\']cid:%s["\']' % (re.escape(img[0]))
                path = os.path.join('attachments', img[1])
                utf8_content = re.sub(pattern, 'src="%s"' % path, utf8_content, 0, re.S | re.I)

            subject = self.subject
            fromname = self.from_[0]

            utf8_content = """<!doctype html>
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <meta name="author" content="%s">
    <title>%s</title>
</head>
<body>
%s
</body>
</html>""" % (html.escape(fromname), html.escape(subject), utf8_content)

            with open(self.file_html, 'wb') as fp:
                fp.write(bytearray(utf8_content, 'utf-8'))

    def sanitize_filename(self, filename):
        keepcharacters = (' ', '.', '_', '-')
        return "".join(c for c in filename if c.isalnum() or c in keepcharacters).rstrip()

    def get_parts(self):
        counter = 1
        message_parts = {
            'text': [],
            'html': [],
            'embed_images': [],
            'files': []
        }

        for part in self.msg.walk():
            # multipart/* are just containers
            if part.get_content_maintype() == 'multipart':
                continue

            # Applications should really sanitize the given filename so that an
            # email message can't be used to overwrite important files
            filename = part.get_filename()
            if not filename:
                if part.get_content_type() == 'text/plain':
                    message_parts['text'].append(part)
                    continue

                if part.get_content_type() == 'text/html':
                    message_parts['html'].append(part)
                    continue

                ext = mimetypes.guess_extension(part.get_content_type())
                if not ext:
                    # Use a generic bag-of-bits extension
                    ext = '.bin'
                filename = 'part-%03d%s' % (counter, ext)

            filename = self.sanitize_filename(filename)

            content_id = part.get('Content-Id')
            if content_id:
                content_id = content_id[1:][:-1]
                message_parts['embed_images'].append((content_id, filename))

            counter += 1
            message_parts['files'].append((part, filename))

        return message_parts

    def create_file_attachments(self):
        if self.parts['files']:
            attdir = os.path.join(self.directory, 'attachments')
            if not os.path.exists(attdir):
                os.makedirs(attdir)
            else:
                return False
            for afile in self.parts['files']:
                payload = afile[0].get_payload(decode=True)
                if payload:
                    with open(os.path.join(attdir, afile[1]), 'wb') as fp:
                        fp.write(payload)
                        fp.close()

    def create_file_pdf(self, wkhtmltopdf):
        if has_pdfkit:
            config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf)
            if os.path.exists(self.file_html):
                try:
                    pdfkit.from_file(self.file_html, self.file_pdf, configuration=config)
                except Exception as e:
                    print('pdfkit: ')
                    print(e)

            else:
                print("Couldn't create PDF message from html")
                if os.path.exists(self.file_txt):
                    try:
                        pdfkit.from_file(self.file_txt, self.file_pdf, configuration=config)
                    except Exception as e:
                        print('pdfkit: ')
                        print(e)
                else:
                    print("Couldn't create PDF message from txt")
        else:
            print("Couldn't create PDF message, since \"pdfkit\" module isn't installed.")
