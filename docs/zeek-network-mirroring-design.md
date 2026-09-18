# Zeek Network Mirroring — Design Spec

## 1. Purpose

The cyber-injects work (`docs/cyber-vs-physical-fault-injection-design.md`,
§4.4) found something structural, not incidental: Suricata, running on the
router's own macvlan sub-interface, **cannot see traffic between two
containers on the same subnet** (e.g. Kali↔HMI, the beacon/C2 channel for
the stuck-valve pairing). That's not a rule-coverage gap, it's the network
topology — same-subnet macvlan sibling traffic never transits the router's
monitored interface at all.

This doc is about closing that gap: adding a Zeek sensor with real
visibility into *all* lab traffic, including same-subnet sibling traffic,
without changing how the lab is installed or run today (`git clone` +
`docker compose up`). That constraint drove most of the design below —
several architecturally "correct" options were ruled out specifically
because they'd add setup complexity or platform-portability risk, not
because they didn't work technically.

## 2. What didn't work, and why

Each of these was tested against the real stack (or a faithful throwaway
stand-in), not just reasoned about — this project's whole cyber-injects
effort has a habit of finding that "should work" and "does work" are
different things, and this was no exception.

### 2.1 A promiscuous macvlan listener — ruled out, confirmed structural

A third macvlan-attached container, even in promiscuous mode, cannot see
unicast traffic between two *other* macvlan siblings on the same parent.
Confirmed directly: spun up three disposable containers on the DMZ macvlan
network, set one promiscuous, pinged between the other two — the third
container saw the broadcast ARP request (macvlan floods broadcast/
multicast to all siblings) but zero of the unicast traffic. This is the
same mechanism behind the Suricata blind spot in §4.4 of the fault-injection
doc: the Linux macvlan driver forwards by destination-MAC lookup like a real
switch, not a hub — there's no mirroring concept in the driver at all.

### 2.2 Open vSwitch with native mirror ports — technically works, ruled out for setup complexity

OVS mirror ports (`ovs-vsctl ... Mirror ... select-all=true`) genuinely
solve the visibility problem — validated with a real OVS bridge, three
containers wired in via veth, and `ovs-appctl dpctl/dump-flows` /
interface counters confirming a `select_all` mirror correctly duplicates
sibling-to-sibling unicast traffic to a third port. (Getting a *visual*
confirmation via `tcpdump` took a detour — see §5.1.)

Ruled out anyway, for two portability/setup reasons, not a technical
failure:

- Docker has no native OVS network driver. Making it declarative in
  `docker-compose.yml` means depending on old/likely-unmaintained
  community libnetwork plugins, or a manual host-side wiring script that
  has to run *before* `docker compose up` — breaking the one-command
  install.
- Docker Desktop (Mac/Windows) runs containers inside a minimal LinuxKit
  VM. Whether that VM's kernel has the `openvswitch` module built in is
  unverified and a real risk for a lab that needs to "just work" across
  Docker CLI and Docker Desktop.

### 2.3 Per-container ERSPAN/GRE taps — works, ruled out as more machinery than needed

Tunneling each monitored container's traffic to a remote Zeek collector via
`tc mirred ... action mirred egress mirror dev erspanX` (GRE-encapsulated,
the same mechanism real switches use for remote SPAN) is a legitimate,
realistic option — GRE/ERSPAN kernel support was confirmed present in this
environment. Set aside once §2.4 turned up a much simpler local mechanism
that needs no encapsulation at all and no changes baked into every
monitored container's Dockerfile.

### 2.4 tcpdump | tcpreplay streaming — unreliable, wrong tool for the job

An early version of the host-capture script piped `tcpdump -w -` into
`tcpreplay --intf1=... -` to inject captured frames onto a veth. This
silently dropped packets under live testing (a 5-ping test only showed 1
packet arriving). `tcpreplay` is built for replaying a complete, seekable
pcap *file*, not for being fed a live, open-ended stream — it's the wrong
tool even though the idea (replay real captured frames onto a local
interface) was right. Replaced by `tc mirred` (§3), which mirrors packets
in-kernel with no userspace process and no pcap serialization in the loop.

## 3. What works — validated design

