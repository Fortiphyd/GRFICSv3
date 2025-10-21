import asyncio
import json
import modbusdevice

async def handlefeed1(context, reader, writer, interval):
    slave_id = 0x01
    while True:
        await modbusdevice.writeData("f1_valve_sp", writer, context, slave_id)
        data = await modbusdevice.readData(reader, writer, interval)

        try:
            valve_pos = int(data["state"]["f1_valve_pos"] / 100.0 * 65535)
            flow = int(data["outputs"]["f1_flow"] / 500.0 * 65535)

            # Clamp to valid range
            valve_pos = modbusdevice.clamp_value(valve_pos)
            flow = modbusdevice.clamp_value(flow)

            # Update Input Registers (address 1 and 2)
            context[slave_id].setValues(4, 1, [valve_pos, flow])

        except:
            print("read error")

        await asyncio.sleep(interval)  # Sleep for 1 second


if __name__ == "__main__":
    asyncio.run(modbusdevice.run_device("Feed 1", "192.168.95.10", handlefeed1))
