import json
import logging
import random
from threading import Thread, Event
import time
import urllib.request


class AutomatThread(Thread):
    def __init__(self, name, host, port, event_stop):
        Thread.__init__(self, name=name)
        self.host = host
        self.port = port
        self.event_stop = event_stop
        self.logger = logging.getLogger(f"TestAutomat.Client #{self.name}")

        self.status_A, self.status_B, self.status_C = 'A', 'B', 'C'
        self.status_D, self.status_E, self.status_F = 'D', 'E', 'F'

    def update_status(self):
        active_state = self.status_A

        while True:
            time.sleep(random.uniform(1, 3))
            try:
                value = yield active_state
            except StopIteration:
                pass
            else:
                if active_state == self.status_A:
                    if value >= 10:
                        active_state = self.status_B
                    elif value < 5:
                        active_state = self.status_C
                    else:
                        active_state = self.status_A

                elif active_state == self.status_B:
                    if value >= 50:
                        active_state = self.status_C
                    elif value < 5:
                        active_state = self.status_D
                    else:
                        active_state = self.status_B

                elif active_state == self.status_C:
                    if value >= 90:
                        active_state = self.status_D
                    elif value < 5:
                        active_state = self.status_E
                    else:
                        active_state = self.status_C

                elif active_state == self.status_D:
                    if value >= 130:
                        active_state = self.status_D
                    elif value < 5:
                        active_state = self.status_F
                    else:
                        active_state = self.status_E

                elif active_state == self.status_E:
                    if value >= 170:
                        active_state = self.status_F
                    elif value < 5:
                        active_state = self.status_A
                    else:
                        active_state = self.status_E

                elif active_state == self.status_F:
                    active_state = self.status_F
                    break

    def send(self, data):
        rsp = json.dumps(data).encode('utf-8')

        try:
            req = urllib.request.Request(url=f"http://{self.host}:{self.port}", data=rsp)
            req.add_header('Content-Type', 'application/json; charset=UTF-8')
            with urllib.request.urlopen(req) as f:
                response = json.load(f)
        except Exception as e:
            self.logger.error(str(e))

        return int(response['message']['y'])

    def run(self):
        automat = self.update_status()
        active_state = automat.send(None)
        while not self.event_stop.is_set():
            random_x = random.randint(1, 255)

            data = {
                'status': active_state,
                'x': random_x,
                'id': self.name
            }
            answer_y = self.send(data)

            try:
                active_state = automat.send(answer_y)
            except StopIteration:
                break

if __name__ == '__main__':
    HOST, PORT = '127.0.0.1', 8001
    for name in range(0, 32):
        thread = AutomatThread(name, HOST, PORT, Event())
        thread.start()
