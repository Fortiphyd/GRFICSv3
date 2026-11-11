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

### 5.1 Debian bookworm's packaged tcpdump/libpcap silently captures nothing

Produced no error but delivered zero packets for anything, even loopback.
Alpine's build (confirmed via `nicolaka/netshoot`) works correctly. Use
an Alpine-based tcpdump in any container that needs to self-observe
captured traffic; sanity-check with a trivial loopback capture first.

### 5.2 OVS kernel-datapath ports are invisible to tcpdump, even when traffic is really flowing

Known, documented OVS behavior, not a bug - confirmed via interface RX
counters incrementing while tcpdump showed nothing. Not relevant to the
chosen veth design (§3), but don't debug "no packets" on an OVS port
with tcpdump directly if OVS is revisited later.

### 5.3 Two copy-paste bugs from following router/scadalts too literally

`zeek/Dockerfile`'s wazuh-agent used `WAZUH_MANAGER=192.168.90.20` and
`dns: [192.168.90.200]`, both copied from DMZ-attached services - `zeek`
is deliberately admin-network-only (§4.1), so both were unreachable.
Fixed: `WAZUH_MANAGER=wazuh` (hostname), and the unneeded `dns` override
removed.

### 5.4 The ossec.conf injection `sed` duplicates its block when there's more than one `</ossec_config>` in the file

The agent package's `ossec.conf` has two top-level blocks, so a
non-anchored `sed` substitution matches, and duplicates the injected
`<localfile>`, at both. Harmless (Wazuh tolerates double-monitoring a
file) and pre-existing in `router`/`scadalts` too, left alone there; the
new injection in `zeek/Dockerfile` range-addresses the substitution to
avoid carrying the same bug forward.

### 5.5 Agent containers have no persistent state, but the manager's registration database does

Every agent container recreate loses its enrollment key, but the
manager's own persistent volume remembers the old registration and
rejects re-enrollment as a duplicate - this is why `router`/`EWS`/
`scadalts` all showed "Disconnected" despite being registered. Fixed in
`wazuh/Dockerfile`'s manager config: `<auth><force>` to allow replacing a
same-named agent, plus a much shorter `agents_disconnection_time` (30s
vs. the 15m package default) so that's actually usable during normal
development.

### 5.6 Shipping a log to Wazuh only gets it *collected*, not *alerted on*

`logall_json` is off by default, and there's no built-in decoder/rule for
Zeek's JSON structure - collection and alerting are separate pipeline
stages, and getting one working doesn't imply the other. A real rule set
was still needed (§5.12-5.13).

### 5.7 The mirror veth needs `-C` (ignore checksums), or every content-level analyzer is silently blind

veth devices commonly have checksum offloading enabled, which Zeek's
default validation reads as corruption, discarding the packet before any
deeper parsing - `conn.log` still looks completely normal throughout
(basic connection tracking only needs headers), which is what made this
easy to miss. Fixed by adding `-C` to `zeek-start.sh`; inherent to any
veth-based mirror, not specific to Modbus.

### 5.8 Wazuh rootcheck's generic "trojaned binary" heuristic false-positives on Zeek's base image

