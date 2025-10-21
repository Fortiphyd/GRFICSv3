from flask import Flask, render_template, request, redirect, url_for, session, flash
import subprocess
import json, os, functools
from pathlib import Path
from datetime import datetime

app = Flask(__name__)

INTERFACE_LABELS = {
    "eth0": "Admin",
    "eth1": "LAN",
    "eth2": "WAN"
}

# SECRET_KEY is required for sessions. Set via env var in compose or host.
# For quick local testing you can hardcode, but better: export SECRET_KEY before starting.
app.secret_key = os.environ.get("FWUI_SECRET_KEY", "dev-secret-key-change-me")

# default user (will be persisted when load_config runs if config exists)
DEFAULT_USER = {"username": "admin", "password": "password"}  # intentionally weak for labs

credentials = DEFAULT_USER.copy()  # dict with username/password

LOG_FILE = "/var/log/ulog/netfilter_log.json"
FIREWALL_RULES_PATH = "/etc/firewall/rules"
CONFIG_PATH = "/etc/firewall/config.json"
IDS_ALERTS_FILE = "/etc/suricata/alerts.json"
IDS_RULES_FILE = "/etc/suricata/rules/local.rules"

pending_rules = []
dirty = False

def parse_firewall_logs(limit=100):
    entries = []
    try:
        with open(LOG_FILE) as f:
            for line in f:
                data = json.loads(line)
                entries.append({
                    "time": datetime.fromisoformat(data.get("timestamp")).strftime("%H:%M:%S"),
                    "action": data.get("oob.prefix", "").replace("FW ", "").strip(": "),
                    "proto": {6:"TCP",17:"UDP",1:"ICMP"}.get(data.get("ip.protocol"), str(data.get("ip.protocol"))),
                    "src": f"{data.get('src_ip','?')}:{data.get('src_port','')}",
                    "dst": f"{data.get('dest_ip','?')}:{data.get('dest_port','')}",
                    "iface": f"{data.get('oob.in','?')} → {data.get('oob.out','?')}",
                })
        entries = entries[-limit:]  # last N lines
    except FileNotFoundError:
        pass
    return entries

def get_recent_alerts(limit=50):
    eve_path = Path("/var/log/suricata/eve.json")
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


def load_config():
    global pending_rules, dirty, credentials
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            data = json.load(f)
            pending_rules = data.get("rules", [])
            # optional: allow storing credentials in the config file
            if "auth" in data:
                credentials = data["auth"]
    else:
        pending_rules = []
    dirty = False


def save_config():
    data = {"rules": pending_rules, "auth": credentials}
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)


# --- login helper/decorator ---
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped_view

@app.route("/login", methods=["GET", "POST"])
def login():
    next_url = request.args.get("next") or url_for("index")
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        # simple check against stored credentials
        if username == credentials.get("username") and password == credentials.get("password"):
            session["logged_in"] = True
            session["username"] = username
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


def parse_iptables_rules():
    raw = subprocess.check_output(["iptables", "-S"], text=True).splitlines()
    idx = 0
    rules = []
    for line in raw:
        if not line.startswith('-A'):  # only actual rules
            continue
        idx += 1
        parts = line.split()
        rule = {
            'index': idx,
            'chain': parts[1],
            'iface_in': next((parts[i+1] for i,p in enumerate(parts) if p == '-i'), ''),
            'iface_out': next((parts[i+1] for i,p in enumerate(parts) if p == '-o'), ''),
            'src': next((parts[i+1] for i,p in enumerate(parts) if p == '-s'), 'any'),
            'dst': next((parts[i+1] for i,p in enumerate(parts) if p == '-d'), 'any'),
            'proto': next((parts[i+1] for i,p in enumerate(parts) if p == '-p'), 'any'),
            'dport': next((parts[i+1] for i,p in enumerate(parts) if p == '--dport'), 'any'),
            'action': parts[-1],
        }
        rules.append(rule)
    return rules

@app.route("/", endpoint="index")
@app.route("/firewall")
@app.route("/index")
@login_required
def firewall():
    global dirty
    user = session.get("username")
    return render_template("firewall.html", rules=pending_rules, labels=INTERFACE_LABELS, dirty=dirty, user=user)


@app.route("/delete", methods=["POST"])
@login_required
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

    rule = {
        "iface_in": iface_in,
        "iface_out": iface_out,
        "src": src,
        "dst": dst,
        "proto": proto,
        "dport": dport,
        "action": action,
    }

    pending_rules.append(rule)
    save_config()
    dirty = True

    return redirect(url_for("index"))


@app.route("/move", methods=["POST"])
@login_required
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


@app.route("/apply", methods=["POST"])
@login_required
def apply_changes():
    # Flush FORWARD chain
    subprocess.run(["iptables", "-F", "FORWARD"], check=False)
    # Reapply each saved rule
    load_config()
    rules = pending_rules
    lines = [
        "*filter",
        ":INPUT ACCEPT [0:0]",
        ":FORWARD ACCEPT [0:0]",
        ":OUTPUT ACCEPT [0:0]",
        ":LOGDROP - [0:0]",
        ":LOGREJECT - [0:0]",
        "-A LOGDROP -m limit --limit 5/second -j NFLOG --nflog-group 1 --nflog-prefix \"FW DROP: \" ",
        "-A LOGDROP -j DROP",
        "-A LOGREJECT -m limit --limit 5/second -j NFLOG --nflog-group 1 --nflog-prefix \"FW REJECT: \" ",
        "-A LOGREJECT -j REJECT",
    ]
    for r in rules:
        line = f"-A FORWARD -p {r['proto']} -s {r['src']} -d {r['dst']}"
        if r.get('iface_in'): line += f" -i {r['iface_in']}"
        if r.get('iface_out'): line += f" -o {r['iface_out']}"
        if r.get('dport') and r['proto'] in ['tcp','udp']: line += f" --dport {r['dport']}"
        if r["action"] in ["DROP","REJECT"]:
            act = "LOG" + r["action"]
            line += f" -j {act}"
        else:
            line += f" -j {r['action']}"

        lines.append(line)

    lines.append("COMMIT")
    rules_text = "\n".join(lines) + "\n"

    with open(FIREWALL_RULES_PATH, "w") as f:
        f.write(rules_text)

    proc = subprocess.run(
        ["iptables-restore", "-n", FIREWALL_RULES_PATH],  # -n = don't flush counters
    )

    if proc.returncode != 0:
        flash("Error applying firewall rules!", "danger")
    else:
        flash("Firewall rules applied successfully.", "success")
    save_config()

    return redirect(url_for("index"))

@app.route("/revert", methods=["POST"])
@login_required
def revert_changes():
    global dirty
    rules = parse_iptables_rules()
    pending_rules = rules
    save_config()
    dirty = False
    flash("Reverted to active iptables configuration", "info")
    return redirect(url_for("index"))


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
    stats = {
        "status": "Running",
        "alerts_today": len(alerts),
        "rules_count": len(rule_text.strip().splitlines()) if rule_text.strip() else 0,
    }

    return render_template(
        "ids.html",
        active_page="ids",
        alerts=alerts,
        rule_text=rule_text,
        stats=stats,
    )


@app.route("/ids/save_rules", methods=["POST"])
@login_required
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




load_config()
proc = subprocess.run(
    ["iptables-restore", "-n", FIREWALL_RULES_PATH],  # -n = don't flush counters
)


app.run(host="0.0.0.0", port=5000)
