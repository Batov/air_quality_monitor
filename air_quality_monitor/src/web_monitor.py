from gevent import monkey
monkey.patch_all()

from time import time

import gevent
from geventwebsocket import WebSocketServer, WebSocketApplication, Resource

from scd30 import SCD30
from ccs811 import CCS811


class Monitor:
    """
    Data poller
    """
    def __init__(self):
        self.scd30 = SCD30(use_pin=True)
        self.ccs811 = CCS811(use_pin=True)

        self.co2 = 0
        self.temp = 0
        self.hum = 0
        self.eco2 = 0
        self.tvoc = 0

        gevent.spawn(self._process_loop)

    def _process_loop(self):
        set_env_counter = 1000
        while True:
            if self.scd30.data_ready():
                self.co2, self.temp, self.hum = self.scd30.read_measurement()

            if self.ccs811.data_ready():
                self.eco2, _, self.tvoc = self.ccs811.read_measurement()

            if set_env_counter == 0:
                print("Update env options")
                self.ccs811.set_environment(self.temp, self.hum)
                set_env_counter = 1000
            else:
                set_env_counter -= 1
            gevent.sleep(0.5)

def get_monitor():
    """
    Singleton
    """
    if get_monitor.instance is None:
        get_monitor.instance = Monitor()
    return get_monitor.instance
get_monitor.instance = None

class Application(WebSocketApplication):
    """
    Web App class
    """
    def on_open(self):
        """
        On socket open callback
        """
        mon = get_monitor()
        while True:
            self.ws.send("%.1f %.1f %.1f %.1f %.1f" %
                         (mon.co2, mon.temp, mon.hum, mon.eco2, mon.tvoc))
            gevent.sleep(0.05)

    def on_close(self, reason):
        """
        On socket close callback
        """
        print("Connection closed", reason)

def get_html(_, start_response):
    """
    Get HTML for browser
    """
    start_response("200 OK", [("Content-Type", "text/html")])
    return [bytes(line, "utf-8") 
            for line in open("air_quality_monitor/static/monitor.html").readlines()]

resource = Resource([
    ('/', get_html),
    ('/data', Application)
])

if __name__ == "__main__":
    server = WebSocketServer(('', 8000), resource, debug=True)
    print("Server started")
    server.serve_forever()
