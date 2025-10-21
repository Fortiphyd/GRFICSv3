import argparse
import logging
import sys

import modbus.version
from modbus.client import ModbusClient

FORMAT = "%(asctime)-15s %(levelname)-8s %(message)s"
log = logging.getLogger()
log.setLevel(logging.INFO)
handler = logging.StreamHandler(stream=sys.stderr)
handler.setFormatter(logging.Formatter(FORMAT))
log.addHandler(handler)


def coil_value_list(values_str, sep=","):
    values = []
    for val in values_str.split(sep):
        coil_val = to_coil_value(val)
        values.append(coil_val)
    return values


def to_coil_value(value_str):
    if value_str.lower() in ["1", "on", "true", "t"]:
        return True

    if value_str.lower() in ["0", "off", "false", "f"]:
        return False

    raise argparse.ArgumentError(f"Invalid coil value: {value_str}")


def uint_list(values_str, sep=","):
    values = []
    for val in values_str.split(sep):
        int_val = to_16bit_uint(val)
        values.append(int_val)
    return values


def to_16bit_uint(value_str):
    try:
        value = int(value_str)
    except ValueError:
        raise argparse.ArgumentError(
            f"Invalid value {value_str}, values must be a number"
        )

    if value < 0 or value > 65535:
        raise argparse.ArgumentTypeError(f"{value_str} is not a valid 16-bit uint.")
    return value


def add_device_id_arg(parser):
    parser.add_argument(
        "-d",
        "--device",
        dest="device_id",
        type=int,
        required=False,
        default=1,
        help="Device ID to be targeted [0-255]",
    )


def add_read_args(parser):
    parser.add_argument(
        "start",
        type=to_16bit_uint,
        help="The starting address to read from [0-65535]",
    )
    parser.add_argument(
        "count",
        type=to_16bit_uint,
        help="The number of items to read [0-65535]",
    )


def add_fuzz_args(parser):
    parser.add_argument(
        "start",
        type=to_16bit_uint,
        help="The start address of the fuzzing range [0-65535]",
    )
    parser.add_argument(
        "end",
        type=to_16bit_uint,
        help="The end address of the fuzzing range [0-65535]",
    )
    add_device_id_arg(parser)
    parser.add_argument(
        "count",
        type=to_16bit_uint,
        help="Number of write operations to perform [0-65535]",
    )
    parser.add_argument(
        "--wait",
        dest="wait",
        type=float,
        required=False,
        default=0.0,
        help="Seconds to wait between write operations [>= 0.0]",
    )

def add_info_args(parser):
    parser.add_argument(
        "--level",
        dest="level",
        type=to_16bit_uint,
        required=False,
        default=3,
        help="Level of info to request: 1=Basic, 2=Regular, 3=Extended",
    )

def add_write_c_subparser(subparsers):
    parser = subparsers.add_parser(
        "write_c",
        help="Write Single Coil: Write to a single specified coil",
    )
    parser.add_argument(
        "start",
        type=to_16bit_uint,
        help="The starting address to write to [0-65535]",
    )
    parser.add_argument(
        "value",
        type=to_coil_value,
        metavar="value",
        help="The value to be written [ON, OFF]",
    )
    add_device_id_arg(parser)


def add_write_multi_c_subparser(subparsers):
    parser = subparsers.add_parser(
        "write_multi_c",
        help="Write Multiple Coils: Write to a specified range of coils",
    )
    parser.add_argument(
        "start",
        type=to_16bit_uint,
        help="The starting address to write to [0-65535]",
    )
    parser.add_argument(
        "values",
        type=coil_value_list,
        metavar="values",
        help="The values to be written [comma separated list of ON or OFF]",
    )
    add_device_id_arg(parser)


def add_read_c_subparser(subparsers):
    parser = subparsers.add_parser(
        "read_c",
        help="Read Coils: Read the status values for the specified coils",
    )
    add_read_args(parser)
    add_device_id_arg(parser)


def add_read_di_subparser(subparsers):
    parser = subparsers.add_parser(
        "read_di",
        help="Read Discrete Input: Read the status values for the specified discrete inputs",
    )
    add_read_args(parser)
    add_device_id_arg(parser)


