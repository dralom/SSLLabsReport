#!/usr/bin/env python

import datetime
import json
import logging.config
import os
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from jinja2 import Template

START_TIME = datetime.datetime.now()

os.chdir("/Main/SSLLabsReport")

API = 'https://api.ssllabs.com/api/v3/analyze'

logging.config.fileConfig('logging.conf', disable_existing_loggers=False)
lg = logging.getLogger()

SLEEP_TIME = 15
WAIT_TIME = 15
MAX_RETRIES = 60

CONFIG_FILE = os.path.join(os.getcwd(), "config.json")

# Load config settings
if os.path.isfile(CONFIG_FILE):
    try:
        with open(CONFIG_FILE) as f:
            config = json.load(f)
    except Exception as e:
        lg.exception("Exception encountered loading config file: {}".format(e))

    if not all(k in config.keys() for k in ("SMTPSERVER",
                                             "SMTPPORT",
                                             "SMTPORIGIN",
                                             "SMTPDESTINATION")):
        lg.exception("Config file does not contain minimum configuration infomrmation.\n"
                     "Settings provided are: {}".format(config.keys()))

def send_report(messageHTML="", messageTXT=""):
    try:
        smtp_server = config['SMTPSERVER']
        smtp_port = config['SMTPPORT']
        smtp_origin = config['SMTPORIGIN']
        smtp_destination = config['SMTPDESTINATION']
    except KeyError as e:
        lg.exception("Mandatory environment variable not defined: {}".format(e))

    server = smtplib.SMTP(smtp_server, smtp_port)

    if all(k in config.keys() for k in ("SMTPUSER",
                                        "SMTPPASSWORD")):
        server.login(config["SMTPUSER"], config["SMTPPASSWORD"])

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
domains_fail_message = {}
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
        'maxAge': 2,
        'all': 'done'
    }

    result = api_request(payload_content=payload)
    for i in range(0, MAX_RETRIES):
        if result['status'] == 'ERROR':
            if 'statusMessage' in result.keys():
                if result['statusMessage'] == 'Unable to resolve domain name':
                    break
            lg.exception("Request returned ERROR status. Attempt {} of {}. Waiting {} seconds and trying again.".format(
                i, MAX_RETRIES, WAIT_TIME))
            time.sleep(WAIT_TIME)
            result = api_request(payload_content=payload)
        else:
            break
    if result['status'] == 'ERROR':
        if i > 0:
            message = "API ERROR! {} failed attempts for domain {}".format(i, domain)
        else:
            domains_failed.append(domain)
            if 'errors' in result.keys():
                lg.exception(result['errors'][0]['message'])
                domains_fail_message[domain] = result['errors'][0]['message']
            elif 'statusMessage' in result.keys():
                lg.exception(message)
                domains_fail_message[domain] = result['statusMessage']
    else:
        if 'endpoints' in result.keys():
            if 'progress' in result['endpoints'][0].keys():
                progress = result['endpoints'][0]['progress']
            else:
                progress = "unknown"
            lg.info("Current status is {}, progress is {}".format(result['status'],
                                                                  progress))
        else:
            lg.info("Current status is {}".format(result['status']))
        lg.info("Waiting for scan of domain {} to complete.".format(domain))
        payload['startNew'] = 'off'
        while result['status'] != 'READY' and result['status'] != 'ERROR':
            lg.info("Sleeping for {} seconds.".format(SLEEP_TIME))
            time.sleep(SLEEP_TIME)
            result = api_request(payload_content=payload)
            if 'endpoints' in result.keys():
                if 'progress' in result['endpoints'][0].keys():
                    progress = result['endpoints'][0]['progress']
                else:
                    progress = "unknown"
                lg.info("Current status is {}, progress is {}".format(result['status'],
                                                                      progress))
            else:
                lg.info("Current status is {}".format(result['status']))

        if result['status'] == 'READY' and 'grade' in result['endpoints'][0].keys():
            lg.info("Scan of domain {} complete with grade {}".format(domain, result['endpoints'][0]['grade']))
            full_results[domain] = result
            domains_complete.append(domain)
        else:
            message = "Scan of domain {} failed.".format(domain)
            lg.exception(message)
            domains_failed.append(domain)
            if 'errors' in result.keys():
                lg.exception(result['errors'][0]['message'])
                domains_fail_message[domain] = result['errors'][0]['message']
            elif 'statusMessage' in result.keys():
                lg.exception(result['statusMessage'])
                domains_fail_message[domain] = result['statusMessage']

simplified_results = {}
for domain in domains_complete:
    simplified_results[domain] = full_results[domain]['endpoints'][0]['grade']

with open("EmailTemplate.html.jinja2") as f:
    template = Template(f.read())
bodyHTML = template.render(domain_total=len(domains),
                           domain_success=len(domains_complete),
                           domain_failed=len(domains_failed),
                           domain_results=simplified_results,
                           domain_list_failed=domains_failed,
                           domain_lookup=domains_lookup,
                           domain_fail_message=domains_fail_message
                           )
with open("EmailTemplate.txt.jinja2") as f:
    template = Template(f.read())
bodyTXT = template.render(domain_total=len(domains),
                          domain_success=len(domains_complete),
                          domain_failed=len(domains_failed),
                          domain_results=simplified_results,
                          domain_list_failed=domains_failed,
                          domain_lookup=domains_lookup,
                          domain_fail_message=domains_fail_message
                          )

send_report(bodyHTML, bodyTXT)
lg.info("Report email sent.")
