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

# Rotate hourly and keep ~2 hours (zeek-prune-logs.sh). Standalone Zeek
# doesn't rotate at all by default: modbus.log + modbus_detailed.log grew
# ~300 MB/hour from the PLC's normal polling of the remote I/O. Rotated
# files are named <name>.<open time>.log; the live <name>.log keeps the
# current hour, which is all the course's Zeek exercises read.
redef Log::default_rotation_interval = 1 hr;
redef Log::default_rotation_postprocessor_cmd = "/usr/lib/grfics/zeek-prune-logs.sh";

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

# modbus_detailed.log is shipped to Wazuh (zeek/Dockerfile), and about half
# of it was the PLC's routine polling reads - none of which any Wazuh rule
# uses (100100-100103 key on writes). At ~125 lines/s the agent's queue
# overflowed ("message queue is full ... Log lines may be lost"), and a PLC
# program-upload alert from http.log was lost with it. Keep everything
# except plain polling reads that completed without an exception: writes,
# exceptions, diagnostics, device identification (FC43 recon) all stay.
# modbus.log (Zeek's own, not shipped) still has every request, for the
# course's baselining exercise.
const routine_poll_reads: set[string] = {
    "READ_COILS", "READ_DISCRETE_INPUTS",
    "READ_HOLDING_REGISTERS", "READ_INPUT_REGISTERS",
};

# Zeek 9 dropped Log::Filter's $pred; a stream policy hook that "break"s
# vetoes the write instead.
hook Log::log_stream_policy(rec: any, id: Log::ID)
    {
    if ( id != Modbus_Extended::LOG_DETAILED )
        return;

    local r = rec as Modbus_Extended::Modbus_Detailed;
    if ( r?$func && r$func in routine_poll_reads && ! r?$exception_code )
        break;
    }

# --- GRFICS defensive notices ---------------------------------------------
# Surface an attack in Wazuh (via notice.log, which the agent ships) that
# otherwise lived only in conn.log on the sensor: a host inside the plant
# beaconing out to a command-and-control port. The course's HMI implant
# checks in to Kali on 4444/tcp; because both ends are in the DMZ, the
# traffic never crosses the router, so neither the firewall nor Suricata
# ever see it - the mirror is the only sensor that can.
module GRFICS;

export {
    redef enum Notice::Type += {
        ## A host inside the plant opened a connection out to a port
        ## commonly used for command-and-control or reverse shells.
        Suspicious_Outbound_Connection,
    };

    ## Destination ports nothing inside the plant should ever contact -
    ## common C2 / reverse-shell defaults (4444 is the course beacon).
    const c2_ports: set[port] = { 4444/tcp, 1337/tcp, 9001/tcp, 31337/tcp } &redef;
}

# new_connection (not connection_established) so the beacon is caught even
# when its C2 listener is down and the handshake never completes - the
# repeated check-in attempts are the signal.
event new_connection(c: connection)
    {
    if ( c$id$resp_p in GRFICS::c2_ports && Site::is_local_addr(c$id$orig_h) )
        NOTICE([$note=GRFICS::Suspicious_Outbound_Connection,
                $conn=c,
                $msg=fmt("Plant host %s connected out to %s on suspicious port %s - possible C2/reverse-shell beacon",
                         c$id$orig_h, c$id$resp_h, c$id$resp_p),
                $identifier=fmt("%s->%s:%s", c$id$orig_h, c$id$resp_h, c$id$resp_p),
                $suppress_for=1 min]);
    }
