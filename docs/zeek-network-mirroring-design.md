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

**Not yet validated**: CIDR-scoped filtering. `matchall` mirrors literally
everything on the physical interface — confirmed via interface counters,
which jumped by 480 packets for a 5-ping test, almost all unrelated
background host/NIC traffic. The real script needs `tc flower` filters
matching the lab's actual subnets (`192.168.90.0/24`, `192.168.95.0/24`,
both as source and destination, both directions) instead of `matchall`, so
Zeek only ever sees lab traffic. This is a standard, well-understood tc
capability, but hasn't been tested with the real flower syntax yet — treat
as the next concrete implementation step, not a settled fact.

### Why this closes the Suricata blind spot specifically

This isn't just "better visibility in general" — it's the direct fix for
the exact gap found in §4.4 of the fault-injection doc. The beacon/C2
channel between Kali and HMI is same-subnet macvlan traffic, which is
precisely the category this mechanism captures (it's parent-NIC-level, not
macvlan-sub-interface-level). Once built, Zeek would have a real shot at
beaconing detection (periodic outbound check-ins with regular timing/size)
for that scenario — the thing §4.4 flagged as needing "a different sensor"
than Suricata.

## 4. Architecture / implementation surfaces

**Not yet built** — this section describes the design to implement, not
completed work.

### 4.1 Zeek service (`docker-compose.yml`)

- New `zeek` service, completely standard Docker networking — joins
  `a-grfics-admin` only (to reach Wazuh for log shipping), *not*
  `b-ics-net`/`c-dmz-net`, and no `network_mode: host`. It gets its traffic
  from the mirror veth, not from network membership.
- Needs a wrapper/entrypoint that tolerates `mirror0` not existing (the
  default state — mirroring is opt-in) and existing/disappearing at
  arbitrary times (`disable-mirror.sh` deletes the veth pair, which removes
  `mirror0` out from under a running Zeek process). Exact supervision
  strategy — retry loop, restart on interface loss — still to be designed.
- **Open risk, not yet checked**: does the official Zeek package (Debian/
  Ubuntu-based, per zeek.org's own repos) link against a working libpcap on
  this class of host, or does it inherit the exact bug found in §5.1? Needs
  testing against a real Zeek build before assuming it's fine — this bit
  us once already in this exact investigation.

### 4.2 `enable-mirror.sh` / `disable-mirror.sh`

Run separately from `docker compose up`, by design — deep packet mirroring
becomes a clearly-labeled, opt-in advanced feature, not part of the default
install path. Requires a native Linux Docker host (WSL2 counts, per all the
testing in this doc) and root/`sudo`; not usable from Docker Desktop's VM.

`enable-mirror.sh`:
1. Resolve the Zeek container's PID (`docker inspect -f '{{.State.Pid}}' zeek`).
2. Resolve the macvlan parent interface automatically from the existing
   network config (`docker network inspect grficsv3_c-dmz-net`) rather than
   asking the user to re-specify it — it's already the same value set once
   in `docker-compose.yml`'s `driver_opts.parent`. Keeps the script itself
   zero-configuration: `sudo ./enable-mirror.sh` and nothing else.
3. Create the veth pair, wire one end into Zeek's netns as `mirror0`.
4. Install the `tc mirred` filters on the parent interface (§3).
5. Idempotent — detect and no-op (with a message) if already enabled,
   rather than erroring or double-installing filters.

`disable-mirror.sh`: remove the `tc qdisc` from the parent interface (this
takes all its filters with it in one operation) and delete the veth pair.
Graceful no-op if not currently enabled.

### 4.3 Wazuh log shipping

Same pattern as the existing Suricata → Wazuh pipeline
(`router/Dockerfile`'s `<localfile><log_format>json</log_format>...`):

- Configure Zeek for JSON logs (`redef LogAscii::use_json = T;` or the
  equivalent policy load) instead of its default TSV.
- Install a wazuh-agent in the Zeek container (matching `scadalts/
  Dockerfile`'s pattern), reporting to `192.168.90.20`.
- Ship `notice.log` first — Zeek's own anomaly/notice framework, the
  closest equivalent to Suricata's `alerts.json`. `conn.log` (full
  connection summaries) is useful supplementary context for future
  correlation rules but high-volume; whether to ship it too, and how much
  of it, is an open question rather than a default-yes.

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

## 6. Open risks / questions

- CIDR-scoped `tc flower` filtering — designed, not yet tested (§3).
- Zeek's own supervision strategy for a mirror interface that can appear/
  disappear at runtime — not designed yet (§4.1).
- Whether the official Zeek package inherits the §5.1 libpcap bug — not
  checked.
- How much of `conn.log` (if any) to ship to Wazuh alongside `notice.log` —
  not decided (§4.3).
- No dashboard/runtime control for any of this — `enable-mirror.sh`/
  `disable-mirror.sh` are deliberately separate, manual, host-level scripts
  for now, consistent with keeping this feature out of the default install
  path (§4.2).
