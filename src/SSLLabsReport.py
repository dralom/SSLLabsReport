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
    smtp_server = ""
    smtp_port = ""
    smtp_origin = ""
    smtp_destination = ""
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


def send_error_notification(errorMessage=''):
    smtp_server = ""
    smtp_port = ""
    smtp_origin = ""
    smtp_destination = ""
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

    err_msg = "ERROR Encountered with SSL Labs Report script.\nError message: {}".format(errorMessage)
    part1 = MIMEText(err_msg, 'plain')

    msg.attach(part1)

    server.sendmail(smtp_origin, smtp_destination, msg.as_string())


def log_error(message):
    lg.exception(message)
    send_error_notification(message)


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
domains = [x.strip() for x in lines if x.strip() != '']

domains_data = {}
full_results = {}
domains_complete = []
domains_failed = []

domains_data['domains'] = {}

for domain in domains:
    domain_api_lookup = "https://www.ssllabs.com/ssltest/analyze.html?d={}&hideResults=on".format(domain)
    domains_data['domains'][domain] = {}
    domains_data['domains'][domain]['lookup'] = domain_api_lookup

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
    retry_attempt = 0
    for retry_attempt in range(0, MAX_RETRIES):
        if result['status'] == 'ERROR':
            if 'statusMessage' in result.keys():
                if result['statusMessage'] == 'Unable to resolve domain name':
                    break
            lg.exception("Request returned ERROR status. Attempt {} of {}. Waiting {} seconds and trying again.".format(
                retry_attempt, MAX_RETRIES, WAIT_TIME))
            time.sleep(WAIT_TIME)
            result = api_request(payload_content=payload)
        else:
            break
    if result['status'] == 'ERROR':
        message = "Unknown failure."
        if retry_attempt > 0:
            message = "API ERROR! {} failed attempts for domain {}".format(retry_attempt, domain)
        else:
            domains_failed.append(domain)
            if 'errors' in result.keys():
                lg.exception(result['errors'][0]['message'])
                domains_data['domains'][domain]['fail_message'] = result['errors'][0]['message']
            elif 'statusMessage' in result.keys():
                lg.exception(message)
                domains_data['domains'][domain]['fail_message'] = result['statusMessage']
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
            domains_data['domains'][domain]['full_results'] = result
            domains_complete.append(domain)
        else:
            message = "Scan of domain {} failed.".format(domain)
            lg.exception(message)
            domains_failed.append(domain)
            if 'errors' in result.keys():
                lg.exception(result['errors'][0]['message'])
                domains_data['domains'][domain]['fail_message'] = result['errors'][0]['message']
            elif 'statusMessage' in result.keys():
                lg.exception(result['statusMessage'])
                domains_data['domains'][domain]['fail_message'] = result['statusMessage']

for domain in domains_complete:

    domains_data['domains'][domain]['grade'] = full_results[domain]['endpoints'][0]['grade']
    protocol_str = ""
    for protocol in full_results[domain]['endpoints'][0]['details']['protocols']:
        if protocol_str != "":
            protocol_str += ", "
        protocol_str += protocol['name'] + protocol['version']
    domains_data['domains'][domain]['protocols'] = protocol_str

simplified_results = {}
for domain in domains_complete:
    simplified_results[domain] = full_results[domain]['endpoints'][0]['grade']

csvAttachment = "Domain,Grade,SupportedProtocols"

domains_data['complete_list'] = domains_complete
domains_data['failed_list'] = domains_failed

domains_data['complete'] = len(domains_complete)
domains_data['failed'] = len(domains_failed)
domains_data['total'] = len(domains)


with open("EmailTemplate.html.jinja2") as f:
    try:
        template = Template(f.read())
        bodyHTML = template.render(domains_data=domains_data)
    except Exception as e:
        lg.exception("Error parsing email html template: {}".format(e))
        exit(1)

with open("EmailTemplate.txt.jinja2") as f:
    try:
        template = Template(f.read())
        bodyTXT = template.render(domains_data=domains_data)
    except Exception as e:
        lg.exception("Error parsing email txt template: {}".format(e))
        exit(1)

send_report(bodyHTML, bodyTXT)
lg.info("Report email sent.")
