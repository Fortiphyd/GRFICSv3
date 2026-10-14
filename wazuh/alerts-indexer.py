#!/usr/bin/env python3
"""Tails /var/ossec/logs/alerts/alerts.json and bulk-indexes into OpenSearch."""
import json
import os
import ssl
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

OPENSEARCH = "https://localhost:9200"
ALERTS_FILE = "/var/ossec/logs/alerts/alerts.json"
STATE_FILE = "/var/lib/wazuh-indexer/.alerts_offset"
BATCH = 50

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

import base64
creds = base64.b64encode(b"admin:admin").decode()
HEADERS = {"Content-Type": "application/json", "Authorization": f"Basic {creds}"}


def post(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(OPENSEARCH + path, data=data, headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None


def get_state():
    """Return (inode, offset) saved by the last run, or (None, 0).

    Older versions saved a bare offset with no inode; that reads as
    (None, offset) and is trusted only if it still fits in the file.
    """
    try:
        txt = open(STATE_FILE).read().strip()
        if ":" in txt:
            ino, off = txt.split(":", 1)
            return int(ino), int(off)
        return None, int(txt)
    except Exception:
        return None, 0


def save_state(inode, offset):
    with open(STATE_FILE, "w") as f:
        f.write(f"{inode}:{offset}")


def sanitize_keys(obj):
    """Rename a nested-object "id" field to "conn_id", recursively.

    Zeek's JSON logs write connection endpoints as a dotted key
    ("id.orig_h", "id.orig_p", ...) for what's conceptually a nested "id"
    object. Wazuh's own JSON decoder already reconstructs this into a
    real nested object (confirmed by inspecting the raw alerts.json:
    "data": {"id": {"orig_h": ..., "orig_p": ..., ...}}) before this
    script ever sees it - so there are no literal dots left to replace by
    the time an alert reaches here. The actual conflict is a field-name
    collision: Wazuh's pre-baked wazuh-template.json already maps
    "data.id" as a plain keyword string (several built-in decoders use a
    simple "id" field that way), so OpenSearch rejects any document where
    the same path is an object instead - confirmed live with
    mapper_parsing_exception, silently for every single Zeek-sourced
    alert (any Zeek log with a conn_id field, not just Modbus) until this
    fix. Renaming just the colliding key avoids the conflict without
    needing to touch Wazuh's own template or Zeek's upstream output.
    """
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            key = "conn_id" if k == "id" and isinstance(v, dict) else k
            out[key] = sanitize_keys(v)
        return out
    if isinstance(obj, list):
        return [sanitize_keys(v) for v in obj]
    return obj


def index_for(alert):
    # Daily index named after the alert's own date, so a backlog indexed
    # after midnight still lands in the right day.
    ts = alert.get("timestamp", "")
    if len(ts) >= 10 and ts[4] == "-" and ts[7] == "-":
        return f"wazuh-alerts-4.x-{ts[:4]}.{ts[5:7]}.{ts[8:10]}"
    return "wazuh-alerts-4.x-" + datetime.now(timezone.utc).strftime("%Y.%m.%d")


def index_batch(alerts):
    bulk = ""
    for a in alerts:
        bulk += json.dumps({"index": {"_index": index_for(a)}}) + "\n"
        bulk += json.dumps(sanitize_keys(a)) + "\n"
    data = bulk.encode()
    req = urllib.request.Request(
        OPENSEARCH + "/_bulk", data=data,
        headers={**HEADERS, "Content-Type": "application/x-ndjson"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
            if r.status not in (200, 201):
                return False
            # A 200 only means the bulk request itself was processed - it
            # says nothing about whether individual documents inside it
            # succeeded. This is exactly how the original mapping-conflict
            # bug went unnoticed: silently dropped, zero-error, offset
            # still advanced. Check each item explicitly.
            resp = json.loads(r.read())
            if resp.get("errors"):
                for item in resp.get("items", []):
                    err = item.get("index", {}).get("error")
                    if err:
                        print(f"[alerts-indexer] index error: {err.get('type')}: {err.get('reason')}", flush=True)
            return True
    except Exception as e:
        print(f"[alerts-indexer] bulk request failed: {e}", flush=True)
        return False


def wait_for_opensearch():
    while True:
        try:
            req = urllib.request.Request(OPENSEARCH + "/_cluster/health", headers=HEADERS)
            with urllib.request.urlopen(req, context=ctx, timeout=5):
                print("[alerts-indexer] OpenSearch ready", flush=True)
                return
        except Exception:
            time.sleep(5)


def drain(f, inode):
    """Index every complete line from f's current position. Returns False
    if OpenSearch rejected a batch (f is left at the last indexed line)."""
    batch, pos = [], f.tell()
    while True:
        line = f.readline()
        if not line:
            break
        if not line.endswith(b"\n"):
            # Partial line still being written - step back and re-read it
            # whole on the next pass.
            f.seek(-len(line), os.SEEK_CUR)
            break
        try:
            batch.append(json.loads(line))
        except json.JSONDecodeError:
            pass
        if len(batch) >= BATCH:
            if not index_batch(batch):
                f.seek(pos)
                return False
            pos = f.tell()
            save_state(inode, pos)
            batch = []
    if batch:
        if not index_batch(batch):
            f.seek(pos)
            return False
        pos = f.tell()
        save_state(inode, pos)
    # Past any undecodable lines too, so they aren't re-read every pass.
    if f.tell() != pos:
        save_state(inode, f.tell())
    return True


wait_for_opensearch()

# wazuh-monitord rotates alerts.json at midnight (UTC in this image): it
# links the day's file into logs/alerts/YYYY/Mon/ and starts a new, empty
# alerts.json with a new inode. The original version of this script kept
# only a byte offset, so after the first midnight it sat past the end of
# the new, smaller file and never indexed another alert - seen live: the
# dashboard showed nothing after 23:59 UTC while the manager kept alerting.
# Track the inode with the offset: when the path points at a new file (or
# the file shrank), finish the old one, then start the new one at 0.
saved_inode, offset = get_state()
f = None
while f is None:
    try:
        f = open(ALERTS_FILE, "rb")
    except FileNotFoundError:
        time.sleep(5)
inode = os.fstat(f.fileno()).st_ino
size = os.fstat(f.fileno()).st_size
if (saved_inode not in (None, inode)) or offset > size:
    offset = 0
f.seek(offset)
print(f"[alerts-indexer] Starting at inode {inode} offset {offset}", flush=True)

while True:
    try:
        ok = drain(f, inode)
        try:
            st = os.stat(ALERTS_FILE)
        except FileNotFoundError:
            st = None
        if ok and st is not None and (st.st_ino != inode or st.st_size < f.tell()):
            # Rotated or truncated. The old handle was drained above, so
            # nothing written before the switch is lost.
            f.close()
            f = open(ALERTS_FILE, "rb")
            inode = os.fstat(f.fileno()).st_ino
            save_state(inode, 0)
            print(f"[alerts-indexer] {ALERTS_FILE} rotated, following inode {inode}", flush=True)
            continue
    except Exception as e:
        print(f"[alerts-indexer] error: {e}", flush=True)
    time.sleep(5)
