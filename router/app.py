from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
import subprocess
import json, os, functools, time, glob, re, ipaddress, shutil
from werkzeug.security import generate_password_hash, check_password_hash
from collections import Counter
from pathlib import Path
from datetime import datetime

app = Flask(__name__)

# Admin-configured extra interfaces (beyond the auto-detected LAN/DMZ),
# and per-zone IDS monitor toggles. Populated by load_config() below —
# declared here so _detect_interface_labels() can reference them.
zones = []
DEFAULT_IDS_MONITOR = {"LAN": False, "DMZ": True}
ids_monitor = DEFAULT_IDS_MONITOR.copy()

# Explicit LAN/DMZ -> interface bindings for hosts where nothing pre-assigns
# an address on those NICs (bare-metal/VM installs — Docker's macvlan config
# used to do this automatically). {"LAN": "eth1", "DMZ": "eth2"}
zone_iface_overrides = {}

# Zone labels the router must NOT act as the gateway for: network-init.py
# skips assigning (and removes) the subnet's first-host (.1) address for
# these. Used where the router should hold only its own interface address —
# e.g. an LXC that must not also claim the subnet's default gateway. ["DMZ"]
gateway_skip = []

# Needed by _detect_interface_labels() below (via load_wg_config(), which
# may run its old-schema migration) before the full constants block further
# down the file is defined.
WG_CONFIG_PATH = "/etc/firewall/wg_config.json"
DEFAULT_TUNNEL_SUBNET = "10.100.0.0/24"
DEFAULT_TUNNEL_PORT = 51820

BUILTIN_ZONE_NETWORKS = [
    ("LAN", ipaddress.ip_network("192.168.95.0/24")),
    ("DMZ", ipaddress.ip_network("192.168.90.0/24")),
]


def _configured_zone_networks():
    """[(label, ipaddress.ip_network), ...] for admin-added zones with a valid subnet."""
    result = []
    for z in zones:
        try:
            result.append((z.get("label", z.get("iface", "Zone")), ipaddress.ip_network(z["subnet"], strict=False)))
        except (KeyError, ValueError):
            continue
    return result


def _configured_tunnel_networks():
    """[(label, ipaddress.ip_network), ...] for configured WireGuard tunnels
    with a valid subnet — zones and tunnels share one address-space
    namespace (both become real router interfaces), so anything checking
    one for an overlap must check the other too.
    """
    result = []
    for t in load_wg_config().get("tunnels", []):
        try:
            result.append((t.get("label", t.get("name", "Tunnel")), ipaddress.ip_network(t["subnet"], strict=False)))
        except (KeyError, ValueError):
            continue
    return result


# load_wg_config/save_wg_config/find_tunnel need to exist before
# _detect_interface_labels() below, which reads tunnel labels.
def _migrate_wg0_firewall_rule():
    """Companion to the wg0 migration below. The blanket `-i/-o wg0 ACCEPT`
    rules this version removes (see build_iptables_rules) used to give an
    existing deployment's VPN peers full forwarding access with no explicit
    rule for it — so migrating the config alone would silently drop all of
    that traffic the moment this version starts, since the new per-tunnel
    model grants no access by default. Write explicit, visible rules that
    preserve the old behavior instead, so the admin can see and scope them
    down like any other rule, rather than losing access outright.

    Reads/writes /etc/firewall/config.json directly with a hardcoded path
    rather than via CONFIG_PATH/save_json: this runs at import time (via
    INTERFACE_LABELS = _detect_interface_labels() below), before either of
    those is defined further down the file.
    """
    path = "/etc/firewall/config.json"
    try:
        with open(path) as f:
            fw_config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        fw_config = {}
    rules = fw_config.setdefault("rules", [])
    marker = "Auto-added on upgrade"
    if any(r.get("comment", "").startswith(marker) for r in rules):
        return
    for iface_in, iface_out in (("wg0", ""), ("", "wg0")):
        rules.append({
            "iface_in": iface_in, "iface_out": iface_out,
            "src": "0.0.0.0/0", "dst": "0.0.0.0/0",
            "proto": "all", "dport": "", "action": "ACCEPT",
            "comment": f"{marker}: preserves this tunnel's pre-existing full "
                       f"access now that VPN traffic is scoped by ordinary "
                       f"rules instead of a blanket accept — review and "
                       f"scope down if it doesn't need this.",
        })
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(fw_config, f, indent=2)


def load_wg_config():
    try:
        with open(WG_CONFIG_PATH) as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"tunnels": []}

    if "tunnels" not in config and "server" in config:
        # Migrate the old single-tunnel {server, peers} schema into one
        # tunnel named wg0, preserving its keys/port/peers so nothing about
        # an existing deployment's WireGuard setup changes until the admin
        # touches it. Access is a separate concern, handled below.
        server = config.get("server", {})
        if server.get("private_key"):
            config = {"tunnels": [{
                "name": "wg0",
                "label": "VPN",
                "listen_port": server.get("listen_port", DEFAULT_TUNNEL_PORT),
                "subnet": DEFAULT_TUNNEL_SUBNET,
                "private_key": server["private_key"],
                "public_key": server["public_key"],
                "client_routes": "192.168.95.0/24, 192.168.90.0/24",
                "peers": config.get("peers", []),
            }]}
            _migrate_wg0_firewall_rule()
        else:
            config = {"tunnels": []}
        save_wg_config(config)

    config.setdefault("tunnels", [])
    return config