def add_write_r_subparser(subparsers):
    parser = subparsers.add_parser(
        "write_r",
        help="Write Single Register: Write to a single specified register",
    )
    parser.add_argument(
        "start",
        type=to_16bit_uint,
        help="The starting address to write to, addressing starts at 0 [0-65535]",
    )
    parser.add_argument(
        "value",
        type=to_16bit_uint,
        help="The value to be written [0-65535]",
    )
    add_device_id_arg(parser)


def add_write_multi_r_subparser(subparsers):
    parser = subparsers.add_parser(
        "write_multi_r",
        help="Write Multiple Registers: Write to a specified range of registers",
    )
    parser.add_argument(
        "start",
        type=to_16bit_uint,
        help="The starting address to write to, addressing starts at 0 [0-65535]",
    )
    parser.add_argument(
        "values",
        type=uint_list,
        metavar="values",
        help="The values to be written [comma separated list of 0-65535]",
    )
    add_device_id_arg(parser)


def add_mask_write_r_subparser(subparsers):
    parser = subparsers.add_parser(
        "mask_write_r",
        help="Mask Write Register: Modifies contents of a single register using AND or OR mask",
    )
    parser.add_argument(
        "start",
        type=to_16bit_uint,
        help="The starting address to write to, addressing starts at 0 [0-65535]",
    )
    parser.add_argument(
        "andmask",
        type=to_16bit_uint,
        help="The value of the AND mask [0-65535]",
    )
    parser.add_argument(
        "ormask",
        type=to_16bit_uint,
        help="The value of the OR mask [0-65535]",
    )
    add_device_id_arg(parser)


def add_read_hr_subparser(subparsers):
    parser = subparsers.add_parser(
        "read_hr",
        help="Read Holding Registers: Read the status values for the specified holding registers",
    )
    add_read_args(parser)
    add_device_id_arg(parser)


def add_read_ir_subparser(subparsers):
    parser = subparsers.add_parser(
        "read_ir",
        help="Read Input Registers: Read the status values for the specified input registers",
    )
    add_read_args(parser)
    add_device_id_arg(parser)


def add_fuzz_c_subparser(subparsers):
    parser = subparsers.add_parser(
        "fuzz_c",
        help="Fuzz Coils: Randomly write coils",
    )
    add_fuzz_args(parser)


def add_fuzz_r_subparser(subparsers):
    parser = subparsers.add_parser(
        "fuzz_r",
        help="Fuzz Registers: Randomly write registers",
    )
    add_fuzz_args(parser)
    parser.add_argument(
        "--min",
        dest="min",
        type=to_16bit_uint,
        required=False,
        default=0,
        help="Minimum register write value [0-65535]",
    )
    parser.add_argument(
        "--max",
        dest="max",
        type=to_16bit_uint,
        required=False,
        default=65535,
        help="Maximum register write value [0-65535]",
    )


def add_read_device_info_subparser(subparsers):
    parser = subparsers.add_parser(
        "read_device_info",
        help="Read device information"
    )
    add_info_args(parser)
    add_device_id_arg(parser)

def create_arg_parser():
    parser = argparse.ArgumentParser(
        description="Modbus Client Action Library " + modbus.version.get_version()
    )

    parser.add_argument("ip", help="The target device IP address")
    parser.add_argument(
        "-p",
        "--port",
        dest="port",
        default="502",
        help="The target device Modbus port [0-65535]",
    )

    subparsers = parser.add_subparsers(
        help="Action to be taken",
        required=True,
        dest="action",
    )
    add_write_c_subparser(subparsers)
    add_write_multi_c_subparser(subparsers)
    add_read_c_subparser(subparsers)
    add_read_di_subparser(subparsers)
    add_fuzz_c_subparser(subparsers)
    add_fuzz_r_subparser(subparsers)
    add_read_hr_subparser(subparsers)
    add_read_ir_subparser(subparsers)
    add_write_r_subparser(subparsers)
    add_write_multi_r_subparser(subparsers)
    add_mask_write_r_subparser(subparsers)
    add_read_device_info_subparser(subparsers)

    return parser


