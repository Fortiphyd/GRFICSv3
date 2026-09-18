##! GRFICSv3 local site policy.
##!
##! Based on Zeek's own recommended default (kept below, mostly unchanged) -
##! see docs/zeek-network-mirroring-design.md for why this container exists
##! and how it gets traffic.

redef digest_salt = "grfics-lab";

# The lab's two subnets - several loaded scripts below key off this (asset
# tracking, external-name detection, software-version tracking).
redef Site::local_nets += { 192.168.90.0/24, 192.168.95.0/24 };

# JSON logs, to match the existing Suricata -> Wazuh pipeline
# (router/Dockerfile's alerts.json -> wazuh-agent localfile pattern).
redef LogAscii::use_json = T;

# This script logs which scripts were loaded during each run.
@load misc/loaded-scripts

# Estimate and log capture loss.
@load misc/capture-loss

# Enable logging of memory, packet and lag statistics.
@load misc/stats

# Generate notices when vulnerable versions of software are discovered.
@load frameworks/software/vulnerable

# Detect software changing (e.g. attacker installing hacked SSHD).
@load frameworks/software/version-changes

# This adds signatures to detect cleartext forward and reverse windows shells.
@load-sigs frameworks/signatures/detect-windows-shells

# Load all of the scripts that detect software in various protocols.
@load protocols/ftp/software
@load protocols/smtp/software
@load protocols/ssh/software
@load protocols/http/software

# This script detects DNS results pointing toward your Site::local_nets
# where the name is not part of your local DNS zone and is being hosted
# externally. Requires that the Site::local_zones variable is defined.
@load protocols/dns/detect-external-names

# Script to detect various activity in FTP sessions.
@load protocols/ftp/detect

# Scripts that do asset tracking - useful here: HMI/PLC/EWS/Kali should be a
# small, stable set of known hosts, so a new host or service showing up is a
# real signal, not just background noise.
@load protocols/conn/known-hosts
@load protocols/conn/known-services

# Detect SQL injection attacks (relevant to ScadaLTS's web UI).
@load protocols/http/detect-sql-injection

# Enable MD5 and SHA1 hashing for all files.
@load frameworks/files/hash-all-files

# OT protocol parsers (CISA's ICSNPP, installed via zkg - see Dockerfile).
# Zeek's own base analyzers cover general IT protocols only; without this,
# Modbus traffic (the lab's primary protocol) shows up as plain TCP
# connections in conn.log with no function codes, addresses, or values.
@load packages
