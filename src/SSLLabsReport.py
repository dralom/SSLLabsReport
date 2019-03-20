#!/usr/bin/env python

import datetime
import logging.config
import os
import smtplib
import time

from jinja2 import Template
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

START_TIME = datetime.datetime.now()

API = 'https://api.ssllabs.com/api/v3/analyze'

# https://www.ssllabs.com/ssltest/analyze.html?d=www.dralom.eu&hideResults=on

logging.config.fileConfig('logging.conf', disable_existing_loggers=False)
lg = logging.getLogger()

SLEEP_TIME = 15
WAIT_TIME = 60
MAX_RETRIES = 15


def send_report(messageHTML="", messageTXT=""):
    try:
        smtp_server = os.environ['SMTPSERVER']
        smtp_port = os.environ['SMTPPORT']
        smtp_origin = os.environ['SMTPORIGIN']
        smtp_destination = os.environ['SMTPDESTINATION']
    except KeyError as e:
        lg.exception("Mandatory environment variable not defined: {}".format(e))

    try:
        smtp_user = os.environ['SMTPUSER']
    except KeyError as e:
        smtp_user = None

    try:
        smtp_password = os.environ['SMTPPASSWORD']
    except KeyError as e:
        smtp_password = None

    server = smtplib.SMTP(smtp_server, smtp_port)
    if smtp_user is not None and smtp_password is not None:
        server.login(smtp_user, smtp_password)

    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'SSL Labs Report'
    msg['From'] = smtp_origin
    msg['To'] = smtp_destination

    part1 = MIMEText(messageTXT, 'plain')
    part2 = MIMEText(messageHTML, 'html')

    msg.attach(part1)
    msg.attach(part2)

    server.sendmail(smtp_origin, smtp_destination, msg.as_string())


def api_request(payload_content: dict = {}) -> dict:
    try:
        r = requests.get(API, params=payload_content)
    except requests.exceptions.RequestException:
        lg.exception('Request failed for domain {}'.format(domain))
        return {'status': 'ERROR'}
    if r.status_code != 200:
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
domains_lookup = {}

for domain in domains:
    domain_http_lookup = "https://www.ssllabs.com/ssltest/analyze.html?d={}&hideResults=on".format(domain)
    domains_lookup[domain] = domain_http_lookup

for domain in domains:
    lg.info("Initiating scan for domain: {}".format(domain))
    payload = {
        'host': domain,
        'publish': 'off',
        'startNew': 'off',
        'fromCache': 'on',
        'all': 'done'
    }

    result = api_request(payload_content=payload)
    for i in range(0, 15):
        if result['status'] == 'ERROR':
            lg.exception("Request returned ERROR status. Attempt {} of {}. Waiting {} seconds and trying again.".format(
                i, MAX_RETRIES, WAIT_TIME))
            time.sleep(WAIT_TIME)
            result = api_request(payload_content=payload)
        else:
            break
    if result['status'] == 'ERROR':
        message = "API ERROR! {} failed attempts for domain {}".format(MAX_RETRIES, domain)
        lg.exception(message)
        domains_failed.append(domain)
    else:
        if 'endpoints' in result.keys():
            lg.info("Current status is {}, progress is {}".format(result['status'],
                                                                  result['endpoints'][0]['progress']))
        else:
            lg.info("Current status is {}".format(result['status']))
        lg.info("Waiting for scan of domain {} to complete.".format(domain))
        payload['startNew'] = 'off'
        while result['status'] != 'READY' and result['status'] != 'ERROR':
            lg.info("Sleeping for {} seconds.".format(SLEEP_TIME))
            time.sleep(SLEEP_TIME)
            result = api_request(payload_content=payload)
            if 'endpoints' in result.keys():
                lg.info("Current status is {}, progress is {}".format(result['status'],
                                                                      result['endpoints'][0]['progress']))
            else:
                lg.info("Current status is {}".format(result['status']))

        if result['status'] == 'READY':
            lg.info("Scan of domain {} complete with grade {}".format(domain, result['endpoints'][0]['grade']))
            full_results[domain] = result
            domains_complete.append(domain)
        else:
            message = "Scan of domain {} failed.".format(domain)
            lg.exception(message)
            domains_failed.append(domain)

simplified_results = {}
for domain in domains_complete:
    simplified_results[domain] = full_results[domain]['endpoints'][0]['grade']

# TODO: email report and docker

with open("EmailTemplate.html.jinja2") as f:
    template = Template(f.read())
bodyHTML = template.render(domain_total=len(domains),
                           domain_success=len(domains_complete),
                           domain_failed=len(domains_failed),
                           domain_results=simplified_results,
                           domain_list_failed=domains_failed,
                           domain_lookup=domains_lookup
                           )
with open("EmailTemplate.txt.jinja2") as f:
    template = Template(f.read())
bodyTXT = template.render(domain_total=len(domains),
                          domain_success=len(domains_complete),
                          domain_failed=len(domains_failed),
                          domain_results=simplified_results,
                          domain_list_failed=domains_failed,
                          domain_lookup=domains_lookup
                          )

send_report(bodyHTML, bodyTXT)