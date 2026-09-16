# Cyber vs. Physical Fault Injection — Design Spec

## 1. Purpose

GRFICSv3 already supports instructor-controlled physical fault injection (valve
and sensor faults — see `feature/fault-injection`, merged to `main`). This
document scopes the next phase: pairing each physical fault with a
symptom-alike **cyber** attack, so instructors can run "was this cyber or
physical?" diagnostic exercises — the core training gap behind the premise
that OT teams over-index on assuming cyber whenever a physical anomaly occurs,
when confirmed OT cyberattacks are statistically rare.

This spec also covers a **noise floor** mechanism for seeding realistic
ambient distractor activity, and a proposed session flow for running this as
either a training exercise or a data-gathering study.

Not covered here: the actual build (Kali MITM script, EWS/ARP automation
scripts, Fault Injection page UI changes). This is the design to build
against, not the implementation.

## 2. Existing physical fault infrastructure (recap)

Already built and merged. All fault logic lives in the C++ physics engine
(`simulation/simulation/TE_process.cc`); the Modbus device scripts
(`simulation/simulation/remote_io/modbus/*.py`) are deliberately
fault-unaware — they only ever read a `measured` value the engine computes
from a `true` value, and never see fault state directly. This
true/measured split is the pattern the cyber side departs from (see §3).

- **Valve faults** (`f1`, `f2`, `purge`, `product`): stuck (frozen position,
  ignores setpoint *and* e-stop), sluggish (slew-rate limited, configurable
  stroke time), fouled (reduced max Cv).
- **Sensor faults** (tank pressure, tank level, 4 flows, analyzer A/B/C):
  one unified `{mode, severity}` pair per sensor. Modes: none / frozen /
  drift / noise / dropout.

## 3. Network topology constraint on cyber injects

```
eth1 (ICS/LAN, macvlan, 192.168.95.0/24): PLC .2, simulation/remote-IO .10-.15,
                                           EWS .5, router .200
eth2 (DMZ/WAN, macvlan, 192.168.90.0/24): HMI .107, Kali .6, Caldera .250,
                                           Wazuh .20, router .200
```

Kali (attacker workstation) shares an L2 segment only with the DMZ devices —
notably the HMI, not the PLC or remote-IO. ARP spoofing only works within a
shared L2 segment, so **Kali's only real MITM position is between the HMI and
its gateway**, intercepting whatever the HMI sends or receives across the
router (i.e. HMI ↔ PLC traffic). It has no path to PLC ↔ remote-IO
traffic, which stays entirely within the ICS segment.

This splits cyber injects into two shapes:

- **Read-path (PLC → HMI)**: values the HMI polls from the PLC. Kali can
  freeze/rewrite these in flight, but **the PLC's own control loop never sees
  the tampering** — it's still acting on real data via its own link to
  remote-IO. Only the human operator's display is corrupted.
- **Write-path (HMI → PLC)**: an operator-issued command. Kali can
  intercept and replace this, and here it *does* reach the real world — the
  PLC has no way to know the command didn't genuinely come from the HMI, and
  executes it.

This is also where the primary diagnostic "tell" comes from for the three
read-path attacks: **does the PLC's own actual behavior (checkable via the
EWS, or by observing real valve/flow behavior) agree with what the HMI
displays?** A physical field-device fault corrupts data at the source, so the
PLC and HMI are fooled identically and agree with each other (both wrong,
together). A read-path cyber attack only corrupts the HMI's view, so the PLC
and HMI *disagree*.

## 4. Cyber injects — four pairings

### 4.1 Sensor freeze (cyber) — implemented and validated end-to-end

- **Mechanism**: Kali ARP-spoofs the HMI's gateway, intercepts PLC→HMI
  responses for a given tag, captures one legitimate response, and replays it
  on a loop instead of forwarding fresh data.
