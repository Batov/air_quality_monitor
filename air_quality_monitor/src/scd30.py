from struct import unpack
from time import sleep

import pigpio # http://abyz.co.uk/rpi/pigpio/python.html

class SCD30IO:
    """
    I/O operation with SCD30
    """
    ADDRESS = 0x61
    BUS = 1
    DATA_RDY_PIN = 4

    def __init__(self, int_callback=None):
        """
        Set int_callback for forward data_ready event
        """
        self._cb = int_callback
        self._pi = pigpio.pi()

        if int_callback:
            self._pi.set_mode(self.DATA_RDY_PIN, pigpio.INPUT)
            self._pi.callback(self.DATA_RDY_PIN, pigpio.RISING_EDGE, self._pigpio_cb)

    def _pigpio_cb(self, gpio, level, _):
        if gpio == self.DATA_RDY_PIN and level:
            if self._cb:
                self._cb()

    def read(self, count):
        """
        Raw read data without register
        """
        i2c = self._pi.i2c_open(self.BUS, self.ADDRESS)
        data = self._pi.i2c_read_device(i2c, count)
        self._pi.i2c_close(i2c)
        return data

    def write(self, data):
        """
        Raw write data without register
        """
        i2c = self._pi.i2c_open(self.BUS, self.ADDRESS)
        self._pi.i2c_write_device(i2c, data)
        self._pi.i2c_close(i2c)


class SCD30:
    """
    doc/SCD30_Interface_Description.pdf
    """
    CMD_TRIGGER_CONT_MEASUREMENT = 0x0010
    CMD_STOP_CONT_MEASUREMENT = 0x0104
    CMD_SET_MEASUREMENT_INTERVAL = 0x4600
    CMD_READ_MEASUREMENT = 0x0300
    CMD_AUTO_SELF_CALIBRATION = 0x5306
    CMD_DATA_READY = 0x0202

    def __init__(self, data_ready_cb=None):
        """
        data_ready_cb - callback will trigger at data ready event
        You can poll SCD30.data_ready() for same event
        """
        self._io = SCD30IO(data_ready_cb)

        self._start_measuring()
        self._set_measurement_interval(2)
        self._set_auto_self_calibration(enable=True)

        sleep(0.1) # wait for start
        self.read_measurement() # Dummy read for flush data_ready status

    def read_measurement(self):
        """
        Read measurement results (6 words + 6 CRC bytes)
        Return CO2, temperature and humidity floats tuple
        """
        self._send_cmd(self.CMD_READ_MEASUREMENT)
        bytes_to_read = 6*2+6
        count, data = self._io.read(bytes_to_read)
        if bytes_to_read != count:
            raise ValueError("I2C read measurement count error")

        raw = self._unpack_bytes(data)
        co2 = unpack('>f', raw[:4])
        temp = unpack('>f', raw[4:8])
        hum = unpack('>f', raw[8:])
        return co2[0], temp[0], hum[0]

    def data_ready(self):
        """
        Check data ready status
        Return True or False
        """
        self._send_cmd(self.CMD_DATA_READY)
        bytes_to_read = 2
        count, responce = self._io.read(bytes_to_read)
        if count != bytes_to_read:
            raise ValueError("I2C read data ready count error")
        return bool(responce[1])

    def _start_measuring(self, pressure_offset_mbar=1000):
        if pressure_offset_mbar not in range(700, 1200):
            raise ValueError("Pressure offset must be in [700, 1200]")
        self._send_cmd(self.CMD_TRIGGER_CONT_MEASUREMENT, [pressure_offset_mbar])

    def _stop_measuring(self):
        self._send_cmd(self.CMD_STOP_CONT_MEASUREMENT)

    def _set_measurement_interval(self, interval=2):
        if interval not in range(2, 1800):
            raise ValueError("Measurement interval must be in [2, 1800]")
        self._send_cmd(self.CMD_SET_MEASUREMENT_INTERVAL, [interval])

    def _set_auto_self_calibration(self, enable=True):
        self._send_cmd(self.CMD_AUTO_SELF_CALIBRATION, [int(enable)])

    def _send_cmd(self, cmd, args=None):
        if args is None:
            args = []
        buf = self._pack_cmd(cmd, args)
        self._io.write(buf)

    @staticmethod
    def _crc(data):
        """
        Calculate CRC8 for SCD30
        x^8+x^5+x^4+1 = 0x31
        doc/SCD30_Interface_Description.pdf
        p. 1.1.3
        """
        crc = 0xFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x31
                else:
                    crc = (crc << 1)
                crc = crc % 0x100
        return crc

    def _unpack_bytes(self, data):
        """
        Unpack bytes and check CRC8 for each bytes coupe
        order: [MSB][LSB][CRC]
        """
        assert len(data) % 3 == 0
        result = bytearray()
        for i in range(0, len(data), 3):
            crc = data[i+2]
            if self._crc(data[i:i+2]) != crc:
                raise ValueError("CRC check failed")
            result.append(data[i])
            result.append(data[i+1])
        return result

    def _pack_cmd(self, cmd, args):
        """
        Pack words with CRC8
        """
        def msb(word):
            """
            Return MSB of byte
            """
            return (word & 0xFF00) >> 8
        def lsb(word):
            """
            Return LSB of byte
            """
            return word & 0x00FF

        result = [msb(cmd), lsb(cmd)]
        for arg in args:
            data = [msb(arg), lsb(arg)]
            crc = self._crc(data)
            result += data + [crc]

        return result


if __name__ == "__main__":
    scd = SCD30()

    for _ in range(7):
        if scd.data_ready():
            print(scd.read_measurement())
        sleep(1)