def save_wg_config(config):
    os.makedirs(os.path.dirname(WG_CONFIG_PATH), exist_ok=True)
    with open(WG_CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def find_tunnel(config, name):
    return next((t for t in config.get("tunnels", []) if t["name"] == name), None)


def _suggest_tunnel_defaults(config):
    """Next free 10.100.<N>.0/24 subnet and 51820+N port, not colliding with an existing tunnel."""
    used_subnets = {t["subnet"] for t in config.get("tunnels", [])}
    used_ports = {t.get("listen_port") for t in config.get("tunnels", [])}
    n = 0
    while True:
        subnet = f"10.100.{n}.0/24"
        port = DEFAULT_TUNNEL_PORT + n
        if subnet not in used_subnets and port not in used_ports:
            return subnet, port
        n += 1


def _detect_interface_labels():
    _FALLBACK = {"eth0": "Admin", "eth1": "LAN", "eth2": "DMZ"}
    try:
        out = subprocess.check_output(["ip", "-4", "addr"], text=True)
    except Exception:
        return _FALLBACK

    iface_ips = {}
    current = None
    for line in out.splitlines():
        m = re.match(r'^\d+:\s+(\S+):', line)
        if m:
            current = m.group(1).split('@')[0]
        ip_m = re.search(r'inet (\d+\.\d+\.\d+\.\d+)/', line)
        if ip_m and current and current != 'lo':
            iface_ips.setdefault(current, []).append(ip_m.group(1))

    zone_networks = BUILTIN_ZONE_NETWORKS + _configured_zone_networks()
    tunnel_labels = {t["name"]: t.get("label", t["name"]) for t in load_wg_config().get("tunnels", [])}

    labels = {}
    for iface, ips in iface_ips.items():
        if iface == 'lo':
            continue
        if iface in tunnel_labels:
            # Each WireGuard tunnel is its own interface (pfSense-style) so
            # it shows up in the Firewall rule builder like any other zone —
            # scoping a tunnel's access is then just an ordinary rule, not a
            # separate VPN-specific mechanism.
            labels[iface] = tunnel_labels[iface]
            continue
        for ip in ips:
            addr = ipaddress.ip_address(ip)
            matched = next((label for label, network in zone_networks if addr in network), None)
            if matched:
                labels[iface] = matched
            else:
                labels.setdefault(iface, 'Admin')

    return labels if labels else _FALLBACK


def _existing_link_names():
    """All current network interface (link) names on the box, physical or
    virtual, regardless of whether they have an IP. Used to reject a new
    tunnel name that collides with a real interface: wg-quick refuses to
    create it (fails cleanly, doesn't touch the real link), but the tunnel
    record would still get saved despite the failed start, and
    wg_iface_up()'s bare `ip link show <name>` would then misreport it as
    permanently "Up" forever after, since the real link always exists.
    """
    try:
        out = subprocess.check_output(["ip", "-o", "link", "show"], text=True)
    except subprocess.CalledProcessError:
        return set()
    names = set()
    for line in out.splitlines():
        m = re.match(r'^\d+:\s+(\S+):', line)
        if m:
            names.add(m.group(1).split('@')[0])
    return names


def _list_unconfigured_ifaces():
    """Interfaces with no IPv4 address at all — free NICs the admin can turn into a zone."""
    try:
        link_out = subprocess.check_output(["ip", "-o", "link", "show"], text=True)
        addr_out = subprocess.check_output(["ip", "-o", "-4", "addr", "show"], text=True)
    except Exception:
        return []

    tunnel_names = {t["name"] for t in load_wg_config().get("tunnels", [])}
    all_ifaces = []
    for line in link_out.splitlines():
        m = re.match(r'^\d+:\s+(\S+):', line)
        if m:
            iface = m.group(1).split('@')[0]
            if iface != 'lo' and iface not in tunnel_names:
                all_ifaces.append(iface)

    has_ip = set()
    for line in addr_out.splitlines():
        m = re.match(r'^\d+:\s+(\S+)\s', line)
        if m:
            has_ip.add(m.group(1).split('@')[0])

    configured = {z.get("iface") for z in zones if z.get("iface")}
    configured |= set(zone_iface_overrides.values())
    return [i for i in all_ifaces if i not in has_ip and i not in configured]


def _refresh_interface_labels():
    global INTERFACE_LABELS
    INTERFACE_LABELS = _detect_interface_labels()


def _restart_daemon(supervisor_name, systemd_unit):
    """Restart a managed daemon under whichever init system is actually
    running this build — supervisord program name on Docker, systemd unit
    name on the VM/bare-metal package. Check supervisorctl first: the
    Docker image also ships a fake no-op `systemctl` stub (to satisfy the
    Wazuh agent's postinstall script), so checking systemd first would
    silently no-op on Docker instead of falling through.
    """
    if shutil.which("supervisorctl"):
        subprocess.run(["supervisorctl", "restart", supervisor_name], check=False)
    elif shutil.which("systemctl"):
        subprocess.run(["systemctl", "restart", systemd_unit], check=False)


def _apply_network():
    """Re-run network-init.py so a zone change takes effect without a reboot.

    A saved config change (the zones/overrides list) and a *live* network
    change are two different things — this makes a network-init.py failure
    visible in the UI instead of silently leaving the OS state unchanged.
    """
    proc = subprocess.run(
        ["python3", "/usr/lib/grfics/network-init.py"],
        capture_output=True, text=True,
    )
    _refresh_interface_labels()
    # network-init.py flushes and rebuilds the whole nat POSTROUTING chain,
    # which wipes the WireGuard masquerade rule each tunnel's apply_wg_tunnel()
    # sets up separately — re-assert every active tunnel's so an unrelated
    # zone change doesn't silently cut VPN peers off from the internet.
    for tunnel in load_wg_config().get("tunnels", []):
        if wg_iface_up(tunnel["name"]):
            _ensure_wg_masquerade(tunnel["subnet"])
    if proc.returncode == 0:
        # network-init.py just rewrote /run/grfics/ids-ifaces, but Suricata
        # only reads that file at process start (suricata-start.sh) — restart
        # it so an IDS-monitor toggle or new zone takes effect without
        # waiting for a full reboot, same as apply_dns_config() does for
        # dnsmasq below. grfics-suricata.service is the VM package's own
        # unit wrapping suricata-start.sh (postinst masks the stock
        # suricata.service to avoid the two conflicting).
        _restart_daemon("suricata", "grfics-suricata")
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        flash("Saved, but applying it to the live network failed: "
              + (detail[-1] if detail else f"network-init.py exited {proc.returncode}"), "danger")
    return proc


INTERFACE_LABELS = _detect_interface_labels()

# SECRET_KEY is required for sessions. Set via env var in compose or host.
# For quick local testing you can hardcode, but better: export SECRET_KEY before starting.
app.secret_key = os.environ.get("FWUI_SECRET_KEY", "dev-secret-key-change-me")

# intentionally weak defaults for lab use
DEFAULT_USERS = [{"username": "admin", "password_hash": generate_password_hash("password"), "role": "admin"}]

users = [u.copy() for u in DEFAULT_USERS]

LOG_FILE = "/var/log/ulog/netfilter_log.json"
SURICATA_EVE_FILE = "/var/log/suricata/eve.json"
FIREWALL_RULES_PATH = "/etc/firewall/rules"
CONFIG_PATH = "/etc/firewall/config.json"
IDS_ALERTS_FILE = "/etc/suricata/alerts.json"
IDS_RULES_FILE = "/etc/suricata/rules/local.rules"
ICS_SUBNET = "192.168.95.0/24"   # trusted LAN — default allow outbound

ARPMON_STATE = "/var/lib/arpmon/state.json"
ARPMON_LOG   = "/var/log/arpmon/events.json"

DNS_CONFIG_PATH = "/etc/firewall/dns_config.json"
WG_CONF_DIR = "/etc/wireguard"
DNS_HOSTS_PATH = "/etc/firewall/dns_hosts"
DNS_BLOCKED_PATH = "/etc/firewall/dns_blocked.conf"
DNSMASQ_LOG = "/var/log/dnsmasq/dnsmasq.log"

pending_rules = []
nat_rules = []
dirty = False

def parse_firewall_logs(limit=100):
    entries = []
    try:
        with open(LOG_FILE) as f:
            for line in f:
                data = json.loads(line)
                in_iface = INTERFACE_LABELS.get(data.get("oob.in"), data.get("oob.in", "?"))
                entries.append({
                    "time": datetime.fromisoformat(data.get("timestamp")).strftime("%H:%M:%S"),
                    "action": data.get("oob.prefix", "").replace("FW ", "").strip(": "),
                    "proto": {6:"TCP",17:"UDP",1:"ICMP"}.get(data.get("ip.protocol"), str(data.get("ip.protocol"))),
                    "src": f"{data.get('src_ip','?')}:{data.get('src_port','')}",
                    "dst": f"{data.get('dest_ip','?')}:{data.get('dest_port','')}",
                    "iface": f"{in_iface}",
                })
        entries = entries[-limit:]  # last N lines
    except FileNotFoundError:
        pass
    return entries

def get_recent_alerts(limit=50):
    eve_path = Path(SURICATA_EVE_FILE)
    alerts = []
    if not eve_path.exists():
        return alerts
    with eve_path.open() as f:
        for line in f:
            try:
                event = json.loads(line)
                if event.get("event_type") == "alert":
                    alerts.append({
                        "timestamp": event.get("timestamp"),
                        "src": event.get("src_ip"),
                        "dst": event.get("dest_ip"),
                        "proto": event.get("proto"),
                        "signature": event["alert"].get("signature"),
                    })
            except json.JSONDecodeError:
                continue
    return alerts[-limit:]


RULES_DIR = "/etc/suricata/rules"


def parse_rule_lines(text):
    # Rejoin lines ending with \ before parsing (multi-line rule format)
    logical_lines = []
    buf = ""
    for raw in text.splitlines():
        stripped = raw.rstrip()
        if stripped.endswith("\\"):
            buf += stripped[:-1]
        else:
            buf += stripped
            logical_lines.append(buf)
            buf = ""
    if buf:
        logical_lines.append(buf)

    rules = []
    for line in logical_lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        msg_m = re.search(r'msg:"([^"]+)"', line)
        sid_m = re.search(r'\bsid:(\d+)', line)
        rules.append({
            "sid": sid_m.group(1) if sid_m else "—",
            "msg": msg_m.group(1) if msg_m else line[:80],
        })
    return rules


def load_builtin_rules():
    rules = []
    for path in sorted(glob.glob(f"{RULES_DIR}/*.rules")):
        if os.path.basename(path) == "local.rules":
            continue
        try:
            with open(path) as f:
                text = f.read()
        except OSError:
            continue
        label = os.path.basename(path).replace(".rules", "")
        for r in parse_rule_lines(text):
            r["file"] = label
            rules.append(r)
    return rules


def load_json(path, default=[]):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


DEFAULT_RULES = [
    {
        "iface_in": "",
        "iface_out": "",
        "src": "0.0.0.0/0",
        "dst": "0.0.0.0/0",
        "proto": "all",
        "dport": "",
        "action": "ACCEPT",
        "comment": "TEMP - allow all traffic for troubleshooting - DO NOT LEAVE IN PRODUCTION",
    }
]

def load_config():
    global pending_rules, nat_rules, dirty, users, zones, ids_monitor, zone_iface_overrides, gateway_skip, INTERFACE_LABELS
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            data = json.load(f)
            pending_rules = data.get("rules", [])
            nat_rules = data.get("nat_rules", [])
            zones = data.get("zones", [])
            ids_monitor = {**DEFAULT_IDS_MONITOR, **data.get("ids_monitor", {})}
            zone_iface_overrides = data.get("zone_iface_overrides", {})
            gateway_skip = data.get("gateway_skip", [])
            if "users" in data:
                users = data["users"]
            elif "auth" in data:
                # migrate legacy plaintext single-user record
                old = data["auth"]
                users = [{"username": old["username"],
                          "password_hash": generate_password_hash(old["password"]),
                          "role": "admin"}]
                save_config()
    else:
        pending_rules = DEFAULT_RULES.copy()
        nat_rules = []
        zones = []
        ids_monitor = DEFAULT_IDS_MONITOR.copy()
        zone_iface_overrides = {}
        gateway_skip = []
        save_config()
    dirty = False
    INTERFACE_LABELS = _detect_interface_labels()


def save_config():
    data = {"rules": pending_rules, "nat_rules": nat_rules, "users": users, "zones": zones,
            "ids_monitor": ids_monitor, "zone_iface_overrides": zone_iface_overrides,
            "gateway_skip": gateway_skip}
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)


# --- traffic stats helpers ---

_iface_prev = {}  # {iface: (monotonic_time, {rx_bytes, rx_packets, tx_bytes, tx_packets})}

