#!/usr/bin/env python

import datetime
import logging.config
import os
import smtplib
import time

import requests

START_TIME = datetime.datetime.now()

API = 'https://api.ssllabs.com/api/v3/analyze'

# https://www.ssllabs.com/ssltest/analyze.html?d=www.dralom.eu&hideResults=on

logging.config.fileConfig('logging.conf', disable_existing_loggers=False)
lg = logging.getLogger()

WAIT_TIME = 60
MAX_RETRIES = 15


def send_report(message=""):
    smtp_server = os.environ['SMTPSERVER']
    smtp_port = os.environ['SMTPPORT']
    smtp_user = os.environ['SMTPUSER']
    smtp_password = os.environ['SMTPPASSWORD']
    smtp_origin = os.environ['SMTPORIGIN']
    smtp_destination = os.environ['SMTPDESTINATION']

    server = smtplib.SMTP(smtp_server, smtp_port)
    if smtp_user and smtp_password:
        server.login(smtp_user, smtp_password)

    server.sendmail(smtp_origin, smtp_destination, message)


def api_request(payload_content: dict = {}) -> dict:
    try:
        r = requests.get(API, params=payload_content)
    except requests.exceptions.RequestException:
        lg.exception('Request failed for domain {}'.format(domain))
        return {'status': 'ERROR'}
    data = r.json()
    return data


with open("domains.txt") as f:
    lines = f.readlines()
domains = [x.strip() for x in lines]

full_results = {}
domains_complete = []
domains_failed = []

for domain in domains:
    lg.info("Initiating scan for domain: {}".format(domain))
    payload = {
        'host': domain,
        'publish': 'off',
        'startNew': 'on',
        'fromCache': 'off',
        'all': 'done'
    }

    result = api_request(payload_content=payload)
    for i in range(0, 15):
        if result['status'] is 'ERROR':
            lg.exception("Request returned ERROR status. Attempt {} of {}. Waiting {} seconds and trying again.".format(
                i, MAX_RETRIES, WAIT_TIME))
            time.sleep(60)
            result = api_request(payload_content=payload)
    if result['status'] is 'ERROR':
        message = "API ERROR! {} failed attempts for domain {}".format(MAX_RETRIES, domain)
        lg.exception(message)
        domains_failed.append(domain)
    else:
        lg.info("Waiting for scan of domain {} to complete.".format(domain))
        payload['startNew'] = 'off'
        while result['status'] is not 'READY' and result['statts'] is not 'ERROR':
            time.sleep(30)
            result = api_request(payload_content=payload)
        if result['status'] is 'READY':
            lg.info("Scan of domain {} complete with grade {}".format(domain, result['endpoints'][0]['grade']))
            full_results[domain] = result
            domains_complete.append(domain)
        else:
            message = "Scan of domain {} failed.".format(domain)
            lg.exception(message)
            domains_failed.append(domain)

# TODO: email report and docker