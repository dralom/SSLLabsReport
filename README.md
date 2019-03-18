# SSLLabsReport

Qualys SSL Labs Scheduled Batch Report

## Description

Given a batch of domains provided in a 'domains.txt' file one domain per line the 
script will send a new request to the Qualys SSL Labs API and initiate a new scan for
each domain, wait for it to finish, then send an email report to a given email address.

The script is intended to be run in a docker container by means of the provided 
Dockerfile configuration.

## Docker container

### Configuration

Environment variables required:
* SMTPSERVER - SMTP Server address
* SMTPPORT - SMTP Server port
* SMTPUSER - [optional] SMTP Server username (if required)
* SMTPPASSWORD - [optional] SMTP Server password (if required)
* SMTPORIGIN - The 'From' email address
* SMTPDESTINATION - The 'To' email address

