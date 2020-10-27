import json
import random
from threading import Thread
import time
import urllib.request


class AutomatThread(Thread):
    def __init__(self, id: int, host, port):
        Thread.__init__(self)
        self.id = id
        self.host = host
        self.port = port
        self.active_state = None

    def update_status(self):
        active_state = 'A'

        while True:
            time.sleep(random.uniform(1, 3))
            try:
                value = yield active_state
            except StopIteration:
                pass
            else:
                if active_state == 'A':
                    if value >= 10:
                        active_state = 'B'
                    elif value < 5:
                        active_state = 'C'
                    else:
                        active_state = 'A'

                elif active_state == 'B':
                    if value >= 50:
                        active_state = 'C'
                    elif value < 5:
                        active_state = 'D'
                    else:
                        active_state = 'B'

                elif active_state == 'C':
                    if value >= 90:
                        active_state = 'D'
                    elif value < 5:
                        active_state = 'E'
                    else:
                        active_state = 'C'

                elif active_state == 'D':
                    if value >= 130:
                        active_state = 'D'
                    elif value < 5:
                        active_state = 'F'
                    else:
                        active_state = 'E'

                elif active_state == 'E':
                    if value >= 170:
                        active_state = 'F'
                    elif value < 5:
                        active_state = 'A'
                    else:
                        active_state = 'E'

                elif active_state == 'F':
                    active_state = 'F'
                    break

    def send(self, data):
        rsp = json.dumps(data).encode('utf-8')

        with urllib.request.urlopen(f"http://{self.host}:{self.port}", rsp) as f:
            try:
                response = json.load(f)
            except Exception as e:
                print(e)

        return int(response['message']['y'])

    def run(self):
        automat = self.update_status()
        self.active_state = automat.send(None)
        while True:
            random_x = random.randint(1, 255)

            data = {
                'status': self.active_state,
                'x': random_x,
                'id': self.id
            }
            answer_y = self.send(data)

            try:
                self.active_state = automat.send(answer_y)
            except StopIteration:
                break