from gevent import monkey
monkey.patch_all()

from time import time

import gevent
from geventwebsocket import WebSocketServer, WebSocketApplication, Resource

from monitor import get_monitor

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
                         (mon.CO2, mon.temp, mon.hum, mon.eCO2, mon.TVOC))
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
