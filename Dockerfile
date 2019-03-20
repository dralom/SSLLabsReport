FROM python:3.7-slim

RUN apt-get clean \
    && apt-get -y update \

COPY ./src /Main/SSLLabsReport

WORKDIR /Main/SSLLabsReport

RUN pip install -r requirements.txt

RUN mkdir logs

ENTRYPOINT ["python", "/Main/SSLLabsReport/SSLLabsReport.py"]