**The host's own capture on the macvlan parent NIC sees everything**,
including sibling-to-sibling traffic that no macvlan sub-interface (the
router's, a promiscuous monitor container's, anyone's) can see. Confirmed
directly: `tcpdump -i eth0` from the host's root network namespace (via a
privileged, host-networked container standing in for a root host process)
captured a real ping exchanged between two unrelated macvlan sibling
containers on the DMZ network. Since `b-ics-net` and `c-dmz-net` both use
`parent: eth0` today, one capture point sees both subnets at once — better
unified visibility than Suricata's current per-interface setup even gets.

The validated mechanism to get that traffic into a Zeek container, without
touching Zeek's own `docker-compose.yml` networking at all:

1. Create a veth pair on the host.
2. Move one end into the Zeek container's network namespace (via its PID,
   `ip link set <if> netns <pid>`), rename it (e.g. `mirror0`), bring it up.
   Zeek then just has a normal live interface to capture on
   (`zeek -i mirror0`) — no stdin/pipe tricks.
3. On the host's parent NIC, install `tc mirred` mirror filters (both
   `ingress` and `egress`, needed — `matchall` mirroring in both directions
   was required to see full two-way ICMP exchanges in testing) pointed at
   the host-side veth end.

Validated end-to-end with `matchall` (mirrors everything on the interface):
a 5-ping exchange between two macvlan siblings showed up completely and
correctly — all 5 request/reply pairs, correct sequence numbers, correct
timestamps — on the far end of the veth, inside the stand-in "Zeek"
container's own netns. (First attempt at checking this looked like another
dropped-packet problem — only 1 of 5 packets visible — but that was just
checking the log file too early; the full log had all 10.)

**CIDR-scoped filtering — done, validated.** `matchall` mirrors literally
everything on the physical interface — confirmed via interface counters,
which jumped by 480 packets for a 5-ping test, almost all unrelated
background host/NIC traffic. Replaced with `tc flower` filters matching
`dst_ip` against the lab's two subnets (both `ingress` and `egress`, both
subnets — 4 filters total; matching on destination alone in both
directions was enough to see complete two-way exchanges with zero
duplication, confirmed live). Validated two ways: a clean synthetic 5-ping
+ 1-ping test showed every packet, correctly ordered, no duplicates; and,
unprompted, the filter picked up real background lab traffic (PLC↔remote-IO
Modbus polling) once the real `plc`/`simulation` containers turned out to
already be running — confirming the scoping works on genuine multi-host
traffic, not just a synthetic pair.

### Why this closes the Suricata blind spot specifically — confirmed live, not just in theory

