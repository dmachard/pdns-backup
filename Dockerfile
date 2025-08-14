FROM python:3.13.6-alpine

LABEL name="Backup tool for PowerDNS database " \
      description="Backup tool for PowerDNS database " \
      url="https://github.com/dmachard/python-pdnsbackup" \
      maintainer="d.machard@gmail.com"

WORKDIR /home/pdnsbackup
COPY . /home/pdnsbackup/

RUN apk update \
    && adduser -D pdnsbackup \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

USER pdnsbackup

ENTRYPOINT ["python", "-c", "import pdnsbackup; pdnsbackup.run();"]