def read_proc_net_dev():
    stats = {}
    try:
        with open('/proc/net/dev') as f:
            for line in f.readlines()[2:]:
                parts = line.split()
                if len(parts) < 11:
                    continue
                iface = parts[0].rstrip(':')
                stats[iface] = {
                    'rx_bytes':   int(parts[1]),
                    'rx_packets': int(parts[2]),
                    'tx_bytes':   int(parts[9]),
                    'tx_packets': int(parts[10]),
                }
    except FileNotFoundError:
        pass
    return stats


def get_interface_rates():
    now = time.monotonic()
    current = read_proc_net_dev()
    rates = {}
    for iface in INTERFACE_LABELS:
        if iface not in current:
            rates[iface] = {'rx_bps': 0.0, 'rx_pps': 0.0, 'tx_bps': 0.0, 'tx_pps': 0.0}
            continue
        cur = current[iface]
        if iface in _iface_prev:
            prev_time, prev = _iface_prev[iface]
            dt = now - prev_time
            if dt > 0:
                rates[iface] = {
                    'rx_bps': max(0.0, (cur['rx_bytes']   - prev['rx_bytes'])   / dt),
                    'rx_pps': max(0.0, (cur['rx_packets'] - prev['rx_packets']) / dt),
                    'tx_bps': max(0.0, (cur['tx_bytes']   - prev['tx_bytes'])   / dt),
                    'tx_pps': max(0.0, (cur['tx_packets'] - prev['tx_packets']) / dt),
                }
            else:
                rates[iface] = {'rx_bps': 0.0, 'rx_pps': 0.0, 'tx_bps': 0.0, 'tx_pps': 0.0}
        else:
            rates[iface] = {'rx_bps': 0.0, 'rx_pps': 0.0, 'tx_bps': 0.0, 'tx_pps': 0.0}
        _iface_prev[iface] = (now, cur)
    return rates


def parse_conntrack():
    entries = []
    try:
        with open('/proc/net/nf_conntrack') as f:
            for line in f:
                parts = line.split()
                if len(parts) < 5:
                    continue
                l4proto = parts[2]
                ttl = int(parts[4])
                # TCP has a state word at position 5 before the key=value pairs
                state = ''
                if l4proto == 'tcp' and len(parts) > 5 and '=' not in parts[5]:
                    state = parts[5]
                # Collect key=value pairs; first occurrence = original direction
                kv = {}
                for p in parts:
                    if '=' in p:
                        k, v = p.split('=', 1)
                        if k not in kv:
                            kv[k] = v
                entries.append({
                    'proto': l4proto,
                    'state': state,
                    'ttl':   ttl,
                    'src':   kv.get('src',   '?'),
                    'dst':   kv.get('dst',   '?'),
                    'sport': kv.get('sport', ''),
                    'dport': kv.get('dport', ''),
                })
    except (FileNotFoundError, ValueError):
        pass
    return entries


def get_top_talkers(entries, n=10):
    counts = Counter(e['src'] for e in entries if e['src'] != '?')
    return [{'ip': ip, 'connections': count} for ip, count in counts.most_common(n)]


# --- dnsmasq helpers ---

def load_dns_config():
    try:
        with open(DNS_CONFIG_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"hosts": [], "blocked": []}


