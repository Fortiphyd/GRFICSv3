from modbus.client import ModbusClient

# MISSING
# 20 (0x14) Read File Record
# 21 (0x15) Write File Record
# 24 (0x18) Read FIFO Queue
# 43 (0x2B) Encapsulated Interface Transport

# SERIAL LINE ONLY Functions not implemented:
# 07 (0x07) Read Exception Status
# 08 (0x08) Diagnostics
# 11 (0x0B) Get Comm Event Counter
# 12 (0x0C) Get Comm Event Log
# 17 (0x11) Report Slave ID


@ModbusClient.action
def read_device_info(self, level=3, device_id=1):
    """
    Protocol Function
    43 (0x2B) -- Encapsulated Interface Transport
    MEI type: 14 (0x0E) - Read Device Information
    """
    self.log.info(
        f"Read Device Info -- [Device ID: {device_id}]"
    )
    result = self.client.read_device_information(read_code=level, object_id=0)
    return result.information

@ModbusClient.action
def read_coils(self, address, count, device_id=1):
    """
    Protocol Function
    01 (0x01) -- Read Coils
    """
    self.log.info(
        f"Read Coil Status (01) -- [Address: {address}, Count: {count}, Device ID: {device_id}]"
    )
    result = self.client.read_coils(address, count=count, slave=device_id)
    return result


@ModbusClient.action
def read_discrete_inputs(self, address, count, device_id=1):
    """
    Protocol Function
    02 (0x02) -- Read Discrete Inputs
    """
    self.log.info(
        f"Read Discrete Inputs (02) -- [Address: {address}, Count: {count}, Device ID: {device_id}]"
    )
    result = self.client.read_discrete_inputs(address, count=count, slave=device_id)
    return result


@ModbusClient.action
def read_holding_registers(self, address, count, device_id=1):
    """
    Protocol Function
    03 (0x03) -- Read Holding Registers
    """
    self.log.info(
        f"Read Holding Registers (03) -- [Address: {address}, Count: {count}, Device ID: {device_id}]"
    )
    result = self.client.read_holding_registers(address, count=count, slave=device_id)
    return result


@ModbusClient.action
def read_input_registers(self, address, count, device_id=1):
    """
    Protocol Function
    04 (0x04) -- Read Input Registers
    """
    self.log.info(
        f"Read Input Registers (04) -- [Address: {address}, Count: {count}, Device ID: {device_id}]"
    )
    result = self.client.read_input_registers(address, count=count, slave=device_id)
    return result


@ModbusClient.action
def write_coil(self, address, value, device_id=1):
    """
    Protocol Function
    05 (0x05) -- Write Single Coil
    """
    self.log.info(
        f"Write Coil (05) -- [Address: {address}, Value: {value}, Device ID: {device_id}]"
    )
    req = self.client.write_coil(address, value, slave=device_id)
    return req


@ModbusClient.action
def write_register(self, address, value, device_id=1):
    """
    Protocol Function
    06 (0x06) -- Write Single Register
    """
    self.log.info(
        f"Write Single Register (06) -- [Address: {address}, Value: {value}, Device ID: {device_id}]"
    )
    req = self.client.write_register(address, value, slave=device_id)
    return req


@ModbusClient.action
def write_coils(self, address, values, device_id=1):
    """
    Protocol Function
    15 (0x0F) -- Write Multiple Coils
    """
    self.log.info(
        f"Write Multiple Coils (15) -- [Address: {address}, Values: {values}, Device ID: {device_id}]"
    )
    req = self.client.write_coils(address, values, slave=device_id)
    return req


@ModbusClient.action
def write_registers(self, address, values, device_id=1):
    """
    Protocol Function
    16 (0x10) -- Write Multiple Registers
    """
    self.log.info(
        f"Write Multiple Registers (16) -- [Address: {address}, Values: {values}, Device ID: {device_id}]"
    )
    req = self.client.write_registers(address, values, slave=device_id)
    return req


@ModbusClient.action
def mask_write_register(self, address, and_mask, or_mask, device_id=1):
    """
    Protocol Function
    22 (0x16) -- Mask Write Register
    """
    self.log.info(
        f"Mask Write Register (22) -- [Address: {address}, AND_mask: {and_mask}, OR_mask: {or_mask}, Device ID: {device_id}]"
    )
    req = self.client.mask_write_register(address, and_mask, or_mask, slave=device_id)
    return req
