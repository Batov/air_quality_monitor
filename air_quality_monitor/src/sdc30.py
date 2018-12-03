from struct import unpack

import pigpio # http://abyz.co.uk/rpi/pigpio/python.html

class SDC30IO:
    """
    I/O operation with SDC30
    """

    ADDRESS = 0x61
    BUS = 1

    def __init__(self, int_callback=None):
        self._cb = int_callback

        self._gpio = pigpio.pi()
        self._i2c = self._gpio.i2c_open(self.BUS, self.ADDRESS)

        if self._i2c < 0:
            raise BlockingIOError("I2C device (%s) open failed, ret code: %s"\
            % (self.ADDRESS, self._i2c))

    def read(self, count):
        """
        Raw read data without register
        """
        return self._gpio.i2c_read_device(self._i2c, count)

    def write(self, data):
        """
        Raw write data without register
        """
        self._gpio.i2c_write_device(self._i2c, data)


class SDC30:
    """
    doc/SCD30_Interface_Description.pdf
    """
    CMD_TRIGGER_CONT_MEASUREMENT = 0x0010
    CMD_SET_MEASUREMENT_INTERVAL = 0x4600
    CMD_READ_MEASUREMENT = 0x0300

    def __init__(self):
        self._io = SDC30IO()

        self._start_measuring()
        self._set_measurement_interval()

    def _read_measurement(self):
        """
        Read measurement results
        6 words + 6 CRC bytes
        """
        self._send_cmd(self.CMD_READ_MEASUREMENT)
        bytes_to_read = 6*2+6
        count, data = self._io.read(bytes_to_read)
        if bytes_to_read != count:
            raise ValueError("I2C read count error")

        raw = self._unpack_bytes(data)
        co2 = unpack('>f', raw[:4])
        temp = unpack('>f', raw[4:8])
        hum = unpack('>f', raw[8:])
        return co2, temp, hum

    def _start_measuring(self, pressure_offset_mbar=1000):
        if pressure_offset_mbar not in range(700, 1200):
            raise ValueError("Pressure offset must be in [700, 1200]")
        self._send_cmd(self.CMD_TRIGGER_CONT_MEASUREMENT, [pressure_offset_mbar])

    def _set_measurement_interval(self, interval=2):
        if interval not in range(2, 1800):
            raise ValueError("Measurement interval must be in [2, 1800]")
        self._send_cmd(self.CMD_TRIGGER_CONT_MEASUREMENT, [interval])

    def _send_cmd(self, cmd, args=None):
        if args is None:
            args = []
        buf = self._pack_words([cmd] + args)
        self._io.write(buf)

    def _crc(self, data):
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

    def _pack_words(self, words):
        """
        Pack words with CRC8
        """
        def msb(word):
            return (word & 0xFF00) >> 8
        def lsb(word):
            return word & 0x00FF

        result = []
        for word in words:
            data = [msb(word), lsb(word)]
            crc = self._crc(data)
            result += data + [crc]

        return result


if __name__ == "__main__":
    sdc = SDC30()

    import time
    time.sleep(3)
    print(sdc._read_measurement())