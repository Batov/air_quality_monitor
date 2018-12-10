from gevent import monkey
monkey.patch_all()

from time import time

import csv
import gevent

from monitor import get_monitor

class CSVMonitor:
    def __init__(self, filename):
        self._mon = get_monitor()
        self._filename = filename
        self._write_header()

    def _write_to_file(self, data):
        with open(self._filename, 'a') as output:
            writer = csv.writer(output,
                                delimiter=';',
                                dialect='excel',
                                quoting=csv.QUOTE_ALL)
            writer.writerow(data)

    def _write_header(self):
        self._write_to_file(("time", "co2", "temp", "hum", "tvoc"))

    def write_row(self):
        row = (int(time()), self._mon.CO2, self._mon.temp, self._mon.hum, self._mon.TVOC)
        self._write_to_file(row)

if __name__ == "__main__":
    filename = "air_log.csv"

    import os
    if os.path.exists(filename):
        os.remove(filename)

    monitor = CSVMonitor(filename)
    print("CSVMonitor started")

    while True:
        monitor.write_row()
        gevent.sleep(10)
