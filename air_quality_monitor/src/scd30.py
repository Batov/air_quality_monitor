from struct import unpack
from time import sleep

from smbus2 import SMBusWrapper, i2c_msg

class SCD30IO:
    """
    I/O operation with SCD30
    """
    ADDRESS = 0x61
    BUS = 1
    DATA_RDY_PIN = 4

    def __init__(self, use_pin=False):
        self.use_pin = use_pin
        if use_pin:
            from gpiozero import Button
            self._pin = Button(self.DATA_RDY_PIN, pull_up=False)

    def is_ready(self):
        """
        True if data ready pin is high
        """
        return self.use_pin and self._pin.is_pressed

    def read(self, count):
        """
        Raw read data without register
        """
        with SMBusWrapper(self.BUS,) as bus:
            msg = i2c_msg.read(self.ADDRESS, count)
            bus.i2c_rdwr(msg)
        return list(msg)

    def write(self, data):
        """
        Raw write data without register
        """
        with SMBusWrapper(self.BUS,) as bus:
            msg = i2c_msg.write(self.ADDRESS, data)
            bus.i2c_rdwr(msg)


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

    def __init__(self, use_pin=False):
        """
        data_ready_cb - callback will trigger at data ready event
        You can poll SCD30.data_ready() for same event
        """
        self._io = SCD30IO(use_pin)

        self._start_measuring()
        self._set_measurement_interval(2)
        self._set_auto_self_calibration(enable=True)

        # TODO: Remove it or add datasheet reference
        sleep(0.1)

    def read_measurement(self):
        """
        Read measurement results (6 words + 6 CRC bytes)
        Return CO2, temperature and humidity floats tuple
        """
        self._send_cmd(self.CMD_READ_MEASUREMENT)
        bytes_to_read = 6*2+6
        data = self._io.read(bytes_to_read)
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
        if self._io.use_pin:
            return self._io.is_ready()
        else:
            self._send_cmd(self.CMD_DATA_READY)
            bytes_to_read = 2
            responce = self._io.read(bytes_to_read)
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
                print(data[i:i+2])
                print(crc)
                print(self._crc(data[i:i+2]))
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
    def test(sensor):
        for _ in range(7):
            if sensor.data_ready():
                print(sensor.read_measurement())
            sleep(1)

    print("Pin polling example:")
    scd30_pin = SCD30(use_pin=True)
    test(scd30_pin) 

    print("I2C polling example:")
    scd30_i2c = SCD30(use_pin=False)
    test(scd30_i2c) 