def do_action(client, args):
    if args.action.lower() == "read_di":
        print("[*] Read discrete inputs")
        try:
            result = client.read_discrete_inputs(args.start, args.count, args.device_id)
        except Exception as err:
            print(f"Read failed: {err}")
            log.error(err)
        else:
            print_read_result(result, args.start, args.count, "discrete input")

    elif args.action.lower() == "read_c":
        print("[*] Read coils")
        f = client.get("read_coils")
        try:
            result = f(client, args.start, args.count, args.device_id)
        except Exception as err:
            print(f"Read failed: {err}")
            log.error(err)
        else:
            print_read_result(result, args.start, args.count, "coil")

    elif args.action.lower() == "read_hr":
        print("[*] Read holding registers")
        try:
            result = client.read_holding_registers(
                args.start, args.count, args.device_id
            )
        except Exception as err:
            print(f"Read failed: {err}")
            log.error(err)
        else:
            print_read_result(result, args.start, args.count, "holding register")

    elif args.action.lower() == "read_ir":
        print("[*] Read input registers")
        try:
            result = client.read_input_registers(args.start, args.count, args.device_id)
        except Exception as err:
            print(f"Read failed: {err}")
            log.error(err)
        else:
            print_read_result(result, args.start, args.count, "input register")

    elif args.action.lower() == "write_c":
        print("[*] Write coil")
        result = client.write_coil(args.start, args.value, args.device_id)
        if result.isError():
            print("Write failed")
            log.error("Write error.")
        else:
            print("Write successful")

    elif args.action.lower() == "write_multi_c":
        print("[*] Write multiple coils")
        result = client.write_coils(args.start, args.values, args.device_id)
        if result.isError():
            print("Write failed")
            log.error("Write error")
        else:
            print("Write successful")

    elif args.action.lower() == "write_r":
        print("[*] Write single register")
        result = client.write_register(args.start, args.value, args.device_id)
        if result.isError():
            print("Write failed")
            log.error("Write error")
        else:
            print("Write successful")

    elif args.action.lower() == "write_multi_r":
        print("[*] Write multiple registers")
        result = client.write_registers(args.start, args.values, args.device_id)
        if result.isError():
            print("Write failed")
            log.error("Write error")
        else:
            print("Write successful")

    elif args.action.lower() == "mask_write_r":
        print("[*] Mask write single register")
        result = client.mask_write_register(
            args.start, args.andmask, args.ormask, args.device_id
        )
        if result.isError():
            print("Write failed")
            log.error("Write error")
        else:
            print("Write successful")

    elif args.action.lower() == "fuzz_c":
        print("[*] Fuzz random coils")
        try:
            result = client.fuzz_coils(
                args.start, args.end, args.count, args.wait, args.device_id
            )
        except ValueError as err:
            print(f"Fuzzing failed: {err}")
            log.error(err)
        else:
            print(f"{result[0]} successful write operations, {result[1]} errors")

    elif args.action.lower() == "fuzz_r":
        print("[*] Fuzz random registers")
        try:
            result = client.fuzz_registers(
                args.start,
                args.end,
                args.count,
                args.min,
                args.max,
                args.wait,
                args.device_id,
            )
        except ValueError as err:
            print(f"Fuzzing failed: {err}")
            log.error(err)
        else:
            print(f"{result[0]} successful write operations, {result[1]} errors")
    elif args.action.lower() == "read_device_info":
        print("[*] Read Device Information")
        try:
            result = client.read_device_info(
                args.level,
                args.device_id
            )
        except ValueError as err:
            print(f"Device Info Read failed: {err}")
            log.error(err)
        else:
            print_info_result(result)

    else:
        print("Action not defined.")

def print_info_result(result):
    print(result.information)

def print_read_result(result, start, count, datatype):
    binary_types = ["coil", "discrete input"]
    analog_types = ["holding register", "input register"]

    if datatype in binary_types and not hasattr(result, "bits"):
        print("Print failed: invalid result")
        log.error("Print error: result does not contain 'bits' attribute")
        return

    if datatype in analog_types and not hasattr(result, "registers"):
        print("Print failed: invalid result")
        log.error("Print error: result does not contain 'registers' attribute")
        return

    if datatype in binary_types:
        value_map = {True: "ON", False: "OFF"}
        value_list = [value_map[bit] for bit in result.bits]
    else:
        value_list = result.registers

    for offset in range(count):
        try:
            value = value_list[offset]
        except IndexError:
            value = "out of range"

        print(f"{datatype} {start + offset} = {value}")


def run():
    args = create_arg_parser().parse_args()
    client = ModbusClient(log=log)
    success = client.connect(args.ip, args.port)
    if not success:
        print(f"Failed to connect to {args.ip}:{args.port}")
        return
    do_action(client, args)
    client.disconnect()


if __name__ == "__main__":
    run()
