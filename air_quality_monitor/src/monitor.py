from gevent import monkey
monkey.patch_all()

import gevent

from scd30 import SCD30
from ccs811 import CCS811

class Monitor:
    def __init__(self, update_env=600):
        self._scd30 = SCD30(use_pin=True)
        self._ccs811 = CCS811(use_pin=True)

        self.CO2 = 0
        self.eCO2 = 0
        self.temp = 0
        self.temp_NTC = 0
        self.hum = 0
        self.TVOC = 0

        self._update_env = update_env

        gevent.spawn(self._data_loop)
        gevent.spawn(self._update_env_loop)

    def _update_env_loop(self):
        while True:
            gevent.sleep(self._update_env)
            self._ccs811.set_environment(self.temp, self.hum)
            self._ccs811.temp_offset = self.temp

    def _data_loop(self):
        """
        Poll data from sensor
        """
        while True:
            if self._ccs811.data_ready():
                ccs811_result = self._ccs811.read_measurement()
                self.eCO2, self.temp_NTC, self.TVOC = ccs811_result

            if self._scd30.data_ready():
                scd30_result = self._scd30.read_measurement()
                self.CO2, self.temp, self.hum = scd30_result

            gevent.sleep(0.5)

def get_monitor():
    """
    Singleton
    """
    if get_monitor.instance is None:
        get_monitor.instance = Monitor()
    return get_monitor.instance
get_monitor.instance = None

if __name__ == "__main__":
    monitor = get_monitor()

    while True:
        gevent.sleep(3)
        print("---------------------------")
        print("CO2: %d ppm" % monitor.CO2)
        print("eCO2: %d ppm" % monitor.eCO2)
        print("temp: %.2f C" % monitor.temp)
        print("hum: %d%%" % monitor.hum)
        print("TVOC: %d ppb" % monitor.TVOC)
