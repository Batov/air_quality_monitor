from gevent import monkey
monkey.patch_all()

import gevent

from geventwebsocket import WebSocketServer, WebSocketApplication, Resource

from scd30 import SCD30

scd30 = SCD30(use_pin=True)

class Application(WebSocketApplication):
    def on_open(self):
        while True:
            if scd30.data_ready():
                scd30_result = scd30.read_measurement()
                self.ws.send("%d %d %d\n" % scd30_result)
            gevent.sleep(1)

    def on_close(self, reason):
        print("Connection Closed", reason)


def get_html(_, start_response):
    start_response("200 OK", [("Content-Type", "text/html")])
    return [bytes(line, "utf-8") for line in open("air_quality_monitor/static/monitor.html").readlines()]


resource = Resource([
    ('/', get_html),
    ('/data', Application)
])

if __name__ == "__main__":
    server = WebSocketServer(('', 8000), resource, debug=True)
    server.serve_forever()