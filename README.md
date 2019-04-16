# SSLLabsReport

Qualys SSL Labs Scheduled Batch Report

## Description

Given a batch of domains provided in a 'domains.txt' file one domain per line the script will send a new request to the Qualys SSL Labs API and initiate a new scan for each domain, wait for it to finish, then send an email report to a given email address.

The script is intended to be run in a docker container by means of the provided Dockerfile configuration.

## Docker container

You can pull the latest version of this container from Docker Hub by running `docker pull dralom/ssllabsreport` or build your own by cloning this repo and running `docker build -t SSLLabsReport .`

### Configuration

The configuration settings for the SMTP connection need to be provided in the form of a `config.json` file in the project's folder. The [config.example.json](src/config.example.json) file provides an example of the format of this file. The `SMTPUSER` and `SMTPPASSWORD` values are not mandatory if the SMTP relay does not require authentication. All other values are mandatory.

### Example Run Command

For use with an open SMTP relay (no authentication)

```
docker run -d -it \
--name qualysReport \
-v /srv/qualysReport/domains.txt:/Main/SSLLabsReport/domains.txt \
-v /srv/qualysReport/config.json:/Main/SSLLabsReport/config.json \
--restart unless-stopped \
dralom/ssllabsreport
```

This will mount the container in detatched mode, map a local, persistent copy of the `domains.txt` file to the location where the script expects the file: `/Main/SSLLabsReport/domains.txt`, and map a local, persistent copy of the `config.json` file to the location where the script expects the file: `/Main/SSLLabsReport/config.json`. You may change the local value to where you store your copy of this file. Additionally, the `--restart` option will ensure that the docker container restarts unless explicitly stopped.

Note: The current default cron job runs the report every Monday at 4AM server time.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
