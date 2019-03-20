# SSLLabsReport

Qualys SSL Labs Scheduled Batch Report

## Description

Given a batch of domains provided in a 'domains.txt' file one domain per line the 
script will send a new request to the Qualys SSL Labs API and initiate a new scan for
each domain, wait for it to finish, then send an email report to a given email address.

The script is intended to be run in a docker container by means of the provided 
Dockerfile configuration.

## Docker container

You can pull the latest version of this container from Docker Hub by running
`docker pull dralom/ssllabsreport` or build your own by cloning this repo and running 
`docker build --label SSLLabsReport .`

### Configuration

Environment variables required:
* `SMTPSERVER` - SMTP Server address
* `SMTPPORT` - SMTP Server port
* `SMTPUSER` - [optional] SMTP Server username (if required)
* `SMTPPASSWORD` - [optional] SMTP Server password (if required)
* `SMTPORIGIN` - The 'From' email address
* `SMTPDESTINATION` - The 'To' email address

### Example Run Command

For use with an open SMTP relay (no authentication)

```
docker run -d -it \
--name qualysReport \
-e "SMTPSERVER=smtp.example.com" \
-e "SMTPPORT=25" \
-e "SMTORIGIN=reports@example.com" \
-e "SMTPDESTINATION=itsupport@example.com" \
-v /srv/qualysReport/domains.txt:/Main/SSLLabsReport/domains.txt \
dralom/ssllabsreport
```

This will set the environment variables needed to configure the script's SMTP
connectivity. It will also map a local, persistent copy of the `domains.txt` file 
to the location where the script expects the file: `/Main/SSLLabsReport/domains.txt`. 
You may change the local value to where you store your copy of this file.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) 
file for details