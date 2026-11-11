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

# --- GRFICS Wazuh write-detection stream -----------------------------------
# A dedicated log, built directly from Zeek's own base Modbus write
# *response* events, for the Wazuh rules that key on writes
# (wazuh/local_rules.xml, 100100-100103) - replacing a direct dependency
# on modbus_detailed.log's own schema. Two reasons:
#   1. Only a genuinely completed response reaches this stream, so there's
#      no separate "matched" field to filter on the way the old rules
#      needed - a half-open/unmatched request (see §5.10/§5.14's
#      modbus_pending findings) never gets here at all.
#   2. The register address needs a field name Wazuh will actually accept.
#      Zeek's own field is literally named "address" - but that word is
#      reserved in Wazuh's rule schema and fails rule-file validation
#      ("Syntax error on tag 'address'") even in complete isolation, even
#      renamed to "addr" - not a data collision, a parser-level
#      reservation. Found live: once workstation/noise_floor/
#      ews_nudge.py started legitimately writing to the PLC as part of
#      the noise floor, the fix attempted first (scoping the *old* rule
#      to specific addresses) couldn't even load. Named write_address
#      here instead, so it never collides.
module GRFICS;

export {
    redef enum Log::ID += { MODBUS_WRITE_LOG };

    type Modbus_Write: record {
        ts: time &log;
        uid: string &log;
        id: conn_id &log;
        func: string &log;
        write_address: count &log;
    };
}

event zeek_init() &priority=5
    {
    Log::create_stream(GRFICS::MODBUS_WRITE_LOG,
                        [$columns=Modbus_Write, $path="grfics_modbus_write"]);
    }

function grfics_log_write(c: connection, op: string, reg: count)
    {
    # Both "func" and "addr" are reserved type keywords in Zeek's own
    # grammar ("a function/event/hook value" and "an IP address",
    # respectively) - neither can be a parameter name here, even though
    # "func" is fine as the $func *record field* name below, and "address"
    # (a different token entirely) is fine as the event parameter names
    # a few lines down, already used successfully by the vendored ICSNPP
    # package itself.
    Log::write(GRFICS::MODBUS_WRITE_LOG, [
        $ts=network_time(), $uid=c$uid, $id=c$id,
        $func=op, $write_address=reg
    ]);
    }

event modbus_write_single_coil_response(c: connection, headers: ModbusHeaders, address: count, value: bool)
    { grfics_log_write(c, "WRITE_SINGLE_COIL", address); }

event modbus_write_single_register_response(c: connection, headers: ModbusHeaders, address: count, value: count)
    { grfics_log_write(c, "WRITE_SINGLE_REGISTER", address); }

event modbus_write_multiple_coils_response(c: connection, headers: ModbusHeaders, start_address: count, quantity: count)
    { grfics_log_write(c, "WRITE_MULTIPLE_COILS", start_address); }

event modbus_write_multiple_registers_response(c: connection, headers: ModbusHeaders, start_address: count, quantity: count)
    { grfics_log_write(c, "WRITE_MULTIPLE_REGISTERS", start_address); }

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
