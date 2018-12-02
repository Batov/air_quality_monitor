from struct import unpack

import pigpio # http://abyz.co.uk/rpi/pigpio/python.html
import crc8

class SDC30IO:

    ADDRESS = 0x61
    BUS = 1

    def __init__(self, int_callback=None):
        self._cb = int_callback

        self._gpio = pigpio.pi()
        self._i2c = self._gpio.i2c_open(self.BUS, self.ADDRESS)

        if self._i2c < 0:
            raise BlockingIOError("I2C device (%s) open failed, ret code: %s" % (self.ADDRESS, self._i2c))

    def read(self, count):
        return self._gpio.i2c_read_device(self._i2c, count)

    def write(self, data):
        self._gpio.i2c_write_device(self._i2c, data)


class SDC30:
    """
    https://cdn.sparkfun.com/assets/d/c/0/7/2/SCD30_Interface_Description.pdf
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
        self._send_cmd(CMD_READ_MEASUREMENT)
        data = self._io.read(6*2+6)
        words = self._unpack_words(data)
        co2 = unpack('f', bytes((words[0] << 16) | words[1]))
        temp = unpack('f', bytes((words[2] << 16) | words[3]))
        hum = unpack('f', bytes((words[4] << 16) | words[5]))
        return co2, temp, hum

    def _start_measuring(self, pressure_offset_mbar=1013):
        if pressure_offset_mbar not in range(700, 1200):
            raise ValueError("Pressure offset must be in [700, 1200]")
        self._send_cmd(self.CMD_TRIGGER_CONT_MEASUREMENT, [pressure_offset_mbar])

    def _set_measurement_interval(self, interval=2):
        if interval not in range(2, 1800):
            raise ValueError("Measurement interval must be in [2, 1800]")
        self._send_cmd(self.CMD_TRIGGER_CONT_MEASUREMENT, [interval])

    def _send_cmd(self, cmd, args=None):
        buf = self._pack_words([cmd] + args)
        self._io.write(buf)

    def _crc(self, data):
        """
        Calculate CRC8 for SCD30
        x^8+x^5+x^4+1 = 0x31
        https://cdn.sparkfun.com/assets/d/c/0/7/2/SCD30_Interface_Description.pdf
        p. 1.1.3
        """
        crc = 0xFF
        for byte in data:
            crc ^= byte;
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x31;
                else:
                    crc = (crc << 1);
        return crc

    def _unpack_words(self, data):
        """
        Unpack words and check CRC8 for each word
        order: [MSB][LSB][CRC]
        """
        assert len(data) % 3 == 0
        words = []
        for i in range(0, len(raw_size), 3):
            crc = data[i+2]
            if self._crc(data[i:i+2]) != crc:
                raise ValueError("CRC check failed")
            word = (data[i] << 8) | data[i+1]
            words.append(word)
        return words

    def _pack_words(self, words):
        """
        Pack words with CRC8
        """
        def msb(word):
            return (word & 0xFF00) >> 8
        def lsb(word):
            return (word & 0x00FF)

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