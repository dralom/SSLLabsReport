FROM python:3.7-slim

RUN apt-get clean \
    && apt-get -y update \
    && apt-get install -y cron supervisor dos2unix

COPY ./src /Main/SSLLabsReport

WORKDIR /Main/SSLLabsReport

RUN pip install -r requirements.txt && \
    chmod +x SSLLabsReport.py && \
    chmod +x start.sh && \
    dos2unix /Main/SSLLabsReport/cronConfig && \
    mkdir /Main/logs && \
    crontab cronConfig

CMD ["/usr/bin/supervisord", "-c", "/Main/SSLLabsReport/supervisor.conf"]
