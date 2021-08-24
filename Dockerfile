FROM python:3.8-alpine
RUN apk add xvfb
# Install dependencies
RUN pip install six
RUN pip install chardet
RUN pip install pdfkit
RUN pip install unidecode
RUN pip install pyvirtualdisplay
RUN apk add --update ttf-dejavu ttf-droid ttf-freefont ttf-liberation wkhtmltopdf

# Make the data and config directory a volume
VOLUME ["/etc/imapbox/"]
VOLUME ["/var/imapbox/"]
ENV XDG_RUNTIME_DIR=/tmp/runtime-root
# Copy source files and set entry point
COPY *.py /opt/bin/
ENTRYPOINT ["python", "/opt/bin/imapbox.py"]