This isn't just "better visibility in general" — it's the direct fix for
the exact gap found in §4.4 of the fault-injection doc, and this was
confirmed directly during implementation, not just argued for: with the
real `zeek` compose service running and mirroring enabled via the real
`enable-mirror.sh` (not a stand-in), Zeek's `conn.log` immediately showed
the actual beacon/C2 channel from the stuck-valve cyber inject —
`192.168.90.107` (HMI) → `192.168.90.6:4444` (Kali's C2 listener) —
recurring every ~5 seconds, exactly matching `beacon_client.py`'s
`--interval 5.0` default. That's a genuine, live beaconing signature,
now visible, that Suricata is structurally blind to (§4.4). The same
capture simultaneously showed PLC↔remote-IO Modbus polling on the ICS-LAN
subnet - one sensor, both subnets, at once, as designed.

## 4. Architecture / implementation surfaces

**Built and validated end-to-end** against the real stack, including a live
capture of the real beacon/C2 channel (§3).

### 4.1 Zeek service (`docker-compose.yml`, `zeek/`)

- New `zeek` service, behind the same `profiles: [siem]` gate as `wazuh` —
  it's useless without a manager to ship logs to, so it doesn't start with
  a plain `docker compose up` either. Joins both `a-grfics-admin` and
  `c-dmz-net` (static `192.168.90.30`) — **revised from the original
  admin-only design.** The admin-only version worked, but reported to
  Wazuh from an admin-bridge IP that didn't look like any other agent in
  the lab; every other agent reports from a real, attributable subnet IP.
  `c-dmz-net` membership is only for that identity - it captures nothing
  and needs no added capabilities either way. Confirmed live: the manager
  sees the agent's actual TCP connection sourced from `192.168.90.30`, not
  the admin network.
- Base image: the official `zeek/zeek:9.0.0` (Debian **trixie**, not
  bookworm) — resolves the open risk below. `zeek/local.zeek` keeps most
  of Zeek's own recommended default policy (asset tracking, software
  version/vulnerability tracking, SQL-injection detection) and adds
  `LogAscii::use_json = T`, the lab's two subnets as `Site::local_nets`,
  and CISA's [ICSNPP](https://github.com/cisagov/ICSNPP) Modbus parser
  (`zeek/cisagov/icsnpp-modbus`, installed via `zkg` in the Dockerfile) -
  without it, Zeek's own base analyzers only cover general IT protocols,
  so Modbus (the lab's only protocol in use today) showed up in `conn.log`
  as opaque TCP connections with no function codes, addresses, or values
  at all. With it, confirmed live against real PLC traffic:
  `modbus_detailed.log` shows real function names
  (`READ_INPUT_REGISTERS`, `WRITE_MULTIPLE_REGISTERS`), register
  addresses, and actual values read/written - genuine content-level
  visibility, not just connection metadata. Only the Modbus parser is
  installed for now, since it's the only ICS protocol this lab actually
  uses; ICSNPP has several others (DNP3, S7comm, ENIP, BACnet, ...) worth
  adding if/when the lab does.
- `zeek/zeek-start.sh`: waits for `mirror0` to exist (polling every 5s)
  before starting `zeek -i mirror0 local`; supervisord's `autorestart`
  handles the rest. **Validated live, including the exact failure mode
  this exists for**: mirroring was disabled (deleting `mirror0`) while
  Zeek was running, then re-enabled — Zeek kept running the whole time and
  picked up traffic on the recreated interface with no restart needed at
  all. Better than the design called for; worth knowing this held on this
  host, though the exact mechanism (why an AF_PACKET capture survives its
  interface being deleted and recreated with the same name) wasn't dug
  into further.
- ~~**Open risk, not yet checked**: does the official Zeek package link
  against a working libpcap on this class of host, or does it inherit the
  exact bug found in §5.1?~~ **Resolved, no.** `zeek/zeek:9.0.0` runs
  Debian trixie, a different libpcap build than bookworm's broken one —
  confirmed working via a live loopback TCP test (a real connection logged
  correctly in `conn.log`) before building anything else on top of it.

### 4.2 `enable-mirror.sh` / `disable-mirror.sh` — built and validated

Run separately from `docker compose up`, by design — deep packet mirroring
is a clearly-labeled, opt-in advanced feature, not part of the default
install path. Requires a native Linux Docker host (WSL2 counts, per all the
testing in this doc) and root/`sudo`; not usable from Docker Desktop's VM.

`enable-mirror.sh`: resolves the zeek container's PID and the macvlan
parent interface/both subnets straight from the existing Docker network
config (`docker network inspect grficsv3_c-dmz-net`/`grficsv3_b-ics-net`) -
zero hardcoded IPs, zero user-supplied config, just `sudo ./enable-mirror.sh`.
Creates the veth pair, wires one end into Zeek's netns as `mirror0`,
installs the `tc flower` filters (§3). Idempotent — no-ops with a message
if already enabled. **Validated by actually running the committed script
file** (not a hand-typed reproduction) via a root-equivalent helper against
the real `zeek` compose service, twice (enable → disable → re-enable), with
the real beacon channel showing up in Zeek's `conn.log` each time.

`disable-mirror.sh`: removes the `tc qdisc` from the parent interface
(takes all its filters with it in one step) and deletes the veth pair.
Graceful no-op if not enabled. Validated the same way - confirmed clean
teardown via `tc qdisc show`/`ip link show` afterward, no residual state
left on the host.

### 4.3 Wazuh log shipping — fully working now: collection *and* alerting

Same pattern as the existing Suricata → Wazuh pipeline
(`router/Dockerfile`'s `<localfile><log_format>json</log_format>...`):
`zeek/Dockerfile` ships `notice.log` and `modbus_detailed.log` (real Modbus
content - function codes, addresses, values, not just connection metadata,
per §4.1/§5.7) as `<localfile>` entries. This section originally stopped at
"collection works, but nothing shows up as a visible alert without a
decoder/rule" (§5.6) - that gap is now closed too: `wazuh/local_rules.xml`
(new file, `COPY`'d into the manager image) adds two rules -

- `100100` (level 3): any `modbus_detailed.log` event, matched purely by
  `<location>` (no decoder needed - Wazuh's JSON auto-parsing already
  exposes every field as `data.<key>`, including dotted keys like
  `id.orig_h` as literal flat field names, not nested objects).
- `100101` (level 7): the same event, but only when `func` contains
  `WRITE` - the actually security-relevant subset - with the description
  interpolating real field values (`$(func)`, `$(id.resp_h)`,
  `$(address)`).

Confirmed live, from a genuinely fresh build (not just a live-patched
running container): real `WRITE_MULTIPLE_REGISTERS` commands from the
PLC's normal remote-IO polling show up in `/var/ossec/logs/alerts/
alerts.log` as `Rule: 100101 (level 7) -> 'Zeek: Modbus write command
(WRITE_MULTIPLE_REGISTERS) to 192.168.95.13, address 1'`.

`conn.log` is still not shipped. That's now genuinely just a volume/scope
decision, not blocked on anything - the decoder/rule question that used to
gate this is resolved. A real frequency/correlation rule for the beacon
signature demonstrated in §3 still doesn't exist - `100100`/`100101` cover
Modbus content, not connection-frequency anomalies on the DMZ side.

## 5. Gotchas found along the way (worth recording so they don't get rediscovered)

### 5.1 Debian bookworm's apt `tcpdump`/`libpcap` silently captures nothing

`apt-get install tcpdump` on `debian:bookworm-slim` (tcpdump 4.99.3,
libpcap 1.10.3) produced a tcpdump that ran without error, set up
capture cleanly, but delivered **zero packets** for anything — not just
OVS-mirrored or veth traffic, but even a trivial same-container loopback
ping (`tcpdump -i lo` while pinging `127.0.0.1`). This looked at first like
a fundamental WSL2/kernel packet-capture limitation and nearly derailed the
whole OVS evaluation (§2.2) before `nicolaka/netshoot`'s tcpdump (libpcap
1.10.6) was tried side-by-side on the identical loopback test and worked
immediately. Root cause not fully isolated (a libpcap build/version issue,
not a kernel or permissions one — confirmed AppArmor isn't even loaded on
this kernel, and confirmed `--privileged` genuinely disables seccomp, so
neither confinement layer was the culprit). Practical fix: don't trust
Debian bookworm's packaged tcpdump/libpcap in this project; Alpine's build
(same family as netshoot's) is confirmed working. Any future container
that needs to actually observe its own captured traffic (not just process
it, the way `modbus_relay.py`'s pymodbus-based capture never had this
problem) should be built accordingly, or at minimum sanity-checked with a
trivial loopback capture test before trusting it.

### 5.2 OVS "system"/kernel-datapath ports are invisible to tcpdump even when working correctly

Separately from §5.1: even with a working tcpdump build, a port that's a
live member of an OVS kernel datapath (`ovs-system`) shows nothing to
`tcpdump` run directly on it, for *any* traffic, mirrored or not — this is
a known, documented OVS behavior (hence the existence of the `ovs-tcpdump`
wrapper script upstream), not a bug. Confirmed via interface RX counters
incrementing correctly while `tcpdump` on the same interface showed
nothing. Not relevant to the chosen design (§3 uses a plain veth, not an
OVS port), but worth remembering if OVS is revisited later — don't debug
"no packets" on an OVS port by reaching for `tcpdump` on that port
directly.

### 5.3 Two copy-paste bugs from following router/scadalts too literally

Both found live, testing against the real `[siem]` profile stack:

- `zeek/Dockerfile` installed the wazuh-agent with the same
  `WAZUH_MANAGER=192.168.90.20` used by `router`/`scadalts`. Those two are
  on `c-dmz-net`, where that static DMZ IP is directly reachable; `zeek`
  deliberately isn't (§4.1) - only `a-grfics-admin`, so that address is
  simply unreachable from it. Confirmed directly (`wazuh` the DNS hostname
  connects, the hardcoded IP times out) and fixed: `WAZUH_MANAGER=wazuh`,
  matching the network zeek is actually on.
- `docker-compose.yml`'s `zeek` service also copied `dns: [192.168.90.200]`
  from the DMZ-attached services (`caldera`, `wazuh`) - same problem,
  unreachable from `a-grfics-admin`, serving no purpose. Removed; Docker's
  own embedded resolver (the default when no override is set) already
  handles `a-grfics-admin` name resolution correctly.

### 5.4 `sed 's|</ossec_config>|...|'` duplicates the injected block when there's more than one `</ossec_config>` in the file

The agent-package `ossec.conf` has more than one top-level
`<ossec_config>...</ossec_config>` block, so a plain (non-anchored) `sed`
substitution matches - and duplicates the injected `<localfile>` - at
*every* occurrence, not just the first. Found live: wazuh-logcollector
logged `WARNING: (1958): Log file '.../notice.log' is duplicated`, and
`grep -c "</ossec_config>"` confirmed 2 occurrences in `zeek`'s
`ossec.conf`. **This is a pre-existing pattern, not something this branch
introduced** - `router/Dockerfile`'s identical `sed` has the exact same
duplicate (confirmed: 2 occurrences there too). Harmless in practice
(Wazuh tolerates monitoring the same file twice, just wastes a little and
logs a warning), so left alone in `router`/`scadalts` as out of scope for
this work, but fixed in `zeek/Dockerfile`'s own new injection using
`sed -i '0,/<\/ossec_config>/{s|...|...|}'` (range-address the
substitution to only the first occurrence) since it's new code with no
reason to carry the same bug forward.

### 5.5 Agent containers have no persistent state, but the manager's registration database does - a structural collision, not specific to Zeek

The real "0 agents reporting" symptom that prompted this whole
investigation. `router`/`EWS`/`scadalts` (and now `zeek`) have no
declared volume for `/var/ossec` - every `docker compose up`/recreate
loses each agent's own enrollment key, forcing a fresh enrollment attempt
on every start. But `wazuh_manager_data` *is* a persistent named volume
(mounted at `/var/ossec` on the manager - the entire agent database lives
there), so the manager still remembers the old registration under the
same name and rejects the new enrollment as a duplicate by default
(`wazuh-authd: WARNING: Duplicate name 'X', rejecting enrollment` /
agent-side `ERROR: Duplicate agent name: X`). This is exactly the
"Wazuh manager stale, 4+ months, config-only verified" situation flagged
in the fault-injection doc - now actually exercised live, and it's why
`router`/`EWS`/`scadalts` all showed "Disconnected" despite being
registered.

Two changes to the manager's `ossec.conf`, both required together, both
now baked into `wazuh/Dockerfile` (confirmed they survive a full
`--force-recreate` of both the `wazuh` and an agent container, and that
agents then auto-reconnect on their own with zero manual steps):

- authd's `<auth><force>` block, which allows replacing a same-named
  agent instead of rejecting it - but only once the manager considers the
  *previous* registration disconnected, which by itself didn't fix
  anything (confirmed: still rejected immediately after adding just this).
- `<global><agents_disconnection_time>`, which controls how long that
  takes - the package default (15m) is reasonable for a real always-on
  deployment, but far slower than how often containers get recreated
  during normal development in this lab. Lowered to 30s.
  `agents_disconnection_alert_time` is already `0` (disabled) in the
  package default, so this doesn't add alert noise, just updates status
  bookkeeping faster.

Immediate unblock for *this* running lab (its `wazuh_manager_data` volume
already existed before these Dockerfile changes, so it needed a live fix
too, not just a rebuild): manually removed the three stale registrations
(`manage_agents -r`) and applied the same two `ossec.conf` changes
directly to the running manager before baking them into the image.

### 5.6 Shipping logs to Wazuh only gets them *collected*, not *alerted on*, without a matching decoder/rule

Once `notice.log` genuinely existed and the agent picked it up
(confirmed: logcollector's "Could not open file" error went away, and a
synthetic test line was written and detected), it still never appeared
anywhere in `/var/ossec/logs/alerts/` on the manager. Root cause: Wazuh's
own `<global><logall_json>` (whether to store *every* collected event,
not just ones that match a rule) is `no` by default, and there's no
built-in Wazuh decoder/rule that recognizes Zeek's JSON log structure the
way there is for Suricata's `eve.json` alerts. Collection (agent → manager
transport) and alerting (manager → visible in the dashboard/API) are two
separate pipeline stages, and this build only confirmed the first one
works. A real Zeek decoder + rule set (or at minimum a rule for
`notice.log`'s structure) is genuinely new work, not a config tweak - see
§6.

### 5.7 The mirror veth needs `-C` (ignore checksums) - without it, every protocol-level analyzer is silently blind, even though `conn.log` looks fine

Found while validating the ICSNPP Modbus parser (§4.1): `zeek -i mirror0`
logged a `Reporter::WARNING` about "likely receiving invalid TCP and UDP
checksums, most likely from NIC checksum offloading" and, without `-C`,
produced **zero** protocol-level output against real, live PLC Modbus
traffic - no `modbus.log`, no `modbus_detailed.log`, nothing. `mirror0` is
a veth (a virtual device, like loopback), and veth devices commonly have
checksum offloading enabled by the kernel the same way loopback does -
Zeek's default checksum validation reads the result as corruption and
discards the packet before any application-layer analysis runs.

The genuinely important part: **`conn.log` looked completely normal the
whole time** (this is how the earlier beacon-channel and PLC-polling
captures in §3/§4.1 looked convincing before this was caught) - because
basic connection tracking only needs packet *headers*, which checksum
validation doesn't gate. Only deeper content parsing does. That means
every content-level script already loaded in `local.zeek` before this fix
- SQL-injection detection, software-version tracking, file hashing, all
of it, not just the new Modbus parser - was silently non-functional the
entire time, with no error visible anywhere except that one easy-to-miss
reporter warning. Fixed by adding `-C` to `zeek-start.sh`'s invocation
(inherent to any veth-based mirror, not a one-off workaround for this
specific test) and confirmed live: real function codes, register
addresses, and values immediately appeared in `modbus_detailed.log`
against genuine PLC↔remote-IO traffic.

### 5.8 rootcheck's generic "trojaned binary" signature check false-positives on Zeek's base image specifically

Wazuh's `rootcheck` module includes a decades-old, generic string-matching
heuristic (`check_trojans`, signature `'bash|file\.h|proc\.h|/dev/ttyo|
/dev/[A-Z]|/dev/[a-s,uvxz]'`) meant to catch classic rootkit-modified
system binaries. It fired on `/bin/passwd`, `/bin/chsh`, `/bin/chfn`, and
others in the Zeek image - all false positives (a fresh official image,
zero chance of real compromise). Confirmed this is specific to Zeek's
base, not a lab-wide issue: `router`/`EWS`/`scadalts`, on older bases,
don't trip it at all, while Zeek's is the only container on Debian
**trixie** - a newer coreutils/glibc build evidently contains incidental
substring matches the legacy signature wasn't designed to distinguish
from a real trojan. Fixed by disabling just that one rootcheck sub-check
(`check_trojans: no`) - files/dev/sys/pids/ports/interfaces checks all
stay on. Worth remembering if a future agent container lands on an even
newer base and starts showing the same "Trojaned version of file"
alerts - it's very likely this same false positive, not a real finding.

### 5.9 `enable-mirror.sh` didn't survive a container recreate without `disable-mirror.sh` run first

Recreating the `zeek` container (e.g. after an image rebuild) destroys its
network namespace, which silently deletes `mirror0`/`mirror0-host` -
removing one end of a veth pair removes both. But it does *not* clean up
the `clsact` qdisc left on the host's parent interface, since qdiscs
aren't tied to the veth's lifecycle. The result: `enable-mirror.sh`'s
idempotency check (`ip link show mirror0-host`) correctly sees nothing and
proceeds, but `tc qdisc add ... clsact` then fails with `Error: Exclusivity
flag on, cannot modify` against the orphaned qdisc - a real failure hit
live while rebuilding zeek for §4.3's changes, not a hypothetical.
Fixed by having `enable-mirror.sh` unconditionally clear any existing
`clsact` qdisc on the parent before setting up fresh state (harmless if
there wasn't one - the `|| true` no-ops cleanly). Confirmed live: recreated
`zeek` without running `disable-mirror.sh` first, then ran `enable-mirror.sh`
directly, and it self-healed with no manual cleanup needed.

### 5.10 A suspected ICSNPP memory leak - investigated, evidence didn't hold up, worth recording so it isn't re-suspected without cause

While validating §4.1/§5.7, Zeek's packet processing stalled completely
after roughly 10-15 minutes of live mirroring (`stats.log`'s `pkts_proc`
dropped from ~18,000/5min to exactly 0, while the interface itself kept
receiving traffic at the kernel level) - a real, observed failure, not
imagined. Code inspection of `icsnpp-modbus/main.zeek` found a real,
verifiable design gap: its `modbus_pending: table[string] of
table[count] of Modbus_Detailed` correlation table has no expiration
attributes at all, and only removes entries on a successful request/
response match - unmatched entries (confirmed present: `"matched":false`
was directly observed in real output) are never cleaned up. For this lab's
long-lived, continuously-polling PLC↔remote-IO connections, that's a
plausible unbounded-growth mechanism, and it was reported to the user as
the likely cause with that reasoning.

It didn't hold up under a longer test. A subsequent 3-hour continuous run
(no mirror churn, no concurrent rebuilds - the conditions the earlier stall
happened under) showed **flat memory (273MB, unchanged) and steady
throughput (~100k packets/5min) the entire time**, with no sign of the
stall recurring. A genuine unconditional table leak should have shown
*some* growth trend over 3 hours; it showed none. The evidence points
instead at the turbulent conditions during the original test - repeated
`enable-mirror.sh`/`disable-mirror.sh` cycles tearing the capture interface
out from under a running Zeek process, concurrent image rebuilds, and
several other test containers competing for host resources, all within a
few minutes - rather than a standing bug in the package.

Left as: not filed upstream (would be reporting a bug no longer believed
to be real), and the `modbus_pending` expiration gap itself is still worth
being aware of as a real, if apparently not load-bearing, design gap in a
third-party package - just not confirmed to cause a practical problem
under normal (non-churning) operation.

### 5.11 Zeek's `id` field collides with Wazuh's own schema - alerts were generated correctly but silently never indexed, for a long time

After §4.3/§5.6 appeared to be fully working (real alerts confirmed in
`alerts.log`), the user still reported seeing nothing in the actual Wazuh
dashboard. The full pipeline turned out to have a third, independent
failure stage beyond collection and alerting: **indexing**.
`/usr/local/bin/alerts-indexer.py` (this project's own lightweight
Filebeat replacement - see its own docstring) tails `alerts.json` and
bulk-indexes into OpenSearch, but only checked the *overall* HTTP status
of each bulk request (200/201), never each item's individual result -
which is exactly how this went unnoticed. OpenSearch's bulk API returns
200 for a request that was *processed*, independent of whether individual
documents inside it succeeded.

Root cause, confirmed by inspecting the raw `alerts.json` structure
directly: Wazuh's own JSON decoder reconstructs Zeek's dotted
`"id.orig_h"`/`"id.orig_p"`/etc. keys into a real nested object -
`"data": {"id": {"orig_h": ..., "orig_p": ..., ...}}` - before the alert
is ever written to `alerts.json`. But Wazuh's pre-baked
`wazuh-template.json` already maps `data.id` as a plain `keyword` string
(several built-in decoders use a simple string "id" field that way), so
OpenSearch's dynamic mapper rejects every document where that same path
is an object instead, with `mapper_parsing_exception`. This affects *any*
Zeek log with a `conn_id`-shaped `id` field (which is nearly all of
them - `conn.log`, `notice.log`, `modbus_detailed.log`), not just Modbus.

Confirmed as the real cause by testing both wrong and right hypotheses
directly against the live index rather than guessing:
- First attempt: assumed the literal dots in Zeek's *raw* key names were
  the problem and tried replacing `.` with `_` in a general JSON-key
  sanitizer. Redeployed, same error - because by the time this script
  sees the alert, there are no dots left; Wazuh already expanded them
  into a real nested object.
- Second attempt, verified against the actual raw JSON: renaming the
  specific colliding field - `data.id` (when it's an object, not the
  unrelated top-level alert `id` or `agent.id`, both plain strings) to
  `data.conn_id` - tested directly via a manual `_bulk` call first
  (`"errors":false`), *then* deployed. Confirmed live: `wazuh-alerts-*`
  document count went from 2,157 (stuck, despite 111,000+ matching lines
  already in `alerts.log`) to growing continuously within seconds of the
  fix landing, with zero new mapping errors.

Also fixed alongside, since it's what let this go unnoticed for as long
as it did: `index_batch()` now parses the bulk response body and logs
each item's individual error (previously: completely silent, and the
read offset still advanced past the failed documents regardless, so they
were gone for good, not just delayed).

## 6. Open risks / questions

- ~~CIDR-scoped `tc flower` filtering~~ — **resolved, validated live**
  (§3, §4.2).
- ~~Zeek's own supervision strategy for a mirror interface that can appear/
  disappear at runtime~~ — **turned out not to need one.** Zeek survived a
  disable/re-enable cycle with no restart and no dropped visibility,
  confirmed live (§4.1). Worth re-checking if this is ever deployed on a
  meaningfully different host/kernel, since the exact mechanism isn't
  understood, just the outcome.
- ~~Whether the official Zeek package inherits the §5.1 libpcap bug~~ —
  **resolved, no** (§4.1).
- ~~Live Wazuh ingestion of `notice.log`~~ — **partially resolved.**
  Collection works end-to-end (agent connects, ships, manager receives) -
  confirmed live, along with two real bugs along the way (§5.3, §5.4). What
  doesn't exist yet: a Wazuh decoder/rule that turns collected Zeek events
  into visible alerts (§5.6) - genuinely new work, not a config fix.
- ~~"0 agents reporting" / agent enrollment~~ — **resolved.** Root cause
  was structural (§5.5), not Zeek-specific - fixed for `router`/`EWS`/
  `scadalts`/`zeek` all at once via two `wazuh/Dockerfile` changes, and
  confirmed to survive a full recreate of both the manager and an agent
  container with zero manual steps needed afterward.
- ~~A Zeek decoder + rule set for Wazuh~~ — **resolved** (§4.3, §5.6):
  `wazuh/local_rules.xml` turns `modbus_detailed.log` events into visible
  alerts, including a dedicated higher-severity rule for write commands
  specifically. What's still open: a *frequency/correlation* rule for the
  beacon signature demonstrated in §3 (connection-pattern anomaly, not
  Modbus content) - the current rules cover ICS content, not that.
- ~~Alerts generated correctly but never reaching the dashboard~~ —
  **resolved** (§5.11): a field-name collision between Zeek's `id` (a
  nested conn_id object once Wazuh's own decoder reconstructs it) and
  Wazuh's pre-baked template (`data.id` mapped as a plain keyword) was
  silently dropping every Zeek-sourced alert at the indexing stage - the
  one pipeline stage after collection (§4.3) and rule-matching (§5.6)
  that hadn't been checked yet. `alerts-indexer.py` now renames the
  colliding field and logs indexing errors instead of swallowing them.
- ~~Zeek reporting from an admin-bridge IP instead of a real subnet IP~~ —
  **resolved** (§4.1): `zeek` now joins `c-dmz-net` too (`192.168.90.30`),
  matching every other agent's convention.
- ~~OT protocol parsing (ICSNPP)~~ — **resolved for Modbus** (§4.1). Other
  ICSNPP parsers (DNP3, S7comm, ENIP, BACnet, ...) not installed - nothing
  in this lab uses those protocols today.
- ~~Every protocol-level analyzer silently non-functional against real
  mirrored traffic~~ — **resolved** (§5.7): `-C` was missing from the
  Zeek invocation. This was serious enough that it's worth flagging
  explicitly even though it's also listed as resolved - anyone modifying
  `zeek-start.sh` later should know why `-C` is there before removing it.
- ~~`enable-mirror.sh` not surviving a container recreate~~ — **resolved**
  (§5.9): it now clears any stale `clsact` qdisc unconditionally before
  setting up fresh state.
- A suspected ICSNPP memory leak - investigated, initial evidence didn't
  hold up under a longer test (§5.10). Not filed upstream. Worth
  re-examining only if the stall is actually seen again under normal
  (non-churning) operation - not assumed to still be a live risk.
- How much of `conn.log` (if any) to ship to Wazuh alongside `notice.log`/
  `modbus_detailed.log` - a genuine scope/volume decision now, not blocked
  on anything (§4.3).
- No dashboard/runtime control for any of this — `enable-mirror.sh`/
  `disable-mirror.sh` are deliberately separate, manual, host-level scripts
  for now, consistent with keeping this feature out of the default install
  path (§4.2).
