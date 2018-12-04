from time import sleep
from math import log, fmod

from smbus2 import SMBusWrapper, i2c_msg

class CCS811IO:
    """
    I/O operation with CCS811
    """
    ADDRESS = 0x5A
    BUS = 1

    def read(self, reg, count):
        """
        I2C read data from register
        """
        with SMBusWrapper(self.BUS,) as bus:
            data = bus.read_i2c_block_data(self.ADDRESS, reg, count)

        return data

    def write(self, reg, data):
        """
        I2C write data to register
        """
        with SMBusWrapper(self.BUS,) as bus:
            bus.write_i2c_block_data(self.ADDRESS, reg, data)

    def read_byte(self, reg):
        return self.read(reg, 1)[0]


class CCS811:
    REG_STATUS = 0x00
    REG_HW_ID = 0x20
    REG_MEAS_MODE = 0x01
    REG_ALG_RESULT_DATA = 0x02
    REG_ENV_DATA = 0x05
    REG_NTC = 0x06
    
    BOOTLOADER_APP_START = 0xF4

    HW_ID_CODE = 0x81
    DRIVE_MODE_1SEC = 0b10000

    BIT_ERROR = 0b1
    BIT_FW_OK = 0b10000
    BIT_DATA_RDY = 0b1000

    REF_RESISTOR = 100000

    def __init__(self):
        self._io = CCS811IO()

        self.temp_offset = 0

        if self._io.read_byte(self.REG_HW_ID) != self.HW_ID_CODE:
            raise Exception("Unexpected hardware ID")

        self._io.write(self.BOOTLOADER_APP_START, [])
        sleep(0.1)

        status = self._get_status()

        if status & self.BIT_ERROR:
            raise Exception("Error has occurred")
        if not (status & self.BIT_FW_OK):
            raise Exception("FW error has occurred")

        self._start_measuring()

    def _get_status(self):
        return self._io.read_byte(self.REG_STATUS)

    def _start_measuring(self):
        self._io.write(self.REG_MEAS_MODE, [self.DRIVE_MODE_1SEC])

    def data_ready(self):
        return bool(self._io.read_byte(self.REG_STATUS) & self.BIT_DATA_RDY)

    def read_temperature(self):
        buf = self._io.read(self.REG_NTC, 4)
        vref = (buf[0] << 8) | buf[1]
        vntc = (buf[2] << 8) | buf[3]

        rntc = float(vntc) * self.REF_RESISTOR / float(vref)

        ntc_temp = log(rntc / 10000.0)
        ntc_temp /= 3380.0
        ntc_temp += 1.0 / (25 + 273.15)
        ntc_temp = 1.0 / ntc_temp
        ntc_temp -= 273.15
        return ntc_temp - self.temp_offset

    def read_measurement(self):
        buf = self._io.read(self.REG_ALG_RESULT_DATA, 5)
        status = buf[4]
        
        if status & self.BIT_ERROR:
            raise Exception("Error has occurred")

        data = buf[:4]
        eCO2 = (data[0] << 8) | (data[1])
        TVOC = (data[2] << 8) | (data[3])
        return eCO2, TVOC

    def set_environment(self, temperature, humidity):
        """
        Humidity is stored as an unsigned 16 bits in 1/512%RH.
        The default value is 50% = 0x64, 0x00. 
        As an example 48.5% humidity would be 0x61, 0x00.
       
        Temperature is stored as an unsigned 16 bits integer in 1/512 degrees; 
        there is an offset: 0 maps to -25°C. 
        The default value is 25°C = 0x64, 0x00. 
        As an example 23.5% temperature would be 0x61, 0x00.
        """
        
        temp = int((temperature + 25) * 512)
        hum = int(humidity * 512)
        data = [
            (temp & 0xff00) >> 8, 
            temp & 0xff,
            (hum & 0xff00) >> 8, 
            hum & 0xff,
            ]
        self._io.write(self.REG_ENV_DATA, data)


if __name__ == "__main__":
    sensor = CCS811()

    sensor.set_environment(23.5, 48.5)

    
    for _ in range(10):
        if sensor.data_ready():
            print(sensor.read_temperature())
            print(sensor.read_measurement())
        sleep(1)