def save_dns_config(config):
    with open(DNS_CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def apply_dns_config(config):
    """Write dnsmasq host and block files then restart dnsmasq."""
    host_lines = [f"{h['ip']}\t{h['hostname']}" for h in config.get("hosts", [])]
    with open(DNS_HOSTS_PATH, "w") as f:
        f.write("\n".join(host_lines) + ("\n" if host_lines else ""))

    block_lines = [f"address=/{b['domain']}/" for b in config.get("blocked", [])]
    with open(DNS_BLOCKED_PATH, "w") as f:
        f.write("\n".join(block_lines) + ("\n" if block_lines else ""))

    # "dnsmasq" is both the supervisord program name (Docker) and the stock
    # package's own systemd unit name (VM/bare-metal) — same string, unlike
    # Suricata which needs its own grfics-suricata unit.
    _restart_daemon("dnsmasq", "dnsmasq")


def get_dns_queries(limit=100):
    queries = []
    try:
        with open(DNSMASQ_LOG) as f:
            for line in f:
                if "query[" not in line:
                    continue
                parts = line.strip().split()
                q_idx = next((i for i, p in enumerate(parts) if "query[" in p), None)
                if q_idx is None:
                    continue
                try:
                    qtype  = parts[q_idx].split("[")[1].rstrip("]")
                    domain = parts[q_idx + 1]
                    src    = parts[q_idx + 3] if len(parts) > q_idx + 3 else "?"
                    queries.append({
                        "time":   " ".join(parts[:3]),
                        "type":   qtype,
                        "domain": domain,
                        "src":    src,
                    })
                except (IndexError, ValueError):
                    continue
    except FileNotFoundError:
        pass
    return queries[-limit:]


# --- wireguard helpers ---
#
# Each tunnel is an independent WireGuard interface (own keys/port/subnet),
# matching pfSense's model of assigning each VPN tunnel as its own
# interface -- that's what lets "Interfaces > Firewall" scope different
# tunnels to different zones instead of one blanket-trusted wg0.
# (load_wg_config/save_wg_config/find_tunnel live earlier in the file,
# above _detect_interface_labels(), since that needs them at import time.)

def wg_genkey():
    priv = subprocess.check_output(["wg", "genkey"], text=True).strip()
    pub = subprocess.check_output(["wg", "pubkey"], input=priv, text=True).strip()
    return priv, pub


def write_wg_conf(tunnel):
    network = ipaddress.ip_network(tunnel["subnet"], strict=False)
    address = list(network.hosts())[0]  # generator normally, list for /31 and /32
    lines = [
        "[Interface]",
        f"PrivateKey = {tunnel['private_key']}",
        f"ListenPort = {tunnel.get('listen_port', DEFAULT_TUNNEL_PORT)}",
        f"Address = {address}/{network.prefixlen}",
        "",
    ]
    for peer in tunnel.get("peers", []):
        lines += [
            f"# {peer.get('name', 'peer')}",
            "[Peer]",
            f"PublicKey = {peer['public_key']}",
            f"AllowedIPs = {peer['allowed_ips']}",
            "",
        ]
    os.makedirs(WG_CONF_DIR, exist_ok=True)
    with open(os.path.join(WG_CONF_DIR, f"{tunnel['name']}.conf"), "w") as f:
        f.write("\n".join(lines))


def _ensure_wg_masquerade(subnet):
    r = subprocess.run(
        ["iptables", "-t", "nat", "-C", "POSTROUTING", "-s", subnet, "-j", "MASQUERADE"],
        capture_output=True,
    )
    if r.returncode != 0:
        subprocess.run(
            ["iptables", "-t", "nat", "-A", "POSTROUTING", "-s", subnet, "-j", "MASQUERADE"],
            check=False,
        )


def apply_wg_tunnel(tunnel):
    write_wg_conf(tunnel)
    subprocess.run(["wg-quick", "down", tunnel["name"]], capture_output=True)
    result = subprocess.run(["wg-quick", "up", tunnel["name"]], capture_output=True, text=True)
    if result.returncode == 0:
        _ensure_wg_masquerade(tunnel["subnet"])
    return result


def parse_wg_show(name):
    """Parse `wg show <name> dump` into a dict keyed by peer public key."""
    try:
        out = subprocess.check_output(
            ["wg", "show", name, "dump"], text=True, stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        return {}
    status = {}
    for line in out.strip().splitlines()[1:]:  # skip interface line
        parts = line.split("\t")
        if len(parts) < 8:
            continue
        pubkey = parts[0]
        last_hs = int(parts[4]) if parts[4] != "0" else 0
        status[pubkey] = {
            "endpoint": parts[2] if parts[2] != "(none)" else None,
            "allowed_ips": parts[3],
            "last_handshake": last_hs,
            "rx_bytes": int(parts[5]),
            "tx_bytes": int(parts[6]),
        }
    return status


def wg_iface_up(name):
    return subprocess.run(["ip", "link", "show", name], capture_output=True).returncode == 0


# --- login helpers/decorators ---
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped_view


def admin_required(view):
    @functools.wraps(view)
    def wrapped_view(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Administrator access required.", "danger")
            return redirect(url_for("index"))
        return view(*args, **kwargs)
    return wrapped_view


@app.route("/login", methods=["GET", "POST"])
def login():
    next_url = request.args.get("next") or url_for("dashboard")
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        user_rec = next((u for u in users if u["username"] == username), None)
        if user_rec and check_password_hash(user_rec["password_hash"], password):
            session["logged_in"] = True
            session["username"] = username
            session["role"] = user_rec["role"]
            flash("Logged in", "success")
            return redirect(next_url)
        else:
            flash("Invalid username or password", "danger")
    return render_template("login.html", next=next_url)

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for("login"))

# --- protect routes: add @login_required above routes that need protection ---
# Example: protect index and all modifying endpoints

def is_dirty():
    active = subprocess.check_output(["iptables-save"], text=True)
    saved = open(CONFIG_PATH).read() if os.path.exists(CONFIG_PATH) else ""
    return saved not in active


def _normalize_ctstate(line):
    """Sort any --ctstate value list before comparing lines for equality.

    The kernel doesn't preserve the order a multi-value match option (like
    `--ctstate ESTABLISHED,RELATED`) was written in — `iptables -S` echoes
    it back in its own canonical order (observed: `RELATED,ESTABLISHED`),
    so a plain string comparison against what build_iptables_rules() wrote
    would spuriously fail.
    """
    return re.sub(r'(--ctstate )(\S+)',
                  lambda m: m.group(1) + ','.join(sorted(m.group(2).split(','))),
                  line)


def parse_iptables_rules():
    """Reconstruct pending_rules from the live FORWARD chain (used by Revert).

    Scoped to FORWARD only — `iptables -S` with no chain lists every chain
    in the filter table, which would otherwise pull in INPUT/OUTPUT and our
    own LOGDROP/LOGREJECT logging chains. The stateful base rules, ICS
    default-allow, and NAT-associated accepts (build_iptables_rules always
    regenerates these itself) are excluded too, since re-adding them as
    "user" pending_rules would just duplicate them on the next Apply.
    """
    raw = subprocess.check_output(["iptables", "-S", "FORWARD"], text=True).splitlines()
    managed_lines = {
        _normalize_ctstate("-A FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT"),
        _normalize_ctstate("-A FORWARD -m conntrack --ctstate INVALID -j DROP"),
        f"-A FORWARD -s {ICS_SUBNET} -j ACCEPT",
        "-A FORWARD -j LOGDROP",
    }
    managed_lines |= {
        _nat_associated_forward_line(nr) for nr in nat_rules
        if nr.get('enabled', True) and nr.get('auto_fw_rule', True)
    }

    idx = 0
    rules = []
    for line in raw:
        if not line.startswith('-A FORWARD') or _normalize_ctstate(line) in managed_lines:
            continue
        idx += 1
        parts = line.split()
        # DROP/REJECT rules jump to LOGDROP/LOGREJECT (see build_iptables_rules),
        # so the action must be un-prefixed back to match the rule schema.
        target = parts[-1]
        action = target[3:] if target.startswith('LOG') else target
        rule = {
            'index': idx,
            'chain': parts[1],
            'iface_in': next((parts[i+1] for i,p in enumerate(parts) if p == '-i'), ''),
            'iface_out': next((parts[i+1] for i,p in enumerate(parts) if p == '-o'), ''),
            'src': next((parts[i+1] for i,p in enumerate(parts) if p == '-s'), '0.0.0.0/0'),
            'dst': next((parts[i+1] for i,p in enumerate(parts) if p == '-d'), '0.0.0.0/0'),
            'proto': next((parts[i+1] for i,p in enumerate(parts) if p == '-p'), 'all'),
            'dport': next((parts[i+1] for i,p in enumerate(parts) if p == '--dport'), ''),
            'action': action,
            'comment': '',
        }
        rules.append(rule)
    return rules

@app.route("/dashboard")
@app.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html", active_page="dashboard", labels=INTERFACE_LABELS)


@app.route("/api/stats")
@login_required
def api_stats():
    entries = parse_conntrack()
    rates = get_interface_rates()
    return jsonify({
        'connection_count': len(entries),
        'interfaces': {
            iface: {'label': INTERFACE_LABELS.get(iface, iface), **data}
            for iface, data in rates.items()
        },
        'top_talkers': get_top_talkers(entries),
    })


@app.route("/states")
@login_required
def states():
    return render_template("states.html", active_page="states")


_CLOSED_STATES = {'TIME_WAIT', 'CLOSE', 'CLOSE_WAIT', 'LAST_ACK'}

@app.route("/api/states")
@login_required
def api_states():
    entries = [e for e in parse_conntrack()
               if e['state'] not in _CLOSED_STATES
               and e['src'] != '127.0.0.1' and e['dst'] != '127.0.0.1']
    return jsonify({'states': entries, 'count': len(entries)})


@app.route("/firewall", endpoint="index")
@app.route("/index")
@login_required
def firewall():
    global dirty
    user = session.get("username")
    return render_template("firewall.html", rules=pending_rules, labels=INTERFACE_LABELS, dirty=dirty, user=user)


@app.route("/delete", methods=["POST"])
@login_required
@admin_required
def delete_rule():
    global dirty
    idx = int(request.form["rule_num"])
    if 0 <= idx < len(pending_rules):
        del pending_rules[idx]
        save_config()
        dirty = True
    return redirect(url_for("index"))


@app.route("/add", methods=["POST"])
@login_required
@admin_required
def add_rule():
    global dirty
    iface_in = request.form.get("iface_in") 
    iface_out = request.form.get("iface_out") 
    src = request.form.get("src") or "0.0.0.0/0" 
    dst = request.form.get("dst") or "0.0.0.0/0" 
    proto = request.form.get("proto") 
    dport = request.form.get("dport") 
    action = request.form.get("action")
    if not src or src.lower() == "any": 
        src = "0.0.0.0/0" 
    if not dst or dst.lower() == "any": 
        dst = "0.0.0.0/0" 

    comment = request.form.get("comment", "").strip()
    rule = {
        "iface_in": iface_in,
        "iface_out": iface_out,
        "src": src,
        "dst": dst,
        "proto": proto,
        "dport": dport,
        "action": action,
        "comment": comment,
    }

    pending_rules.append(rule)
    save_config()
    dirty = True

    return redirect(url_for("index"))


@app.route("/move", methods=["POST"])
@login_required
@admin_required
def move_rule():
    global dirty
    idx = int(request.form["rule_num"])
    direction = request.form["direction"]

    if direction == "up" and idx > 0:
        pending_rules[idx - 1], pending_rules[idx] = pending_rules[idx], pending_rules[idx - 1]
    elif direction == "down" and idx < len(pending_rules) - 1:
        pending_rules[idx + 1], pending_rules[idx] = pending_rules[idx], pending_rules[idx + 1]

    save_config()
    dirty = True
    return redirect(url_for("index"))


def _nat_associated_forward_line(nr):
    """The FORWARD ACCEPT line build_iptables_rules() auto-adds for a port
    forward with auto_fw_rule set. Factored out so parse_iptables_rules()
    can recognize and exclude these framework-managed lines too — they're
    regenerated from nat_rules, not user-authored pending_rules.
    """
    line = f"-A FORWARD -i {nr['iface_in']} -p {nr['proto']}"
    if nr.get('src') and nr['src'] not in ('', '0.0.0.0/0'):
        line += f" -s {nr['src']}"
    line += f" -d {nr['target_ip']} --dport {nr['target_port']} -j ACCEPT"
    return line


def build_iptables_rules(rules, nat_rules=None):
    """Return an iptables-restore compatible *filter table ruleset for the given rule list.

    nat_rules (port forwards, see build_nat_rules) each contribute one ACCEPT
    line here when their auto_fw_rule flag is set — pfSense auto-adds an
    associated filter-rule pass for every port forward by default, since
    otherwise a DNAT would just get default-denied by the FORWARD chain.
    """
    nat_rules = nat_rules or []
    lines = [
        "*filter",
        ":INPUT ACCEPT [0:0]",
        ":FORWARD DROP [0:0]",
        ":OUTPUT ACCEPT [0:0]",
        ":LOGDROP - [0:0]",
        ":LOGREJECT - [0:0]",
        "-A LOGDROP -m limit --limit 5/second -j NFLOG --nflog-group 1 --nflog-prefix \"FW DROP: \" ",
        "-A LOGDROP -j DROP",
        "-A LOGREJECT -m limit --limit 5/second -j NFLOG --nflog-group 1 --nflog-prefix \"FW REJECT: \" ",
        "-A LOGREJECT -j REJECT",
        # Stateful base rules: pass return traffic, drop invalid packets
        "-A FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT",
        "-A FORWARD -m conntrack --ctstate INVALID -j DROP",
    ]
    for r in rules:
        proto = r['proto']
        if proto == 'all':
            line = f"-A FORWARD -s {r['src']} -d {r['dst']}"
        else:
            line = f"-A FORWARD -p {proto} -s {r['src']} -d {r['dst']}"
        if r.get('iface_in'): line += f" -i {r['iface_in']}"
        if r.get('iface_out'): line += f" -o {r['iface_out']}"
        if r.get('dport') and proto in ['tcp', 'udp']: line += f" --dport {r['dport']}"
        if r["action"] in ["DROP", "REJECT"]:
            line += f" -j LOG{r['action']}"
        else:
            line += f" -j {r['action']}"
        lines.append(line)
    # Associated filter rules for enabled port forwards (pfSense-style
    # "auto-add filter rule"). Matched on the forward's translated
    # (post-DNAT) destination, since that's what the FORWARD chain actually
    # sees after PREROUTING rewrites the packet.
    for nr in nat_rules:
        if not nr.get('enabled', True) or not nr.get('auto_fw_rule', True):
            continue
        lines.append(_nat_associated_forward_line(nr))
    # No blanket accept for WireGuard interfaces: each tunnel is a normal,
    # selectable interface (see _detect_interface_labels), so VPN traffic is
    # scoped by the same per-interface rules above as any other zone —
    # matches pfSense's model instead of trusting all decrypted VPN traffic.
    # Default allow for ICS-originated traffic (trusted → untrusted).
    # Match on source subnet rather than interface name — interface assignment
    # is not deterministic in Docker containers.
    lines.append(f"-A FORWARD -s {ICS_SUBNET} -j ACCEPT")
    # Catch-all: log and drop everything else (untrusted inbound not matched above)
    lines.append("-A FORWARD -j LOGDROP")
    lines.append("COMMIT")
    return "\n".join(lines) + "\n"


def build_nat_rules(nat_rules):
    """Return an iptables-restore compatible *nat table PREROUTING stanza
    (the DNAT half of a port forward, pfSense-style).

    POSTROUTING is deliberately left out of this stanza: it's owned by
    network-init.py's rebuild_nat() and WireGuard's per-tunnel masquerade
    calls (_ensure_wg_masquerade). iptables-restore -n (noflush) only
    flushes/replaces chains actually listed in the file being restored, so
    omitting POSTROUTING here leaves those other rules untouched.
    """
    lines = ["*nat", ":PREROUTING ACCEPT [0:0]"]
    for r in nat_rules:
        if not r.get('enabled', True):
            continue
        line = f"-A PREROUTING -i {r['iface_in']} -p {r['proto']}"
        if r.get('src') and r['src'] not in ('', '0.0.0.0/0'):
            line += f" -s {r['src']}"
        if r.get('dst'):
            line += f" -d {r['dst']}"
        line += f" --dport {r['ext_port']} -j DNAT --to-destination {r['target_ip']}:{r['target_port']}"
        lines.append(line)
    lines.append("COMMIT")
    return "\n".join(lines) + "\n"


def _apply_rules_now(rules, nat_rules=None):
    """Write the iptables ruleset for `rules`/`nat_rules` to disk and load it. Returns the proc result."""
    nat_rules = nat_rules or []
    os.makedirs(os.path.dirname(FIREWALL_RULES_PATH), exist_ok=True)
    rules_text = build_nat_rules(nat_rules) + build_iptables_rules(rules, nat_rules)
    with open(FIREWALL_RULES_PATH, "w") as f:
        f.write(rules_text)
    subprocess.run(["iptables", "-F", "FORWARD"], check=False)
    subprocess.run(["iptables", "-t", "nat", "-F", "PREROUTING"], check=False)
    return subprocess.run(["iptables-restore", "-n", FIREWALL_RULES_PATH])


@app.route("/apply", methods=["POST"])
@login_required
@admin_required
def apply_changes():
    load_config()
    proc = _apply_rules_now(pending_rules, nat_rules)
    if proc.returncode != 0:
        flash("Error applying firewall rules!", "danger")
    else:
        flash("Firewall rules applied successfully.", "success")
    save_config()
    return redirect(url_for("index"))

@app.route("/revert", methods=["POST"])
@login_required
@admin_required
def revert_changes():
    global pending_rules, dirty
    pending_rules = parse_iptables_rules()
    save_config()
    dirty = False
    flash("Reverted to active iptables configuration", "info")
    return redirect(url_for("index"))


@app.route("/nat")
@login_required
def nat_page():
    user = session.get("username")
    return render_template("nat.html", active_page="nat", nat_rules=nat_rules,
                            labels=INTERFACE_LABELS, dirty=dirty, user=user)


def _validate_nat_form(form):
    """Validate a submitted port-forward form. Returns (rule_dict, errors)."""
    iface_in = form.get("iface_in", "")
    proto = form.get("proto", "tcp")
    src = form.get("src", "").strip() or "0.0.0.0/0"
    if src.lower() == "any":
        src = "0.0.0.0/0"
    dst = form.get("dst", "").strip()
    if dst.lower() == "any":
        dst = ""
    ext_port = form.get("ext_port", "").strip()
    target_ip = form.get("target_ip", "").strip()
    target_port = form.get("target_port", "").strip() or ext_port
    auto_fw_rule = form.get("auto_fw_rule") == "on"
    comment = form.get("comment", "").strip()

    errors = []
    if not iface_in or iface_in not in INTERFACE_LABELS:
        errors.append("Select a valid incoming interface.")
    if proto not in ("tcp", "udp"):
        errors.append("Protocol must be TCP or UDP.")
    if not ext_port.isdigit() or not (1 <= int(ext_port) <= 65535):
        errors.append("External port must be a number between 1 and 65535.")
    if not target_port.isdigit() or not (1 <= int(target_port) <= 65535):
        errors.append("Target port must be a number between 1 and 65535.")
    try:
        ipaddress.ip_address(target_ip)
    except ValueError:
        errors.append("Target IP must be a valid IPv4 address.")
    if dst:
        try:
            ipaddress.ip_address(dst)
        except ValueError:
            errors.append("Destination address must be a valid IPv4 address, or left blank for any.")

    rule = {
        "iface_in": iface_in,
        "proto": proto,
        "src": src,
        "dst": dst,
        "ext_port": ext_port,
        "target_ip": target_ip,
        "target_port": target_port,
        "auto_fw_rule": auto_fw_rule,
        "enabled": True,
        "comment": comment,
    }
    return rule, errors


@app.route("/nat/add", methods=["POST"])
@login_required
@admin_required
def nat_add_rule():
    global dirty
    rule, errors = _validate_nat_form(request.form)
    if errors:
        for e in errors:
            flash(e, "danger")
        return redirect(url_for("nat_page"))

    nat_rules.append(rule)
    save_config()
    dirty = True
    return redirect(url_for("nat_page"))


@app.route("/nat/delete", methods=["POST"])
@login_required
@admin_required
def nat_delete_rule():
    global dirty
    idx = int(request.form["rule_num"])
    if 0 <= idx < len(nat_rules):
        del nat_rules[idx]
        save_config()
        dirty = True
    return redirect(url_for("nat_page"))


@app.route("/nat/toggle", methods=["POST"])
@login_required
@admin_required
def nat_toggle_rule():
    global dirty
    idx = int(request.form["rule_num"])
    if 0 <= idx < len(nat_rules):
        nat_rules[idx]["enabled"] = not nat_rules[idx].get("enabled", True)
        save_config()
        dirty = True
    return redirect(url_for("nat_page"))


@app.route("/nat/move", methods=["POST"])
@login_required
@admin_required
def nat_move_rule():
    global dirty
    idx = int(request.form["rule_num"])
    direction = request.form["direction"]
    if direction == "up" and idx > 0:
        nat_rules[idx - 1], nat_rules[idx] = nat_rules[idx], nat_rules[idx - 1]
    elif direction == "down" and idx < len(nat_rules) - 1:
        nat_rules[idx + 1], nat_rules[idx] = nat_rules[idx], nat_rules[idx + 1]
    save_config()
    dirty = True
    return redirect(url_for("nat_page"))


@app.route("/ids")
@login_required
def ids():
    # Load existing rules as flat text
    try:
        with open(IDS_RULES_FILE, "r") as f:
            rule_text = f.read()
    except FileNotFoundError:
        rule_text = ""

    alerts = get_recent_alerts()
    builtin_rules = load_builtin_rules()
    stats = {
        "status": "Running",
        "alerts_today": len(alerts),
        "rules_count": len(rule_text.strip().splitlines()) if rule_text.strip() else 0,
        "builtin_count": len(builtin_rules),
    }

    return render_template(
        "ids.html",
        active_page="ids",
        alerts=alerts,
        rule_text=rule_text,
        builtin_rules=builtin_rules,
        stats=stats,
    )


@app.route("/ids/save_rules", methods=["POST"])
@login_required
@admin_required
def save_rules():
    new_rules = request.form.get("rules_text", "")
    os.makedirs(os.path.dirname(IDS_RULES_FILE), exist_ok=True)
    with open(IDS_RULES_FILE, "w") as f:
        f.write(new_rules.strip() + "\n")

    try:
        subprocess.run(["pkill", "-USR2", "Suricata-Main"], check=False)
        flash("Rules saved and Suricata reloaded.", "success")
    except Exception as e:
        flash(f"Rules saved, but reload failed: {e}", "warning")

    return redirect(url_for("ids"))



@app.route("/firewall/logs")
@login_required
def firewall_logs():
    entries = parse_firewall_logs(limit=200)
    user = session.get("username")
    return render_template("firewall_logs.html", entries=entries, user=user)


@app.route("/dns")
@login_required
def dns():
    config = load_dns_config()
    queries = get_dns_queries(limit=50)
    return render_template("dns.html", active_page="dns",
                           hosts=config.get("hosts", []),
                           blocked=config.get("blocked", []),
                           queries=queries)


@app.route("/dns/add_host", methods=["POST"])
@login_required
@admin_required
def dns_add_host():
    hostname = request.form.get("hostname", "").strip().lower()
    ip = request.form.get("ip", "").strip()
    comment = request.form.get("comment", "").strip()
    if hostname and ip:
        config = load_dns_config()
        config["hosts"].append({"hostname": hostname, "ip": ip, "comment": comment})
        save_dns_config(config)
        apply_dns_config(config)
        flash(f"Host entry added: {hostname} → {ip}", "success")
    else:
        flash("Hostname and IP are required.", "danger")
    return redirect(url_for("dns"))


@app.route("/dns/delete_host", methods=["POST"])
@login_required
@admin_required
def dns_delete_host():
    idx = int(request.form["idx"])
    config = load_dns_config()
    if 0 <= idx < len(config["hosts"]):
        removed = config["hosts"].pop(idx)
        save_dns_config(config)
        apply_dns_config(config)
        flash(f"Host entry removed: {removed['hostname']}", "success")
    return redirect(url_for("dns"))


@app.route("/dns/add_block", methods=["POST"])
@login_required
@admin_required
def dns_add_block():
    # Strip leading wildcards/dots so "*.evil.com" and "evil.com" both become "evil.com"
    domain = request.form.get("domain", "").strip().lower().lstrip("*.").strip(".")
    comment = request.form.get("comment", "").strip()
    if domain:
        config = load_dns_config()
        config["blocked"].append({"domain": domain, "comment": comment})
        save_dns_config(config)
        apply_dns_config(config)
        flash(f"Domain blocked: {domain}", "success")
    else:
        flash("Domain is required.", "danger")
    return redirect(url_for("dns"))


@app.route("/dns/delete_block", methods=["POST"])
@login_required
@admin_required
def dns_delete_block():
    idx = int(request.form["idx"])
    config = load_dns_config()
    if 0 <= idx < len(config["blocked"]):
        removed = config["blocked"].pop(idx)
        save_dns_config(config)
        apply_dns_config(config)
        flash(f"Block removed: {removed['domain']}", "success")
    return redirect(url_for("dns"))


@app.route("/api/dns/queries")
@login_required
def api_dns_queries():
    queries = get_dns_queries(limit=100)
    return jsonify({"queries": queries, "count": len(queries)})


# --- wireguard routes ---

def _client_routes_include(client_routes, target_network):
    for part in (client_routes or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            net = ipaddress.ip_network(part, strict=False)
        except ValueError:
            continue
        if net.overlaps(target_network):
            return True
    return False


@app.route("/vpn")
@login_required
def vpn():
    config = load_wg_config()
    tunnels = [
        {**t, "up": wg_iface_up(t["name"]), "peer_count": len(t.get("peers", []))}
        for t in config.get("tunnels", [])
    ]
    suggested_subnet, suggested_port = _suggest_tunnel_defaults(config)
    return render_template(
        "wireguard.html",
        active_page="vpn",
        tunnels=tunnels,
        suggested_subnet=suggested_subnet,
        suggested_port=suggested_port,
    )


@app.route("/vpn/add_tunnel", methods=["POST"])
@login_required
@admin_required
def vpn_add_tunnel():
    config = load_wg_config()
    name = request.form.get("name", "").strip()
    label = request.form.get("label", "").strip() or name
    client_routes = request.form.get("client_routes", "").strip()
    try:
        port = int(request.form.get("listen_port", "").strip())
    except ValueError:
        port = None
    try:
        network = ipaddress.ip_network(request.form.get("subnet", "").strip(), strict=False)
    except ValueError:
        network = None

    if not name or not re.match(r'^[a-zA-Z0-9_-]{1,15}$', name):
        flash("Tunnel name must be a short alphanumeric identifier, e.g. wg1.", "danger")
    elif find_tunnel(config, name):
        flash(f"Tunnel '{name}' already exists.", "danger")
    elif name in _existing_link_names() - {t["name"] for t in config["tunnels"]}:
        flash(f"'{name}' is already a network interface on this system — choose a different tunnel name.", "danger")
    elif network is None:
        flash("Invalid subnet — use CIDR notation, e.g. 10.100.1.0/24.", "danger")
    elif port is None or not (1 <= port <= 65535):
        flash("Invalid listen port.", "danger")
    elif any(network.overlaps(n) for n in
             [n for _, n in BUILTIN_ZONE_NETWORKS] + [n for _, n in _configured_zone_networks()]
             + [ipaddress.ip_network(t["subnet"], strict=False) for t in config["tunnels"]]):
        flash("Subnet overlaps with an existing zone or tunnel.", "danger")
    elif any(t.get("listen_port") == port for t in config["tunnels"]):
        flash("Listen port already used by another tunnel.", "danger")
    else:
        priv, pub = wg_genkey()
        tunnel = {
            "name": name,
            "label": label,
            "listen_port": port,
            "subnet": str(network),
            "private_key": priv,
            "public_key": pub,
            "client_routes": client_routes,
            "peers": [],
        }
        config["tunnels"].append(tunnel)
        save_wg_config(config)
        result = apply_wg_tunnel(tunnel)
        _refresh_interface_labels()
        if result.returncode == 0:
            flash(f"Tunnel '{name}' created and started. Add firewall rules on this "
                  f"interface to grant it access — it has none by default.", "success")
        else:
            flash(f"Tunnel saved but failed to start: {result.stderr}", "danger")
    return redirect(url_for("vpn"))


@app.route("/vpn/<name>/delete", methods=["POST"])
@login_required
@admin_required
def vpn_delete_tunnel(name):
    config = load_wg_config()
    tunnel = find_tunnel(config, name)
    if tunnel:
        subprocess.run(["wg-quick", "down", name], capture_output=True)
        try:
            os.remove(os.path.join(WG_CONF_DIR, f"{name}.conf"))
        except OSError:
            pass
        subprocess.run(
            ["iptables", "-t", "nat", "-D", "POSTROUTING", "-s", tunnel["subnet"], "-j", "MASQUERADE"],
            check=False, stderr=subprocess.DEVNULL,
        )
        config["tunnels"] = [t for t in config["tunnels"] if t["name"] != name]
        save_wg_config(config)
        _refresh_interface_labels()
        flash(f"Tunnel '{name}' deleted.", "success")
    return redirect(url_for("vpn"))


@app.route("/vpn/<name>")
@login_required
def vpn_tunnel(name):
    config = load_wg_config()
    tunnel = find_tunnel(config, name)
    if not tunnel:
        flash("Tunnel not found.", "danger")
        return redirect(url_for("vpn"))
    return render_template(
        "vpn_tunnel.html",
        active_page="vpn",
        tunnel=tunnel,
        peer_status=parse_wg_show(name),
        iface_up=wg_iface_up(name),
    )


@app.route("/vpn/<name>/toggle", methods=["POST"])
@login_required
@admin_required
def vpn_toggle_tunnel(name):
    config = load_wg_config()
    tunnel = find_tunnel(config, name)
    if not tunnel:
        flash("Tunnel not found.", "danger")
        return redirect(url_for("vpn"))
    if wg_iface_up(name):
        subprocess.run(["wg-quick", "down", name], check=False)
        flash(f"Tunnel '{name}' stopped.", "info")
    else:
        result = apply_wg_tunnel(tunnel)
        if result.returncode == 0:
            flash(f"Tunnel '{name}' started.", "success")
        else:
            flash(f"Failed to start '{name}': {result.stderr}", "danger")
    _refresh_interface_labels()
    return redirect(url_for("vpn_tunnel", name=name))


@app.route("/vpn/<name>/add_peer", methods=["POST"])
@login_required
@admin_required
def vpn_add_peer(name):
    config = load_wg_config()
    tunnel = find_tunnel(config, name)
    if not tunnel:
        flash("Tunnel not found.", "danger")
        return redirect(url_for("vpn"))
    peer_name = request.form.get("name", "").strip()
    public_key = request.form.get("public_key", "").strip()
    allowed_ips = request.form.get("allowed_ips", "").strip()
    comment = request.form.get("comment", "").strip()
    if not peer_name or not public_key or not allowed_ips:
        flash("Name, public key, and allowed IPs are required.", "danger")
    else:
        tunnel["peers"].append({
            "name": peer_name,
            "public_key": public_key,
            "allowed_ips": allowed_ips,
            "comment": comment,
        })
        save_wg_config(config)
        result = apply_wg_tunnel(tunnel)
        if result.returncode == 0:
            flash(f"Peer '{peer_name}' added.", "success")
        else:
            flash(f"Peer saved but apply failed: {result.stderr}", "warning")
    return redirect(url_for("vpn_tunnel", name=name))


@app.route("/vpn/<name>/delete_peer", methods=["POST"])
@login_required
@admin_required
def vpn_delete_peer(name):
    config = load_wg_config()
    tunnel = find_tunnel(config, name)
    if not tunnel:
        flash("Tunnel not found.", "danger")
        return redirect(url_for("vpn"))
    try:
        idx = int(request.form.get("idx", -1))
    except ValueError:
        idx = -1
    peers = tunnel.get("peers", [])
    if 0 <= idx < len(peers):
        removed = peers.pop(idx)
        save_wg_config(config)
        apply_wg_tunnel(tunnel)
        flash(f"Peer '{removed['name']}' removed.", "success")
    return redirect(url_for("vpn_tunnel", name=name))


@app.route("/vpn/<name>/client_config/<int:idx>")
@login_required
def vpn_client_config(name, idx):
    config = load_wg_config()
    tunnel = find_tunnel(config, name)
    if not tunnel:
        flash("Tunnel not found.", "danger")
        return redirect(url_for("vpn"))
    peers = tunnel.get("peers", [])
    if idx >= len(peers):
        flash("Peer not found.", "danger")
        return redirect(url_for("vpn_tunnel", name=name))
    peer = peers[idx]
    try:
        wan_iface = next((k for k, v in INTERFACE_LABELS.items() if v == 'DMZ'), None)
        wan_info = subprocess.check_output(["ip", "-4", "addr", "show", wan_iface], text=True)
        match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", wan_info)
        endpoint = match.group(1) if match else "YOUR_ROUTER_WAN_IP"
    except Exception:
        endpoint = "YOUR_ROUTER_WAN_IP"

    client_routes = tunnel.get("client_routes", "").strip()
    dns_line = ""
    ics_net = ipaddress.ip_network(ICS_SUBNET)
    if _client_routes_include(client_routes, ics_net):
        dns_line = f"DNS = {list(ics_net.hosts())[0]}\n"

    client_conf = (
        f"# Client config for: {peer['name']} (tunnel: {tunnel.get('label', name)})\n"
        f"# Run 'wg genkey | tee privkey | wg pubkey > pubkey' to generate your keys,\n"
        f"# then replace <your-private-key> below.\n\n"
        f"[Interface]\n"
        f"PrivateKey = <your-private-key>\n"
        f"Address = {peer['allowed_ips'].split(',')[0].strip()}\n"
        f"{dns_line}\n"
        f"[Peer]\n"
        f"PublicKey = {tunnel['public_key']}\n"
        f"Endpoint = {endpoint}:{tunnel.get('listen_port', DEFAULT_TUNNEL_PORT)}\n"
        f"AllowedIPs = {client_routes or tunnel['subnet']}\n"
        f"PersistentKeepalive = 25\n"
    )
    from flask import Response
    return Response(
        client_conf,
        mimetype="text/plain",
        headers={"Content-Disposition": f"attachment; filename={name}-{peer['name']}.conf"},
    )


@app.route("/api/vpn/status")
@login_required
def api_vpn_status():
    config = load_wg_config()
    tunnels = {
        t["name"]: {"up": wg_iface_up(t["name"]), "peers": parse_wg_show(t["name"])}
        for t in config.get("tunnels", [])
    }
    return jsonify({"tunnels": tunnels})


# --- diagnostics routes ---

_DIAG_TARGET_RE = re.compile(r'^[a-zA-Z0-9.\-_]{1,253}$')
PCAP_PATH = "/tmp/diag_capture.pcap"


@app.route("/diagnostics", methods=["GET", "POST"])
@login_required
def diagnostics():
    output = None
    tool = None
    error = None
    pcap_available = False

    if request.method == "POST":
        tool = request.form.get("tool")
        lan_iface = next((k for k, v in INTERFACE_LABELS.items() if v == 'LAN'), 'eth1')
        iface = request.form.get("iface", lan_iface)
        target = request.form.get("target", "").strip()
        bpf = request.form.get("bpf", "").strip()

        try:
            count_raw = int(request.form.get("count", "4"))
            count = max(1, min(count_raw, 50))
        except ValueError:
            count = 4

        if iface not in INTERFACE_LABELS:
            error = "Invalid interface."
        elif tool in ("ping", "traceroute") and not _DIAG_TARGET_RE.match(target):
            error = "Invalid target — use a hostname or IP address."
        else:
            cmd = None
            timeout = 30
            if tool == "ping":
                cmd = ["ping", "-c", str(count), "-W", "2", "-I", iface, target]
            elif tool == "traceroute":
                cmd = ["traceroute", "-i", iface, "-w", "2", target]
                timeout = 60
            elif tool == "tcpdump":
                # remove stale file — tcpdump drops to 'tcpdump' user before
                # opening the output file, so it can't overwrite a root-owned file
                try:
                    os.remove(PCAP_PATH)
                except FileNotFoundError:
                    pass
                cap_cmd = ["tcpdump", "-i", iface, "-c", str(count), "-n",
                           "--no-promiscuous-mode", "-w", PCAP_PATH]
                if bpf:
                    cap_cmd.append(bpf)
                try:
                    subprocess.run(cap_cmd, capture_output=True, timeout=30)
                except subprocess.TimeoutExpired:
                    pass  # partial pcap is still valid
                if os.path.exists(PCAP_PATH) and os.path.getsize(PCAP_PATH) > 24:
                    r2 = subprocess.run(["tcpdump", "-r", PCAP_PATH, "-n"],
                                        capture_output=True, text=True, timeout=10)
                    output = r2.stdout + r2.stderr
                    pcap_available = True
                else:
                    output = "(no packets captured — interface may be idle)"
            else:
                error = "Unknown tool."

            if cmd:
                try:
                    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
                    output = r.stdout + r.stderr
                except subprocess.TimeoutExpired as e:
                    decode = lambda b: b.decode(errors="replace") if isinstance(b, bytes) else (b or "")
                    output = decode(e.stdout) + decode(e.stderr) + "\n[timed out]"

        if error:
            flash(error, "danger")

    return render_template(
        "diagnostics.html",
        active_page="diagnostics",
        interfaces=INTERFACE_LABELS,
        tool=tool,
        output=output,
        pcap_available=pcap_available,
    )


@app.route("/diagnostics/download_pcap")
@login_required
def download_pcap():
    from flask import send_file
    if not os.path.exists(PCAP_PATH) or os.path.getsize(PCAP_PATH) <= 24:
        flash("No capture file available.", "danger")
        return redirect(url_for("diagnostics"))
    return send_file(
        PCAP_PATH,
        as_attachment=True,
        download_name="capture.pcap",
        mimetype="application/vnd.tcpdump.pcap",
    )


# --- arp monitoring routes ---

@app.route("/arp")
@login_required
def arp():
    try:
        with open(ARPMON_STATE) as f:
            devices = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        devices = {}

    events = []
    try:
        with open(ARPMON_LOG) as f:
            for line in f:
                try:
                    events.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        pass

    return render_template(
        "arp.html",
        active_page="arp",
        devices=devices,
        events=events[-100:],
    )


# --- log clearing routes ---

def _truncate_log(path):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, 'w').close()
        return True
    except OSError:
        return False


@app.route("/firewall/logs/clear", methods=["POST"])
@login_required
@admin_required
def clear_firewall_logs():
    if _truncate_log(LOG_FILE):
        flash("Firewall logs cleared.", "success")
    else:
        flash("Failed to clear firewall logs.", "danger")
    return redirect(url_for("firewall_logs"))


@app.route("/ids/clear_alerts", methods=["POST"])
@login_required
@admin_required
def clear_ids_alerts():
    if _truncate_log(SURICATA_EVE_FILE):
        flash("IDS alerts cleared.", "success")
    else:
        flash("Failed to clear IDS alerts.", "danger")
    return redirect(url_for("ids"))


@app.route("/dns/clear_queries", methods=["POST"])
@login_required
@admin_required
def clear_dns_queries():
    if _truncate_log(DNSMASQ_LOG):
        flash("DNS query log cleared.", "success")
    else:
        flash("Failed to clear DNS query log.", "danger")
    return redirect(url_for("dns"))


@app.route("/arp/clear_events", methods=["POST"])
@login_required
@admin_required
def clear_arp_events():
    if _truncate_log(ARPMON_LOG):
        flash("ARP events cleared.", "success")
    else:
        flash("Failed to clear ARP events.", "danger")
    return redirect(url_for("arp"))


@app.route("/arp/clear_devices", methods=["POST"])
@login_required
@admin_required
def clear_arp_devices():
    try:
        os.makedirs(os.path.dirname(ARPMON_STATE), exist_ok=True)
        with open(ARPMON_STATE, 'w') as f:
            json.dump({}, f)
        flash("Known devices reset.", "success")
    except OSError:
        flash("Failed to reset known devices.", "danger")
    return redirect(url_for("arp"))


# --- settings / user management routes ---

@app.route("/settings/users")
@login_required
def settings_users():
    return render_template("settings.html", active_page="settings",
                           users=users, current_user=session["username"],
                           current_role=session.get("role"))


@app.route("/settings/export")
@login_required
@admin_required
def export_config():
    """Bundle every persisted config store into one downloadable JSON file.

    Includes secrets (WireGuard private keys, user password hashes) so the
    file is a real backup, not just a shareable snapshot -- treat it like a
    credential.
    """
    try:
        with open(IDS_RULES_FILE) as f:
            ids_rules_text = f.read()
    except FileNotFoundError:
        ids_rules_text = ""

    bundle = {
        "schema_version": 1,
        "exported_at": datetime.now().isoformat(),
        "firewall": {
            "rules": pending_rules,
            "nat_rules": nat_rules,
            "zones": zones,
            "ids_monitor": ids_monitor,
            "zone_iface_overrides": zone_iface_overrides,
            "gateway_skip": gateway_skip,
        },
        "users": users,
        "dns": load_dns_config(),
        "ids_custom_rules": ids_rules_text,
        "vpn": load_wg_config(),
    }

    filename = f"grfics-router-config-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    return Response(
        json.dumps(bundle, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.route("/settings/import", methods=["POST"])
@login_required
@admin_required
def import_config():
    """Wholesale-replace every persisted config store from an export_config() bundle.

    This is a restore, not a merge: firewall/NAT rules, zones, DNS, IDS
    custom rules, VPN tunnels, and users are all replaced outright and
    re-applied live. Unlike add_zone()/vpn_add_tunnel(), it does not
    re-validate subnets for overlap -- the bundle is assumed to already be
    an internally-consistent config that was exported from a working router.
    """
    global pending_rules, nat_rules, zones, ids_monitor, zone_iface_overrides, gateway_skip, users, dirty

    upload = request.files.get("config_file")
    if not upload or not upload.filename:
        flash("Choose a config file to import.", "danger")
        return redirect(url_for("settings_users"))

    try:
        bundle = json.load(upload.stream)
    except (json.JSONDecodeError, UnicodeDecodeError):
        flash("That file isn't valid JSON.", "danger")
        return redirect(url_for("settings_users"))

    firewall = bundle.get("firewall")
    vpn = bundle.get("vpn")
    dns_cfg = bundle.get("dns")
    imported_users = bundle.get("users")
    if (bundle.get("schema_version") != 1 or not isinstance(firewall, dict)
            or not isinstance(vpn, dict) or not isinstance(dns_cfg, dict)
            or not isinstance(imported_users, list)):
        flash("That file doesn't look like a router config export.", "danger")
        return redirect(url_for("settings_users"))
    if not any(u.get("role") == "admin" for u in imported_users):
        flash("Refusing to import: the file has no admin user, which would lock everyone out.", "danger")
        return redirect(url_for("settings_users"))

    # --- firewall / NAT / zones / users ---
    pending_rules = firewall.get("rules", [])
    nat_rules = firewall.get("nat_rules", [])
    zones = firewall.get("zones", [])
    ids_monitor = {**DEFAULT_IDS_MONITOR, **firewall.get("ids_monitor", {})}
    zone_iface_overrides = firewall.get("zone_iface_overrides", {})
    gateway_skip = firewall.get("gateway_skip", [])
    users = imported_users
    save_config()
    dirty = False
    _apply_network()
    fw_proc = _apply_rules_now(pending_rules, nat_rules)

    # --- DNS ---
    save_dns_config(dns_cfg)
    apply_dns_config(dns_cfg)

    # --- IDS custom rules ---
    ids_rules_text = bundle.get("ids_custom_rules", "") or ""
    os.makedirs(os.path.dirname(IDS_RULES_FILE), exist_ok=True)
    with open(IDS_RULES_FILE, "w") as f:
        f.write(ids_rules_text.strip() + ("\n" if ids_rules_text.strip() else ""))
    subprocess.run(["pkill", "-USR2", "Suricata-Main"], check=False)

    # --- VPN tunnels: tear down whatever's running that isn't in the
    # import, then bring up the imported set ---
    imported_tunnels = vpn.get("tunnels", [])
    imported_names = {t["name"] for t in imported_tunnels}
    for t in load_wg_config().get("tunnels", []):
        if t["name"] not in imported_names:
            subprocess.run(["wg-quick", "down", t["name"]], capture_output=True)
            try:
                os.remove(os.path.join(WG_CONF_DIR, f"{t['name']}.conf"))
            except OSError:
                pass
    save_wg_config(vpn)
    for tunnel in imported_tunnels:
        apply_wg_tunnel(tunnel)
    _refresh_interface_labels()

    if fw_proc.returncode != 0:
        flash("Config imported, but applying the firewall/NAT rules failed — check them on the Firewall page.", "danger")
    else:
        flash("Config imported and applied. If the imported file changed your account, "
              "you'll need to log back in with the restored credentials once your session ends.", "success")
    return redirect(url_for("settings_users"))


@app.route("/interfaces")
@login_required
def interfaces():
    return render_template("interfaces.html", active_page="interfaces",
                           current_role=session.get("role"),
                           zones=zones, ids_monitor=ids_monitor,
                           gateway_skip=gateway_skip,
                           interface_labels=INTERFACE_LABELS,
                           available_ifaces=_list_unconfigured_ifaces())


@app.route("/settings/change_password", methods=["POST"])
@login_required
def change_password():
    current = request.form.get("current_password", "")
    new = request.form.get("new_password", "").strip()
    confirm = request.form.get("confirm_password", "").strip()
    rec = next((u for u in users if u["username"] == session["username"]), None)
    if not rec or not check_password_hash(rec["password_hash"], current):
        flash("Current password is incorrect.", "danger")
    elif new != confirm:
        flash("New passwords do not match.", "danger")
    elif len(new) < 6:
        flash("Password must be at least 6 characters.", "danger")
    else:
        rec["password_hash"] = generate_password_hash(new)
        save_config()
        flash("Password updated.", "success")
    return redirect(url_for("settings_users"))


@app.route("/settings/add_user", methods=["POST"])
@login_required
@admin_required
def add_user():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    role = request.form.get("role", "viewer")
    if not username or not password:
        flash("Username and password are required.", "danger")
    elif any(u["username"] == username for u in users):
        flash(f"User '{username}' already exists.", "danger")
    elif role not in ("admin", "viewer"):
        flash("Invalid role.", "danger")
    else:
        users.append({"username": username,
                      "password_hash": generate_password_hash(password),
                      "role": role})
        save_config()
        flash(f"User '{username}' added.", "success")
    return redirect(url_for("settings_users"))


@app.route("/settings/delete_user", methods=["POST"])
@login_required
@admin_required
def delete_user():
    global users
    username = request.form.get("username", "")
    if username == session["username"]:
        flash("Cannot delete your own account.", "danger")
    else:
        users = [u for u in users if u["username"] != username]
        save_config()
        flash(f"User '{username}' deleted.", "success")
    return redirect(url_for("settings_users"))


@app.route("/settings/zones/bind_builtin", methods=["POST"])
@login_required
@admin_required
def bind_builtin_zone():
    zone = request.form.get("zone", "")
    iface = request.form.get("iface", "").strip()
    if zone not in ("LAN", "DMZ"):
        flash("Invalid zone.", "danger")
    elif iface not in _list_unconfigured_ifaces():
        flash("That interface is unavailable — pick an unconfigured NIC.", "danger")
    else:
        zone_iface_overrides[zone] = iface
        save_config()
        _apply_network()
        flash(f"{zone} bound to {iface}.", "success")
    return redirect(url_for("interfaces"))


@app.route("/settings/zones/add", methods=["POST"])
@login_required
@admin_required
def add_zone():
    iface = request.form.get("iface", "").strip()
    label = request.form.get("label", "").strip() or iface
    monitor = request.form.get("ids_monitor") == "on"

    try:
        network = ipaddress.ip_network(request.form.get("subnet", "").strip(), strict=False)
    except ValueError:
        network = None

    known_networks = ([n for _, n in BUILTIN_ZONE_NETWORKS]
                       + [n for _, n in _configured_zone_networks()]
                       + [n for _, n in _configured_tunnel_networks()])

    if iface not in _list_unconfigured_ifaces():
        flash("That interface is unavailable — pick an unconfigured NIC.", "danger")
    elif network is None:
        flash("Invalid subnet — use CIDR notation, e.g. 192.168.50.0/24.", "danger")
    elif any(network.overlaps(n) for n in known_networks):
        flash("Subnet overlaps with an existing zone or VPN tunnel.", "danger")
    else:
        zones.append({"iface": iface, "subnet": str(network), "label": label, "ids_monitor": monitor})
        save_config()
        _apply_network()
        flash(f"Zone '{label}' added on {iface}.", "success")
    return redirect(url_for("interfaces"))


@app.route("/settings/zones/delete", methods=["POST"])
@login_required
@admin_required
def delete_zone():
    global zones
    try:
        idx = int(request.form.get("idx", -1))
    except ValueError:
        idx = -1
    if 0 <= idx < len(zones):
        removed = zones.pop(idx)
        save_config()
        try:
            network = ipaddress.ip_network(removed["subnet"], strict=False)
            hosts = list(network.hosts())  # generator normally, but a plain list for /31 and /32
            if hosts:
                subprocess.run(["ip", "addr", "del", f"{hosts[0]}/{network.prefixlen}", "dev", removed["iface"]],
                                check=False, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        _apply_network()
        flash(f"Zone '{removed.get('label', removed.get('iface'))}' removed.", "success")
    return redirect(url_for("interfaces"))


@app.route("/settings/zones/ids_monitor", methods=["POST"])
@login_required
@admin_required
def set_ids_monitor():
    key = request.form.get("key", "")
    monitor = request.form.get("ids_monitor") == "on"
    if key in ("LAN", "DMZ"):
        ids_monitor[key] = monitor
    else:
        try:
            idx = int(key)
            if 0 <= idx < len(zones):
                zones[idx]["ids_monitor"] = monitor
        except ValueError:
            pass
    save_config()
    _apply_network()
    return redirect(url_for("interfaces"))


@app.route("/settings/zones/gateway", methods=["POST"])
@login_required
@admin_required
def set_zone_gateway():
    """Toggle whether the router acts as this zone's gateway (holds the
    subnet's .1). The checkbox is 'act as gateway'; unchecking adds the
    zone's label to gateway_skip so network-init.py drops the .1 alias."""
    key = request.form.get("key", "")
    act_as_gateway = request.form.get("gateway") == "on"
    if key in ("LAN", "DMZ"):
        label = key
    else:
        try:
            label = zones[int(key)].get("label")
        except (ValueError, IndexError):
            label = None
    if label:
        if act_as_gateway:
            gateway_skip[:] = [l for l in gateway_skip if l != label]
        elif label not in gateway_skip:
            gateway_skip.append(label)
        save_config()
        _apply_network()
    return redirect(url_for("interfaces"))


load_config()
_apply_rules_now(pending_rules, nat_rules)

for _tunnel in load_wg_config().get("tunnels", []):
    apply_wg_tunnel(_tunnel)
_refresh_interface_labels()

app.run(host="0.0.0.0", port=5000)
