FROM python:3.7-slim

RUN apt-get clean \
    && apt-get -y update \
    && apt-get install -y cron

COPY ./src /Main/SSLLabsReport

WORKDIR /Main/SSLLabsReport

RUN pip install -r requirements.txt && \
    chmod +x SSLLabsReport.py && \
    chmod +x start.sh

RUN mkdir /Main/logs

RUN crontab cronConfig