A decades-old substring-matching signature (`check_trojans`) fired on
`/bin/passwd` and others - specific to Zeek's newer Debian trixie base,
not a lab-wide issue (other containers on older bases don't trip it).
Disabled just that one rootcheck sub-check.

### 5.9 `enable-mirror.sh` didn't survive a container recreate without `disable-mirror.sh` run first

Recreating `zeek` destroys the `mirror0` veth but leaves a stale `clsact`
qdisc on the host's parent interface, which then blocks re-adding it.
Fixed by having `enable-mirror.sh` unconditionally clear any existing
qdisc before setting up fresh state.

### 5.10 A suspected ICSNPP memory leak didn't hold up under a longer, clean test

Packet processing stalled after ~10-15 minutes under turbulent test
conditions (concurrent rebuilds, mirror churn); a subsequent clean
3-hour run showed flat memory and steady throughput throughout. Not
filed upstream - the evidence points at test conditions, not a real leak,
though ICSNPP's `modbus_pending` table genuinely has no expiration
attributes (see §5.14 for its real, smaller effect).

### 5.11 Zeek's `id` field collides with Wazuh's own index schema - alerts generated correctly but never indexed

Wazuh's JSON decoder reconstructs Zeek's dotted `id.orig_h` etc. into a
real nested `data.id` object, but Wazuh's own index template already
maps `data.id` as a plain string - so OpenSearch rejected every such
document with `mapper_parsing_exception`, silently. Affects any Zeek log
with a `conn_id`-shaped `id` field. Fixed by renaming the colliding key
to `data.conn_id` before indexing, and by checking per-item bulk-API
results instead of trusting the overall HTTP status (which reports
"processed," not "succeeded").

### 5.12 With indexing finally working, alert volume itself became the problem - "any write" isn't a usable signal here

Real alerts flowed at ~1000/sec once indexing worked: rule 100100
matched every Modbus event unconditionally, and "alert on writes" fares
no better, since this lab's remote-IO polling issues a write on every
normal cycle - contradicting the near-zero-write assumption the original
Suricata-based tell design (§4.4 of the fault-injection doc) was built
on. Both rules set to level 0 until a real content/rate-based rule
existed (§5.13).

### 5.13 Built both a content-based and a rate-based write rule - plus an undocumented Wazuh correlation mechanic

100102 (any write targeting the PLC itself, zero real baseline) and
100103 (>120 writes/2s to the same destination) both validated against
real traffic/attacks. Getting 100103 working surfaced two non-obvious
Wazuh behaviors: level-0 rules are excluded from `frequency`/
`if_matched_sid` correlation entirely, not just from alert output; and
`<options>no_log</options>` does not suppress alert output despite its
name. The manager's `log_alert_level` floor (default 3) is what actually
gates output, independent of correlation.

### 5.14 The §5.10 modbus_pending gap does have a real effect after all, just not a stall

Unmatched entries eventually flush out individually, long after the
fact, with stale original timestamps - harmless for a content rule like
100102, but a real false-positive source for a timing-sensitive one like
100103. Fixed with a `matched=true` requirement on the base write rule.

### 5.15 Measuring a write-rate baseline needs more care than a single sample

Two wrong attempts (an unrepresentative sample, then one contaminated by
leftover test traffic) before a clean measurement found a genuine ~3x
variance between remote-IO targets; threshold set to clear the worst
one. Separately: the "remote-IO units" are secondary IPs on
`simulation`'s own interface, so a test connecting to them from
`simulation` itself never reaches the mirror - burst tests need a
genuinely separate container.

### 5.16 `zeek` was missing `cap_add: NET_ADMIN` - mirrored packets arrived at the interface but libpcap silently never saw them

libpcap needs `CAP_NET_ADMIN` to set promiscuous mode (required to see
frames whose MACs don't match the interface's own, true of every
mirrored packet) - Docker only grants `CAP_NET_RAW` by default, and
`zeek`'s service definition had no `cap_add` at all, unlike every other
service touching raw networking. The capture "succeeded" with no error
while structurally seeing nothing, which looked like "no traffic right
now" rather than "broken." Fixed by adding the capability.

## 6. Open risks / questions

- ~~A real Modbus-content Wazuh rule~~ — **resolved** (§5.13): both a
  content-based rule (100102, any write to the PLC itself - zero
  measured baseline, validated against the real stuck-valve attack) and
  a rate-based rule (100103, write-rate anomaly per target, validated
  against a real synthetic burst) are built and live, with no false
  positives over multiple clean windows.
- **Per-target thresholds for 100103** (§5.15) - the current single
  threshold (120/2s) is calibrated to the noisiest of the 6 remote-IO
  targets, which means real sensitivity for the other 5 (whose own
  baseline would tolerate a much lower bar) is worse than it could be.
  Would need a separate rule per target rather than one `same_field`-
  grouped rule.
- **Why `192.168.95.13` runs a structurally different write rate than
  the other 5 remote-IO targets** (§5.15) - confirmed real and
  reproducible, not explained. Possibly relevant to the §5.14 finding
  too (that target may also be where stale flushed entries are most
  visible) - not confirmed either way.
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