- **Implementation**: `attacker/cyber_injects/modbus_relay.py` - continuously
  polls the real target and re-serves it on its own Modbus TCP port, with
  frozen mode caching the first reading. An `iptables` PREROUTING REDIRECT
  rule on Kali (port 502 → the relay's listen port) makes the ARP-spoofed
  traffic actually terminate at the relay instead of merely flowing through.
  Verified against real running containers: HMI, using its completely normal
  connection to the PLC's real IP, received the frozen value, while a direct
  read from the ICS side (the simulation container) showed the true,
  still-changing value at the same moment - the PLC-vs-HMI disagreement tell
  below, demonstrated live, not just designed on paper. Noise and dropout
  (§4.2, §4.3) and drift (bonus, see below) are implemented in the same
  script and validated the same way - direct relay logic plus one full
  ARP-spoof+redirect chain test each.
- **Symptom**: HMI shows a static reading; PLC's own behavior keeps tracking
  the real, still-changing process.
- **Tell**: PLC-vs-HMI disagreement (§3). Bonus forensic tell: a packet
  capture shows byte-for-byte identical payloads across multiple poll
  cycles — real traffic always has minor variation (timestamps, sequence
  counters); an exact repeat is a replay signature.
- **Distractor**: put the physical process into genuine near-equilibrium
  (balanced feed/purge/product) before the exercise starts, so an unrelated
  tag is also naturally flat for real, non-malicious reasons. Forces
  participants to check whether the *driving inputs* for a flat tag are also
  static (real equilibrium) or still changing while the readout never budges
  (fake).

### 4.2 Sensor noise (cyber) — implemented and validated

- **Mechanism**: same MITM position; Kali adds randomized jitter to each
  intercepted read-path value before forwarding it. PLC's control loop still
  runs on the true, smooth value. Same `modbus_relay.py` as 4.1 (`--mode 3
  --severity <amplitude>`) - verified the reported value stays within
  ±amplitude of the true value, varies unpredictably in both directions, and
  shows no accumulating bias (unlike drift, below).
- **Symptom**: HMI trend looks erratic; PLC-driven behavior (valve movement,
  downstream flows) stays smooth.
- **Tell**: PLC-vs-HMI disagreement, plus a statistical tell — naive
  attacker-injected noise (e.g. uniform random) doesn't resemble real
  instrument noise, which is typically small, quantized to the register's
  actual resolution, and often correlated between samples rather than
  independent every poll.
- **Distractor**: reuse the *existing physical noise fault*, at low severity,
  on a genuinely different, historically-steady tag — established as "this
  one's always been a little noisy" well before the real event. Forces
  comparison against that specific tag's own history rather than
  pattern-matching on "is anything noisy right now."

### 4.3 Sensor dropout (cyber) — implemented and validated, mechanism revised

- **Mechanism** (revised from the original "drops or RSTs the session" plan):
  same MITM position; on a fixed duty cycle (10s period, matching the
  physical dropout fault), Kali substitutes `0` for the real value instead of
  forwarding it - the TCP connection itself stays up throughout, both on the
  HMI↔relay side and the relay↔PLC side. Deliberately *not* an actual
  connection drop: breaking the TCP session would look like an obvious
  network problem (an error, not a plausible reading), which would make this
  *easier* to distinguish from the physical dropout fault, undermining the
  whole point of a symptom-alike pairing. Serving `0` on a live connection is
  exactly what the physical dropout fault already does (a NAMUR NE43-style
  fail-low reading), so the two are indistinguishable at the HMI. Verified:
  reported value cycles between `0` and the true value on the expected
  cadence while the underlying connections never drop.
- **Symptom**: HMI periodically shows a stale/error/zero reading.
- **Tell**: a genuine field-device comms failure would *also* raise a
  loss-of-comms alarm at the PLC's own diagnostics level, since the PLC
  really did lose contact with that device. A pure HMI-channel disruption
  raises no such PLC-side alarm — the PLC's own link was never touched.
  "Does the PLC itself think it lost that device" is concrete, checkable
  proof.
- **Distractor**: hand out a piece of context during briefing — a note that
  network maintenance is scheduled for a certain window. Tests whether
  participants accept a plausible cover story at face value or verify it
  against an actual documented change record and check whether the timing
  and behavior genuinely match it.

### 4.4 Stuck valve (cyber) — compromised-HMI model via beacon/C2, implemented and validated end-to-end

**Revised from the original MITM-based plan.** The original design had Kali
intercepting an HMI→PLC write in flight. The current version instead assumes
the HMI itself is compromised (a CrashOverride/Industroyer-style model: the
attacker either drops their own tool or leverages whatever's already on the
host) and issues the write directly, using HMI's own real identity — no
interception needed. This is both more realistic (real OT incidents
overwhelmingly start with a compromised engineering workstation or HMI, not
L2 MITM) and, deliberately, harder to catch: a write from a genuinely
compromised HMI is indistinguishable on the wire from a legitimate operator
action. That last point drove a real change in the tell (below) - the
original "check the local audit log" design doesn't survive this revision,
since a sufficiently capable host compromise could tamper with that same
local log.

- **Mechanism**: a script running on the HMI host issues the write directly
  to the PLC. Uses the existing OpenPLC "manual mode" mechanism (already in
  `plc/st_files/326339.st`): a coil (`manual_mode`, `%QX0.0` → Modbus coil
  0) that, when set, makes the ladder logic use fixed manual setpoints
  (`%QW10-13` → holding registers 10-13, one per valve) instead of its own
  closed-loop control.
- **Implementation**: `attacker/cyber_injects/setpoint_inject.py` (usable
  directly, e.g. from Kali, for a simpler MITM-free demo of the same
  mechanism) plus a raw-socket equivalent for the "runs on HMI itself"
  version - HMI is a Java/Mango-derived app (ScadaLTS) with no `pymodbus`
  available, so the validated compromised-HMI test used nothing but
  Python's stdlib `socket` module, which is itself a better match for
  "leveraging what's already there" than dropping a new dependency would
  have been. Verified against the real running PLC, executed from *inside*
  HMI's own container: with f1's valve fully open (input register 100 =
  65535) under normal automatic control, writing coil 0 = `true` closed the
  valve completely within about a second, zero operator action. Disabling
  manual mode immediately handed control back. Also confirmed this is
  genuinely "stuck," not just a one-off move: while manual mode stays set,
  the ladder logic's `IF manual_mode THEN ... ELSE` means *no* normal
  operator adjustment does anything until manual mode is turned back off.
- **Delivery mechanism — beacon/C2, not SSH-in, implemented and validated
  end-to-end.** Considered having Kali actively SSH into HMI to run the
  write (simpler, and still more realistic than the earlier MITM plan), but
  settled on a persistent outbound-beaconing implant instead:
  `scadalts/cyber_injects/beacon_client.py` runs continuously on HMI from
  container start (wired into `scadalts/supervisord.conf`, matching how
  every other daemon in that container is managed), periodically checking
  in with `attacker/cyber_injects/c2_listener.py` on Kali (wired into
  `attacker/supervisord.conf` the same way) over a small JSON-over-TCP
  protocol, and executing whatever command is queued there (reusing the
  same raw-socket `write_coil`/`write_register` logic already validated in
  `setpoint_inject.py`). This is a better match for how real ICS malware
  actually persists and gets commanded (Stuxnet, TRITON, and most real APT
  tooling beacon outbound rather than requiring the attacker to hold
  working inbound credentials - egress filtering is far less commonly
  enforced than ingress filtering, including in real OT networks).
  Verified against the real running stack: queuing a command by writing
  `{"action": "write_coil", "address": 0, "value": true}` to
  `/tmp/c2_pending_command.json` on Kali (no restart of anything needed),
  the implant picked it up on its next check-in (~5s later), executed the
  real Modbus write, and the real valve closed - confirmed both via the
  beacon's own log (`[beacon] received command ... executed, response:
  00010000000601050000ff00`) and by reading the valve's true position
  before and after. Disabling manual mode the same way restored normal
  control immediately.
- **Can Suricata see the beacon traffic? No - confirmed, not just
  suspected.** Kali and HMI are both on the DMZ segment, and same-subnet
  macvlan traffic between them never transits the router's monitored eth2
  interface at all, so Suricata structurally cannot see the beacon
  check-ins no matter what rule exists. This matters architecturally: it
  means the write-frequency tell (below) isn't just *one* detection
  surface for this scenario, it's the *only* network-level one - the
  compromise's C2 channel itself is invisible to the current IDS
  placement, by construction, not by a gap in rule coverage. If beaconing
  detection specifically is wanted as a teachable moment later (a
  genuinely valuable, distinct skill from what this pairing currently
  teaches), it would need a different sensor: HMI already has a
  configured Wazuh agent (`scadalts/Dockerfile` installs one reporting to
  the manager at `192.168.90.20`), and host-based telemetry doesn't care
  about network segments the way a network IDS does - that's the natural
  next place to look, not more Suricata rules.
- **Symptom**: operator sees a valve at an unexpected position with no memory
  of commanding it there.
- **Tell — revised to a frequency anomaly in Wazuh, not a content or source
  check.** No Suricata rule can reliably distinguish a legitimate write from
  a compromised-HMI write - same source IP, same protocol, same everything.
  So `router/grfics_cyber_injects.rules` (sid `9000001`) doesn't try: it
  logs *every* Modbus write, unconditionally, regardless of source or
  target address. The actual tell is the write *rate* Wazuh sees, ingesting
  these via Suricata's existing `alerts.json` → wazuh-agent pipeline:
  baseline is near-zero (confirmed: 0 alerts over a 30s idle window, since
  ScadaLTS's default seed config doesn't do any writes on its own), while a
  burst of repeated writes (e.g. malware re-asserting control, matching a
  real pattern from actual ICS malware) produces a sharp, checkable spike -
  confirmed 1:1: 10 writes issued, 10 alerts logged, no noise, no false
  negatives. A locked-down deployment should still restrict the ICS segment
  to just the HMI's IP (recommended in the prior revision of this section),
  but that's now more about good network hygiene than about this specific
  tell, since the whole point of the compromised-HMI model is that the
  traffic looks legitimate regardless of firewall posture.
- **Distractor**: a legitimate but unusual *burst* of writes that isn't an
  attack - e.g. an engineer doing a batch of setpoint tuning across several
  *different* valves during a documented commissioning/maintenance window.
  Forces participants to look past raw count alone: a real tuning session
  produces a scattered set of distinct, once-each adjustments across
  different tags, while malware re-asserting control looks like rapid,
  repeated writes to the *same* coil/register - the shape of the burst
  matters, not just that a burst happened.
- **Notable finding along the way**: the pre-existing Quickdraw rule most
  obviously suited to this ("Unauthorized Write Request to a PLC",
  sid `1111007`) never actually fires for *any* traffic in this lab -
  `MODBUS_CLIENT`/`MODBUS_SERVER` are both defined as `$HOME_NET`, which
  covers the entire lab, so its "not a recognized client" condition can
  never be true internally. This was true before this revision too (it
  wouldn't have fired for the original Kali-direct version either) - it's
  a pre-existing gap, not something this revision introduced. Also found,
  as a byproduct of testing rule-loading: `quickdraw.rules` has 17
  pre-existing parse errors on this Suricata version (7.0.10) - undefined
  rule-vars for BACnet/Modicon/FINS/S7, duplicate SIDs, and PCRE syntax
  Suricata 7 rejects - meaning several vendored protections for other
  protocols likely aren't loading at all. Worth a separate investigation;
  out of scope for this change.

### Bonus: drift mode exists but isn't one of the four scoped pairings

`modbus_relay.py` implements a fourth mode (`--mode 2`, drift) mirroring
`TE_process.cc`'s `SENSOR_FAULT_DRIFT`, since it came for free from sharing
one `FaultState` class across all modes. It's validated the same way as
noise/dropout (steadily growing gap between true and reported values,
confirmed both directly and through the full ARP-spoof+redirect chain), but
there's no cyber-drift pairing in the four scoped in §4 - the physical drift
fault doesn't currently have a cyber counterpart in this plan. Worth keeping
in mind as a fifth pairing option later, or as one more type of event for the
noise floor (§5), rather than scoping new work around it now.

### Cross-cutting distractor (applies to any/all of the above)

A genuinely benign ARP event (a legitimate device reconnecting, an
engineer's laptop rejoining) near the attack's own ARP-spoofing activity —
defeats the "I saw ARP weirdness, therefore cyber" shortcut across all four,
forcing participants to look at *what* changed (a known device vs. a
genuinely anomalous MAC/IP pairing), not just *whether* anything changed.

## 5. Noise floor

**Terminology**: "noise floor" (signal-processing framing — the ambient
level a real signal must be detected against) or "noise injects" (the
HSEEP/MSEL tabletop-exercise-design term for deliberately irrelevant
scripted events mixed in with the real ones, to test whether participants
can filter signal from noise). Either is better than "background noise."

**Concept**: rather than hand-scripting each distractor into a specific
phase, run a single seeded, randomized scheduler that continuously fires a
mix of minor ambient events throughout the *entire* session — both
familiarization and the event window. Because it never stops, a coincidental
ambient blip near the real event isn't suspicious timing anymore, it's just
the environment's normal texture. This is a structural improvement over
phase-scripted distractors, not just a simplification.

**Content** (deliberately populated with events that specifically undermine
each pairing's tell from §4, not just generic noise):

| Ambient event | Reuses | New work needed |
|---|---|---|
| Minor sensor noise, random tag | existing physical noise fault, low severity | none |
| Occasional dropout, random tag | existing physical dropout fault, low severity | none |
| Occasional valve stickiness | existing physical stuck-valve fault, brief | none |
| Minor EWS setpoint nudges | EWS's normal control path | small script: periodic, legitimately-logged small setpoint changes |
| Benign ARP churn | — | small script: simulate a legitimate device reconnect/lease-renewal |

So of the five ambient event types, three are pure reuse of what's already
built (a scheduler wrapping existing fault controls), and only two need new
automation.

**Design details**:

- **Seeded PRNG**: the exact sequence and timing of ambient events should be
  reproducible via a shared seed, so every participant (or every participant
  in a given condition) experiences the identical ambient pattern. Removes
  "luck of the draw" as a confound between trials — the seed governs ambient
  scheduling independently of the real event, which the instructor triggers
  separately per participant/condition.
- **Quiet buffer**: suppress the noise-floor generator for a short window
  (e.g. ±60s) around the real event's trigger time. Otherwise the
  seed could occasionally land an ambient blip on top of the real event by
  pure chance — not "harder," just an unfair coin flip for whoever gets that
  alignment.
- **Transient vs. persistent as a distinguishing axis**: ambient blips
  (especially the stuck-valve and dropout ones, since those are also real
  test conditions) should self-resolve after a few seconds. The real
  injected fault holds and ideally escalates. This is a deliberate design
  choice, not an afterthought — it teaches "don't declare an incident on the
  first blip, watch whether it persists," a genuinely useful skill distinct
  from pure pattern-matching.
- **Density as a difficulty knob**: mean time between ambient events is a
  natural, continuous independent variable. Rather than a binary "distractor
  present / absent," sessions could vary noise-floor density and plot
  accuracy/speed against it — a stronger, more quantifiable result for the
  talk than a flat two-condition comparison.

## 6. Session flow

Target: ~45-60 minutes total per participant.

| Phase | Duration | Content |
|---|---|---|
| 0. Briefing | ~5 min | Role, available tools (Wazuh, Suricata, ScadaLTS, EWS), what "done" looks like (stated conclusion + confidence + cited evidence). Do **not** disclose that scenarios are deliberately ambiguous or that distractors exist. |
| 1. Familiarization | ~15-20 min | Environment is live under normal control; noise floor already running. This is where *ambient* distractor elements are established as baseline: near-equilibrium state, the historically-noisy tag, the maintenance-window note, one benign operator action observed. Also separates "do they know these tools" from "can they diagnose the ambiguity." |
| 2. Event window | timed (core metric) | Real fault/attack triggered. Noise floor continues (minus quiet buffer). Episodic distractor patterns (second legitimate setpoint change, second benign ARP event) recur here too, reinforcing they're a stable feature of the environment. |
| 3. Decision | ~5 min | Participant states cyber/physical, confidence, and specific evidence. Score against a rubric (did they check PLC-vs-HMI agreement? Wazuh's write-frequency alerts? IDS/ARP?) for richer data than right/wrong alone. |
| 4. Debrief | ~10-15 min | Reveal ground truth; gather qualitative feedback (did the distractor feel fair, how confident vs. how accurate were they) — useful material for the talk beyond raw numbers. |

**Structural decision**: given recruiting real OT SOC analysts is the binding
constraint (not engineering effort), run this as a **between-subjects**
design — each participant experiences exactly one condition (one fault,
cyber or physical, with or without its distractor), not multiple. Trades a
larger required N for a much smaller per-participant time ask, which matters
more than statistical elegance when recruitment itself is the bottleneck.

## 7. Implementation surfaces

- ~~Kali: one parameterized MITM script...~~ **done**:
  `attacker/cyber_injects/modbus_relay.py` (read-path: frozen/drift/noise/
  dropout) and `attacker/cyber_injects/setpoint_inject.py` (write-path:
  stuck valve, MITM-free demo version) — two scripts rather than one, since
  the read-path relay and the write-path injection turned out to need
  genuinely different mechanisms (intercept-and-reserve vs. a direct
  unauthenticated write), not just different modes of the same tool. Both
  baked into `attacker/Dockerfile` via `COPY cyber_injects /opt/cyber_injects`.
- ~~Written, not yet live-validated~~ **done, validated** (§4.4):
  `attacker/cyber_injects/c2_listener.py` (Kali, always-on via
  `attacker/supervisord.conf`) and `scadalts/cyber_injects/beacon_client.py`
  (HMI, always-on via `scadalts/supervisord.conf`) — the beacon/C2 delivery
  mechanism for the stuck-valve pairing's compromised-HMI model. Both baked
  into their respective Dockerfiles.
- None of the above has runtime control yet — everything takes its
  configuration via CLI args/hardcoded startup flags, restart/rerun to
  change (the beacon/C2 pair's one exception: a command can be queued for
  the implant without restarting anything, by writing to
  `/tmp/c2_pending_command.json` on Kali - see the script's docstring).

Still not built:

- EWS: small automation for periodic legitimate setpoint nudges (noise
  floor).
- Kali or router: small script for benign ARP churn (noise floor).
- Noise-floor scheduler: seeded, needs a home (likely a small controller
  process — TBD where).
- Dashboard: new "Cyber Injects" and "Noise Floor" sections on the existing
  Fault Injection page, following the same pattern as the physical fault
  controls (mode/severity where applicable, a seed input for the noise
  floor).
- Some new control surface on Kali the dashboard can reach to start/stop/
  configure the relay/injection scripts and noise floor (mirrors how the
  simulation container already exposes a control channel for physical
  faults). For the beacon/C2 pair specifically, this could be as simple as
  the dashboard writing to the same pending-command file/API a manual
  `docker exec` currently would.

## 8. Open risks / questions to resolve before or during implementation

- ~~**ARP spoofing reliability** in this specific Docker macvlan setup~~ —
  **resolved, confirmed working.** Verified empirically against real running
  containers (`router`, `HMI`, `kali`, images pulled from Docker Hub):
  `arpspoof -i eth1 -t <HMI> <router-IP>` (from `dsniff`, already installed
  in the Kali image) successfully and continuously poisoned HMI's ARP cache
  to point the router's IP at Kali's MAC. Better still, Kali's `ip_forward`
  is already `1`, so the kernel transparently relayed a real HTTP request
  from HMI through Kali to the actual router and back with no extra proxy
  code — basic interception works out of the box. Rewriting Modbus content
  in flight (rather than pure passthrough) will still need an explicit
  userspace proxy (e.g. `iptables`/`NFQUEUE` + a `pymodbus`-based rewriter,
  which is also already installed in the Kali image) rather than relying on
  kernel forwarding alone.
- ~~**Reset between trials**~~ — **resolved, cheaper than assumed.** A full
  container restart is not necessary. Simply killing the `arpspoof` process
  is enough — HMI's ARP cache self-healed back to the router's real MAC
  within seconds on its own (confirmed via repeated checks and a forced
  fresh request), no restart or manual cache-clearing needed. This avoids
  paying HMI's slow healthcheck ramp (~60s+ `start_period`) between every
  trial.
- ~~**Connection redirect + local termination**~~ — **resolved, confirmed
  working.** Verified that ARP spoofing alone (kernel forwarding) only
  gives passthrough, not rewriting capability, so also tested an
  `iptables` PREROUTING REDIRECT rule on Kali (port 5000 &rarr; a local
  listener on 8888) alongside the ARP spoof: HMI's request was served by
  Kali's own local process, not passed through to the real router,
  confirming the connection genuinely terminates at Kali rather than
  merely flowing through it. This is the mechanism a pymodbus-based proxy
  (server side accepting HMI's connection, client side talking to the real
  PLC) would sit behind. **Implementation note**: `iptables` is not
  installed in the Kali image by default (only `dsniff`, `kali-tools-top10`,
  `python3-pymodbus`, `net-tools` are) - needs adding to
  `attacker/Dockerfile` for the real build.
- ~~**Full Modbus-specific end-to-end validation**~~ — **done, not just the
  HTTP stand-in above.** Built `attacker/cyber_injects/modbus_relay.py` and
  ran the complete chain (ARP spoof + REDIRECT + the relay in frozen mode)
  against real `plc`/`simulation`/`HMI`/`router`/`kali` containers. HMI,
  polling the PLC's real IP exactly as it normally would, received a frozen
  value while a direct read from the ICS side showed the true value still
  changing at the same moment. Three things learned along the way, worth
  recording so they don't get rediscovered:
  - `python3-pymodbus` from kali-rolling's apt repo is 3.14+, which has a
    substantially different, simulator-based datastore API than
    `pymodbus==3.9.2`, already used by `simulation/remote_io/modbus/*.py`.
    Fixed by pinning the same version via pip at build time instead (the lab
    network is intentionally isolated at runtime, so this can't happen live
    in a running container).
  - A container reporting "healthy" doesn't mean every service inside it is
    actually ready — `plc`'s healthcheck only probes its web UI (port 8080),
    not its Modbus server, so there's a real gap where the container is
    "healthy" but a fresh Modbus connection attempt still fails. Worth
    building in a retry rather than assuming healthy = fully ready.
  - The PLC's Modbus server exposes live, changing telemetry at input
    register addresses starting around 100 (confirmed non-zero, live values
    at 100-109), consistent with the `%IW100-112` mapping noted in
    `plc/st_files/326339.st` from the earlier physical-fault investigation -
    useful as a known-good target for testing without needing to reverse
    ScadaLTS's own (serialized, not human-readable) point configuration.
  - Not a design gotcha, just a testing trap worth naming: a connection
    failure from Kali to the PLC that looks identical to a firewall block or
    a not-ready-yet PLC can also just mean the `router` container isn't
    running - the actual error (`connect_ex` returning errno 113, "No route
    to host") is diagnostic and worth checking before assuming anything more
    interesting is going on.
- **Where the "PLC's own view" check actually happens** for the read-path
  tells — via the EWS UI, a new diagnostic surface, or something else —
  isn't decided yet.
- **Statistical power**: given the likely small volunteer N and a
  between-subjects design, results should be framed explicitly as a pilot,
  not a statistically powered study.
- ~~**Can Suricata even see the beacon traffic?**~~ — **resolved: no, it
  cannot, structurally.** Kali and HMI are both on the DMZ segment (§3);
  Suricata sits on the router's eth2 interface, and same-subnet macvlan
  traffic between two endpoints on the same segment never transits the
  router's interface at all. See §4.4 for the implication - this makes the
  write-frequency tell the only network-level detection surface for this
  scenario, and points at HMI's existing Wazuh agent (host-based, segment-
  agnostic) as the right place to look if beaconing detection is wanted
  later, not more Suricata rules.
- ~~**Live validation of the beacon/C2 mechanism**~~ — **resolved,
  confirmed working end-to-end** (§4.4): queuing a command on Kali's state
  file, the implant picked it up on its next check-in and executed the
  real Modbus write, moving the real valve, with no restart of anything
  needed.

## 9. Broader evidence plan for the talk (context, not part of this build)

This tooling is one of four planned evidence sources for the S4 talk, not
the only one:

1. Mining public incident data (CISA ICS-CERT, RISI, Dragos/Waterfall/SANS
   surveys) for real base-rate numbers and reclassification examples.
2. A short anonymous survey of the broader OT security community.
3. This volunteer pilot study, explicitly labeled as such.
4. A live audience poll during the talk itself (largest reachable N).

**Timeline**: talk is February; final slides due January. Recruiting and the
survey should start immediately, in parallel with building the tooling
described here, since recruiting real analysts' calendars is the highest
schedule risk in the plan — not the engineering.
