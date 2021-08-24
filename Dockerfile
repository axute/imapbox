FROM python:3.8-alpine

# Install dependencies
RUN apk add --update ttf-dejavu ttf-droid ttf-freefont ttf-liberation wkhtmltopdf xvfb tini tzdata
RUN pip install six
RUN pip install chardet
RUN pip install pdfkit
RUN pip install unidecode
RUN pip install pyvirtualdisplay
RUN pip install crython

# basic environment variables for system and wkhtmltopdf
ENV XDG_RUNTIME_DIR=/tmp/runtime-root
ENV TZ=Europe/Berlin
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=UTF-8

# environment variables for IMAPBOX
ENV IMAPBOX_WKHTMLTOPDF=/usr/bin/wkhtmltopdf
ENV IMAPBOX_LOCAL_FOLDER=/var/imapbox/
ENV IMAPBOX_DAYS=10
ENV IMAPBOX_CRON_EXPR="@minutely"

# Make the data and config directory a volume
VOLUME ["/etc/imapbox/"]
VOLUME ["/var/imapbox/"]

# Copy source files and set entry point
COPY *.py /opt/bin/
WORKDIR /var/imapbox
CMD ["python", "/opt/bin/cron.py"]
ENTRYPOINT ["/sbin/tini", "--"]
