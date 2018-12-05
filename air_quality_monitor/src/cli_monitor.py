from gevent import monkey
monkey.patch_all()

import gevent

from scd30 import SCD30
from ccs811 import CCS811

class CliMonitor:
    def __init__(self):
        self._scd30 = SCD30(use_pin=True)
        self._ccs811 = CCS811(use_pin=True)

        self.CO2 = 0
        self.eCO2 = 0
        self.temp = 0
        self.hum = 0
        self.TVOC = 0

        gevent.spawn(self._data_loop)

    def _data_loop(self):
        """
        Poll data from sensor
        """
        set_env = True
        while True:
            if self._ccs811.data_ready():
                ccs811_result = self._ccs811.read_measurement()
                self.eCO2, _, self.TVOC = ccs811_result

            if self._scd30.data_ready():
                scd30_result = self._scd30.read_measurement()
                self.CO2, self.temp, self.hum = scd30_result

                if set_env:
                    self._ccs811.set_environment(self.temp, self.hum)
                    self._ccs811.temp_offset = self.temp
                    set_env = False

            gevent.sleep(0.5)

if __name__ == "__main__":
    monitor = CliMonitor()

    while True:
        gevent.sleep(3)
        print("---------------------------")
        print("CO2: %d ppm" % monitor.CO2)
        print("eCO2: %d ppm" % monitor.eCO2)
        print("temp: %.2f C" % monitor.temp)
        print("hum: %d%%" % monitor.hum)
        print("TVOC: %d ppb" % monitor.TVOC)
