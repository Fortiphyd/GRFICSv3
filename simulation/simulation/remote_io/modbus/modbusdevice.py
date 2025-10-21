import asyncio
import json
import socket
from pymodbus.server import StartAsyncTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext, ModbusSlaveContext

def clamp_value(value):
    return max(0, min(65535, value))

async def write_with_timeout(writer, data, timeout):
    try:
        writer.write(data)
        await asyncio.wait_for(writer.drain(), timeout=timeout)
    except asyncio.TimeoutError:
        print("Write operation timed out.")
    except Exception as e:
        print(f"An error occurred: {e}")
    #finally:
    #    writer.close()
    #    await writer.wait_closed()

async def read_with_timeout(reader, timeout):
    try:
        return await asyncio.wait_for(reader.readline(), timeout=timeout)
    except asyncio.TimeoutError:
        print("Read operation timed out.")
    except Exception as e:
        print(f"An error occurred: {e}")

async def readData(reader, writer, interval):
    await asyncio.sleep(interval)
    req_str = '{"request":"read"}\n'
    await write_with_timeout(writer, req_str.encode(), 1)
    await asyncio.sleep(interval)
    response = await read_with_timeout(reader, 1)
    try:
        return json.loads(response.decode())
    except:
        return None

async def writeData(name, writer, context, slave_id):
    values = context[slave_id].getValues(16, 1, count=1)
    current_command = (values[0] / 65535.0) * 100.0
    writeDict = {
        "request": "write",
        "data": {
            "inputs": {}
        }
    }
    writeDict["data"]["inputs"][name] = current_command
    request_str = json.dumps(writeDict) + "\n"
    await write_with_timeout(writer, request_str.encode(), 1)

async def run_device(name, ip, handler):
    # Initialize datastore
    store = ModbusSlaveContext(
        di=ModbusSequentialDataBlock(0, list(range(1, 101))),
        co=ModbusSequentialDataBlock(0, list(range(101, 201))),
        hr=ModbusSequentialDataBlock(0, list(range(201, 301))),
        ir=ModbusSequentialDataBlock(0, list(range(301, 401)))
    )
    #context = ModbusServerContext(slaves={0x01: store}, single=False)
    context = ModbusServerContext(slaves=store, single=True)

    # Server identity
    identity = ModbusDeviceIdentification()
    identity.VendorName = 'pymodbus'
    identity.ProductCode = 'PM'
    identity.VendorUrl = 'http://github.com/pymodbus-dev/pymodbus/'
    identity.ProductName = 'pymodbus Server'
    identity.ModelName = 'pymodbus Server'
    identity.MajorMinorRevision = '3.0.0'
    identity.UserApplicationName = name

    # Socket connection to simulator
    HOST = '127.0.0.1'
    PORT = 55555

    async def maintain_connection():
        reader = writer = None
        while True:
            try:
                if writer is None:
                    print(f"[{name}] Connecting to simulator at {HOST}:{PORT} ...")
                    reader, writer = await asyncio.open_connection(HOST, PORT)
                    print(f"[{name}] Connected.")
                    # Start the loop once we have a live socket
                    asyncio.create_task(handler(context, reader, writer, 0.1))

                # Sleep while the handler runs; if it fails, we’ll detect that
                await asyncio.sleep(1)

            except (ConnectionRefusedError, ConnectionResetError, BrokenPipeError) as e:
                print(f"[{name}] Connection lost: {e}. Reconnecting ...")
                if writer:
                    writer.close()
                    await writer.wait_closed()
                writer = reader = None
                await asyncio.sleep(1)

    asyncio.create_task(maintain_connection())

    # Start modbus TCP server
    await StartAsyncTcpServer(
        context=context,
        identity=identity,
        address=(ip, 502)
    )
