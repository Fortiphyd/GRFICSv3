#!/usr/bin/env python3
"""Benign ARP churn - the 5th and last noise-floor ambient event type.

See docs/cyber-vs-physical-fault-injection-design.md §5. Purpose: three of
the four cyber-inject pairings (§4.1-4.3) rely on Kali ARP-spoofing the
HMI's gateway for their MITM position - without some genuinely benign ARP
activity also happening throughout the session, "I saw ARP weirdness"
would be sufficient evidence of an attack on its own. This produces real,
periodic, *legitimate* ARP churn (simulating a visiting device joining and
leaving, e.g. an engineer's laptop) so that shortcut doesn't work.

Mechanism: creates a short-lived container on the DMZ network
(192.168.90.50, otherwise unused) from the fortiphyd/grfics-arp-churn-device
image, has it ping the router's gateway IP (forcing a real ARP exchange,
not just a passive interface-up event), lets it "stay connected" for a
while, then stops it. A fresh container gets a fresh MAC from Docker every
time, so re-running this on the same IP naturally produces the same
"changed_mac" signature (router/arpmon.py, Wazuh rule 100222) a real
device swap would - confirmed by that rule's own comment ("changed_mac
alone also fires when a container is recreated"). Crucially, this fresh
MAC never collides with any other IP's MAC, so it never trips rule
100223's mac_also_claimed_by escalation to a definite-spoofing alert -
same ambiguous signal a benign reconnect would leave, by construction, not
by chance.

Deliberately has no quiet-buffer suppression, unlike the other ambient
event types: the whole point of this one is to keep recurring
independently of whenever the real attack's own ARP spoofing happens, not
avoid colliding with it - see §5's "distractor" framing. It does still
respect the single dashboard enabled/seed/mean_interval_s controls, like
every other ambient event type.

Talks to the Docker Engine API directly over /var/run/docker.sock (same
socket, same raw-HTTP-over-unix-socket technique as
web_visualization/versions.php, just extended to the write operations
that script never needed) - no docker CLI or SDK required, and this
container already has write access to that socket (it runs as root, same
as every other supervisord program here).
"""
import http.client
import json
import random
import socket
import time
import urllib.parse
import urllib.request

DASHBOARD_URL = "http://127.0.0.1/data/index.php"
DOCKER_SOCKET = "/var/run/docker.sock"
POLL_INTERVAL_S = 2.0

CHURN_IMAGE = "fortiphyd/grfics-arp-churn-device"
CHURN_NETWORK = "grficsv3_c-dmz-net"
CHURN_IP = "192.168.90.50"
CHURN_GATEWAY = "192.168.90.200"  # router's DMZ IP - pinged to force a real ARP exchange
CONTAINER_NAME_PREFIX = "grfics-benign-device-"
DWELL_RANGE_S = (10.0, 30.0)  # how long the "visiting device" stays connected


def log(msg):
    print(f"[arp_churn] {msg}", flush=True)


class UnixSocketHTTPConnection(http.client.HTTPConnection):
    def __init__(self, path):
        super().__init__("localhost")
        self._unix_socket_path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self._unix_socket_path)


def docker_api(method, path, body=None):
    conn = UnixSocketHTTPConnection(DOCKER_SOCKET)
    headers = {}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    conn.request(method, path, body=data, headers=headers)
    resp = conn.getresponse()
    raw = resp.read()
    conn.close()
    decoded = json.loads(raw) if raw else None
    return resp.status, decoded


def fetch_noise_floor_state():
    try:
        with urllib.request.urlopen(DASHBOARD_URL, timeout=3) as resp:
            data = json.loads(resp.read().decode())
        return data.get("noise_floor") or {}
    except Exception as exc:
        log(f"could not reach dashboard: {exc}")
        return {}


def list_stray_devices():
    filters = json.dumps({"name": [CONTAINER_NAME_PREFIX]})
    status, body = docker_api("GET", f"/containers/json?all=1&filters={urllib.parse.quote(filters)}")
    if status != 200 or not body:
        return []
    return [c["Id"] for c in body]


def remove_device(container_id):
    # stop then force-remove, rather than relying only on AutoRemove - a
    # container this script never cleanly stopped (e.g. this script
    # crashed or the whole stack restarted) needs cleaning up on the next
    # startup, the same class of bug the cyber-injects control daemon's
    # stray-relay cleanup already caught once in this project.
    try:
        docker_api("POST", f"/containers/{container_id}/stop?t=1")
    except Exception:
        pass
    try:
        docker_api("DELETE", f"/containers/{container_id}?force=1")
    except Exception:
        pass


def spawn_device():
    name = f"{CONTAINER_NAME_PREFIX}{int(time.time())}"
    status, body = docker_api("POST", f"/containers/create?name={name}", {
        "Image": CHURN_IMAGE,
        "Cmd": ["sh", "-c", f"ping -c 2 -W 1 {CHURN_GATEWAY} >/dev/null 2>&1; sleep 86400"],
        "HostConfig": {"NetworkMode": CHURN_NETWORK, "AutoRemove": True},
        "NetworkingConfig": {
            "EndpointsConfig": {
                CHURN_NETWORK: {"IPAMConfig": {"IPv4Address": CHURN_IP}},
            }
        },
    })
    if status not in (200, 201):
        raise RuntimeError(f"create failed: {status} {body}")
    container_id = body["Id"]
    status, body = docker_api("POST", f"/containers/{container_id}/start")
    if status not in (200, 204):
        raise RuntimeError(f"start failed: {status} {body}")
    log(f"{name} joined {CHURN_NETWORK} as {CHURN_IP}")
    return container_id


def main():
    for stray in list_stray_devices():
        log(f"cleaning up stray device from a previous run: {stray[:12]}")
        remove_device(stray)

    rng = None
    last_seed = None
    was_enabled = False
    next_fire = None
    active_container = None
    disconnect_at = None

    while True:
        try:
            nf_state = fetch_noise_floor_state()
            enabled = bool(nf_state.get("enabled"))
            seed = nf_state.get("seed", 0)
            mean_interval_s = max(1.0, float(nf_state.get("mean_interval_s", 30.0) or 30.0))

            if enabled and (not was_enabled or seed != last_seed):
                # Offset from the raw seed so this doesn't draw the exact
                # same sequence as the EWS nudge script or the main
                # sensor/valve scheduler, which both seed from the same
                # value - each ambient producer needs its own independent
                # stream, not a shared one.
                rng = random.Random((int(seed) if seed is not None else 0) + 1)
                last_seed = seed
                next_fire = time.time() + rng.expovariate(1.0 / mean_interval_s)
                log(f"(re)seeded with seed={seed}, mean_interval_s={mean_interval_s}")
            was_enabled = enabled

            if not enabled and active_container:
                remove_device(active_container)
                active_container = None
                disconnect_at = None

            if active_container and disconnect_at is not None and time.time() >= disconnect_at:
                remove_device(active_container)
                active_container = None
                disconnect_at = None
                next_fire = time.time() + rng.expovariate(1.0 / mean_interval_s)
                log("visiting device disconnected")

            if (enabled and rng is not None and not active_container
                    and next_fire is not None and time.time() >= next_fire):
                try:
                    active_container = spawn_device()
                    disconnect_at = time.time() + rng.uniform(*DWELL_RANGE_S)
                except Exception as exc:
                    log(f"spawn failed: {exc}")
                    next_fire = time.time() + rng.expovariate(1.0 / mean_interval_s)
        except Exception as exc:
            log(f"unexpected error, continuing: {exc}")

        time.sleep(POLL_INTERVAL_S)


if __name__ == "__main__":
    main()
