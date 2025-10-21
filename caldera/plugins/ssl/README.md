# MITRE Caldera plugin: SSL

This plugin switches Caldera from using HTTP to HTTPS.

## Overview

When this plugin has been loaded, Caldera will start the HAProxy service on the machine and then serve Caldera at hxxps://[YOUR_IP]:8443, instead of the normal hxxp://[YOUR_IP]:8888.

All deployed agents should use the correct address to connect to Caldera. 

If you would like to modify any of the proxy details, you can do so by going into the `templates/haproxy.conf` file, modifying the contents and restarting Caldera.

## Requirements
* Any Linux or MacOS
* HaProxy >= 1.8

> install haproxy using `brew install haproxy` (MacOS) or `sudo apt-get install haproxy` (Linux)


**Warning:** This plugin uses a default self-signed ssl certificate and key which is insecure. It is highly recommended that you generate your own before using the plugin to increase the safety of the system. Find documentation to do so in the full Caldera docs here: http://caldera.readthedocs.io
If using a self-signed certificate, you may have to update your system preferences to trust the certificate. Additionally, when downloading agents with `curl`, you may have to use the `--insecure` flag to ignore the SSL certificate check for the Caldera server.
