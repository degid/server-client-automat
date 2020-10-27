import curses
import json
import os
import random
from multiprocessing import Queue
import signal
import sys
from threading import Thread
import time
import urllib.request

from server_async import Server

HOST, PORT = '127.0.0.1', 8001

count_F_status = 0


class AutomatThread(Thread):
    def __init__(self, id):
        Thread.__init__(self)
        self.id = id
        self.active_state = 'A'

    def set_state(self, state):
        self.active_state = state
        time.sleep(random.uniform(1, 3))

    def update_status(self, value):
        if self.active_state == 'A':
            if value >= 10:
                self.set_state('B')
            elif value < 5:
                self.set_state('C')
            else:
                self.set_state('A')

        elif self.active_state == 'B':
            if value >= 50:
                self.set_state('C')
            elif value < 5:
                self.set_state('D')
            else:
                self.set_state('B')

        elif self.active_state == 'C':
            if value >= 90:
                self.set_state('D')
            elif value < 5:
                self.set_state('E')
            else:
                self.set_state('C')

        elif self.active_state == 'D':
            if value >= 130:
                self.set_state('D')
            elif value < 5:
                self.set_state('F')
            else:
                self.set_state('E')

        elif self.active_state == 'E':
            if value >= 170:
                self.set_state('F')
            elif value < 5:
                self.set_state('A')
            else:
                self.set_state('E')

        elif self.active_state == 'F':
            return True

        return False

    def run(self):
        while True:
            random_x = random.randint(1, 255)

            data = {
                'status': self.active_state,
                'x': random_x,
                'id': self.id
            }
            rsp = json.dumps(data).encode('utf-8')

            with urllib.request.urlopen(f"http://{HOST}:{PORT}", rsp) as f:
                try:
                    response = json.load(f)
                except Exception as e:
                    print(e)
                    break

            answer_y = int(response['message']['y'])
            if self.update_status(answer_y):
                break


class MainWindow:
    def __init__(self, queue):
        self.queue = queue
        self.screen_buffer = {'request_count': 0, 'F_status_count': 0, 'clients': {}, 'max': 0, 'min': 255}
        self.setwondow()
        self.start()

    def setwondow(self):
        self.screen = curses.initscr()
        curses.start_color()
        curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.curs_set(False)
        self.screen.nodelay(True)

    def start(self):
        char = 0
        exit_symbol = [81, 113, 176, 208]
        while char not in exit_symbol:
            char = self.screen.getch()
            # FIXME update if screen_buffer changed or resize window
            self.paint()
            time.sleep(.1)

            # All threads completed, close
            if self.screen_buffer['F_status_count'] == 32:
                break
        signal.alarm(1)
        time.sleep(1)

    def paint(self):
        if not self.queue.empty():
            self.screen_buffer = self.queue.get()

        self.screen.clear()
        self.screen.keypad(1)
        self.screen.border()
        curses.update_lines_cols()

        # satatus processes
        next_pos = 0
        next_row = 0
        for i, clnt in enumerate(self.screen_buffer['clients']):
            X = 0 if self.screen_buffer['clients'][clnt]['count'] > 99 else 1
            if self.screen_buffer['clients'][clnt]['status'] == 'F':
                self.screen.addstr(1 + next_row, 1 + next_pos, " X_X ", curses.color_pair(1))
                self.screen.addstr(2 + next_row, 1 + next_pos,
                                   f"  {self.screen_buffer['clients'][clnt]['status']}  ",
                                   curses.color_pair(1))
                self.screen.addstr(3 + next_row, X + next_pos,
                                   f"  {self.screen_buffer['clients'][clnt]['count']}  ",
                                   curses.color_pair(1))
            else:
                self.screen.addstr(1 + next_row, 1 + next_pos, " O_O ", curses.color_pair(2))
                self.screen.addstr(2 + next_row, 1 + next_pos,
                                   f"  {self.screen_buffer['clients'][clnt]['status']}  ",
                                   curses.color_pair(2))
                self.screen.addstr(3 + next_row, X + next_pos,
                                   f"  {self.screen_buffer['clients'][clnt]['count']}  ",
                                   curses.color_pair(2))

            if (i+1) % 8 == 0:
                next_pos = 0
                next_row += 3
            else:
                next_pos += 5

        self.screen.hline(13, 1, curses.ACS_HLINE, 41)
        self.screen.hline(13, 0, curses.ACS_LTEE, 1)
        self.screen.hline(13, 42, curses.ACS_LRCORNER, 1)
        self.screen.vline(0, 42, curses.ACS_TTEE, 1)

        # server statistics
        self.screen.vline(1, 42, curses.ACS_VLINE, 12)
        # self.screen.vline(0, 59, curses.ACS_TTEE, 1)
        # self.screen.vline(1, 59, curses.ACS_VLINE, 4)
        # self.screen.hline(5, 59, curses.ACS_LRCORNER, 1)
        self.screen.addstr(1, 48, "SERVER")
        self.screen.addstr(2, 45, f"request: {self.screen_buffer['request_count']}")
        if self.screen_buffer['min'] == 255:
            self.screen.addstr(3, 45, "min: -")
        else:
            self.screen.addstr(3, 45, f"min: {self.screen_buffer['min']}")

        if self.screen_buffer['max'] == 0:
            self.screen.addstr(4, 45, "max: -")
        else:
            self.screen.addstr(4, 45, f"max: {self.screen_buffer['max']}")

        self.screen.hline(5, 42, curses.ACS_LTEE, 1)
        self.screen.hline(5, 43, curses.ACS_HLINE, 16)

        self.screen.addstr(6, 45, f"Exit: { 32 - self.screen_buffer['F_status_count']}")

        # diagram
        self.screen.vline(2, 62, curses.ACS_VLINE, 11)
        self.screen.hline(13, 63, curses.ACS_HLINE, 33)
        self.screen.hline(13, 62, curses.ACS_PLUS, 1)

        height = 12
        for i, clnt in enumerate(self.screen_buffer['clients']):
            value = round(self.screen_buffer['clients'][clnt]['count'] / height)
            self.screen.vline(1 + height - value, 63+i, curses.ACS_BOARD, value)

        # Show [Quit]
        self.screen.addstr(curses.LINES-1, 1, "Q", curses.color_pair(3) | curses.A_UNDERLINE)
        self.screen.addstr(curses.LINES-1, 2, "uit", curses.color_pair(3))

        self.screen.move(curses.LINES-1, 1)


def start_clients():
    for th in range(0, 32):
        thread = AutomatThread(th)
        thread.start()


def start_server(queue):
    srv = Server(HOST, PORT, queue)
    srv.run()


def handler(signum, frame):
    print('Signal handler called with signal', signum)
    curses.endwin()
    sys.exit()


if __name__ == '__main__':
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGALRM, handler)
    print("PID:", os.getpid())

    queue = Queue()

    thread = Thread(target=start_server, args=(queue, ), daemon=True)
    thread.start()
    start_clients()
    win = MainWindow(queue)