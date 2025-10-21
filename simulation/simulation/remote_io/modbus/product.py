import asyncio
import json
import modbusdevice

async def handleproduct(context, reader, writer, interval):
    while True:
        slave_id = 0x01
        await modbusdevice.writeData("product_valve_sp", writer, context, slave_id)
        data = await modbusdevice.readData(reader, writer, interval)

        try:
            valve_pos = int(data["state"]["product_valve_pos"] / 100.0 * 65535)
            flow = int(data["outputs"]["product_flow"] / 500.0 * 65535)

            # Clamp to valid range
            valve_pos = modbusdevice.clamp_value(valve_pos)
            flow = modbusdevice.clamp_value(flow)

            # Update Input Registers (address 1 and 2)
            context[slave_id].setValues(4, 1, [valve_pos, flow])

        except:
            print("read error")

        await asyncio.sleep(interval)  # Sleep for 1 second


if __name__ == "__main__":
    asyncio.run(modbusdevice.run_device("Product", "192.168.95.13", handleproduct))
