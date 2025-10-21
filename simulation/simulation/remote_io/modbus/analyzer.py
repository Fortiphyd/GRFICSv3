import asyncio
import json
import modbusdevice

async def handleanalyzer(context, reader, writer, interval):
    while True:
        slave_id = 0x01
        data = await modbusdevice.readData(reader, writer, interval)
        try:
            a_in_purge = int(data["outputs"]["A_in_purge"]*65535)
            b_in_purge = int(data["outputs"]["B_in_purge"]*65535)
            c_in_purge = int(data["outputs"]["C_in_purge"]*65535)
            context[slave_id].setValues(4, 1, [a_in_purge,b_in_purge,c_in_purge])
            context[slave_id].getValues(0x03, 0, 2)
        except:
            print("read error")
        await asyncio.sleep(interval)  # Sleep for 1 second


if __name__ == "__main__":
    asyncio.run(modbusdevice.run_device("Analyzer", "192.168.95.15", handleanalyzer))
