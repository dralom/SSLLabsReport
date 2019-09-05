FROM python:3.7-slim

RUN apt-get clean \
    && apt-get -y update \
    && apt-get install -y cron supervisor dos2unix

COPY ./src /srv/SSLLabsReport

WORKDIR /srv/SSLLabsReport

RUN pip install -r requirements.txt && \
    chmod +x SSLLabsReport.py && \
    dos2unix /srv/SSLLabsReport/cronConfig && \
    dos2unix /srv/SSLLabsReport/SSLLabsReport.py && \
    mkdir /srv/logs && \
    crontab cronConfig

CMD ["/usr/bin/supervisord", "-c", "/srv/SSLLabsReport/supervisor.conf"]
