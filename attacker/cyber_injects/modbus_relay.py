#!/usr/bin/env python3
"""Modbus MITM relay for cyber-attack fault injection.

See docs/cyber-vs-physical-fault-injection-design.md for the design this
implements.

Continuously polls a register range from the real Modbus TCP target (e.g.
the PLC) and re-serves it on this relay's own Modbus TCP port, applying an
optional fault mode to what gets served without ever touching the polled
values themselves. This mirrors the true/measured split used for the
physical sensor faults in simulation/simulation/TE_process.cc: "true" is
what this script reads from the real target every poll; "measured" is what
it actually serves, and only the served copy is ever faulted.

Getting a real Modbus master's connection to land here instead of going
straight to the real target (ARP spoofing + a REDIRECT rule) is a separate,
already-verified concern - this script only needs to be handed a TCP
connection, it doesn't care how it got there.

This first version takes its fault config as CLI args (restart to change
it); a runtime control API to match the physical fault dashboard is a
follow-up once this core relay is validated against the real PLC.
"""

import argparse
import asyncio
import random
import time

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusServerContext,
    ModbusSlaveContext,
)
from pymodbus.server import StartAsyncTcpServer

# fault modes - mirrors TE_process.cc's SENSOR_FAULT_* constants
FAULT_NONE = 0
FAULT_FROZEN = 1
FAULT_DRIFT = 2
FAULT_NOISE = 3
FAULT_DROPOUT = 4

DROPOUT_PERIOD_SECONDS = 10.0


def clamp16(value):
    return max(0, min(65535, int(value)))


class FaultState:
    """Mutable fault configuration applied to one relayed register range."""

    def __init__(self, mode=FAULT_NONE, severity=0.0):
        self.mode = mode
        self.severity = severity
        self._bias = 0.0
        self._frozen = None

    def apply(self, true_values, dt_seconds, now_seconds):
        if self.mode == FAULT_FROZEN:
            if self._frozen is None:
                self._frozen = list(true_values)
            return self._frozen
        self._frozen = None

        if self.mode == FAULT_DRIFT:
            self._bias += self.severity * dt_seconds
            return [clamp16(v + self._bias) for v in true_values]
        self._bias = 0.0

        if self.mode == FAULT_NOISE:
            amplitude = int(self.severity)
            if amplitude <= 0:
                return list(true_values)
            return [clamp16(v + random.randint(-amplitude, amplitude)) for v in true_values]

        if self.mode == FAULT_DROPOUT:
            if self.severity <= 0:
                return list(true_values)
            phase = (now_seconds % DROPOUT_PERIOD_SECONDS) / DROPOUT_PERIOD_SECONDS
            if phase < self.severity:
                return [0] * len(true_values)
            return list(true_values)

        return list(true_values)


async def poll_loop(args, store, fault):
    client = AsyncModbusTcpClient(args.target_host, port=args.target_port)
    read = client.read_input_registers if args.register_type == "input" else client.read_holding_registers
    # matches the datablock selector convention already used by
    # simulation/remote_io/modbus/*.py: 4 for input registers, 3 for holding
    datastore_fc = 4 if args.register_type == "input" else 3
    last_time = time.monotonic()
    while True:
        try:
            if not client.connected:
                connected = await client.connect()
                if not connected:
                    print(f"[modbus_relay] could not connect to {args.target_host}:{args.target_port}", flush=True)
                    await asyncio.sleep(args.interval)
                    continue
            result = await read(args.address, count=args.count, slave=args.target_slave_id)
            now_mono = time.monotonic()
            dt = now_mono - last_time
            last_time = now_mono
            if result.isError():
                print(f"[modbus_relay] read error: {result}", flush=True)
            else:
                reported = fault.apply(result.registers, dt, time.time())
                store.setValues(datastore_fc, args.address, reported)
                print(f"[modbus_relay] true={result.registers} reported={reported}", flush=True)
        except Exception as exc:
            print(f"[modbus_relay] poll exception: {exc}", flush=True)
        await asyncio.sleep(args.interval)


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-host", required=True, help="real Modbus target, e.g. the PLC's IP")
    parser.add_argument("--target-port", type=int, default=502)
    parser.add_argument("--target-slave-id", type=int, default=1)
    parser.add_argument("--listen-host", default="0.0.0.0")
    parser.add_argument("--listen-port", type=int, default=5502)
    parser.add_argument("--register-type", choices=["holding", "input"], default="holding")
    parser.add_argument("--address", type=int, default=0, help="starting register address")
    parser.add_argument("--count", type=int, default=1, help="number of consecutive registers")
    parser.add_argument("--interval", type=float, default=0.2, help="poll interval in seconds")
    parser.add_argument("--mode", type=int, choices=[0, 1, 2, 3, 4], default=FAULT_NONE,
                         help="0=none 1=frozen 2=drift 3=noise 4=dropout")
    parser.add_argument("--severity", type=float, default=0.0)
    args = parser.parse_args()

    fault = FaultState(mode=args.mode, severity=args.severity)

    block_kwargs = {"hr" if args.register_type == "holding" else "ir":
                     ModbusSequentialDataBlock(args.address, [0] * args.count)}
    slave_store = ModbusSlaveContext(**block_kwargs)
    server_context = ModbusServerContext(slaves=slave_store, single=True)

    print(f"[modbus_relay] relaying {args.register_type} registers "
          f"{args.address}..{args.address + args.count - 1} from "
          f"{args.target_host}:{args.target_port} -> listening on "
          f"{args.listen_host}:{args.listen_port}, mode={args.mode} severity={args.severity}",
          flush=True)

    await asyncio.gather(
        poll_loop(args, slave_store, fault),
        StartAsyncTcpServer(context=server_context, address=(args.listen_host, args.listen_port)),
    )


if __name__ == "__main__":
    asyncio.run(main())
