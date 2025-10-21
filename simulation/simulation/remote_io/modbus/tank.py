import asyncio
import json
import modbusdevice

async def handletank(context, reader, writer, interval):
    while True:
        slave_id = 0x01
        data = await modbusdevice.readData(reader, writer, interval)
        try:
            pressure = int(data["outputs"]["pressure"]/3200.0*65535)
            level = int(data["outputs"]["liquid_level"]/100.0*65535)
            pressure = modbusdevice.clamp_value(pressure)
            level = modbusdevice.clamp_value(level)
            context[slave_id].setValues(4, 1, [pressure,level])
            context[slave_id].getValues(0x03, 0, 2)
        except:
            print("read error")

if __name__ == "__main__":
    asyncio.run(modbusdevice.run_device("Reactor", "192.168.95.14", handletank))
