import curses
import logging
from multiprocessing import Queue
import signal
import sys
from threading import Thread, Event
import time

from clients_urllib import AutomatThread

HOST, PORT = '127.0.0.1', 8001

logger = logging.getLogger("TestAutomat")
logger.setLevel(logging.ERROR)
fh = logging.FileHandler("error.log")
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)


class MainWindow:
    def __init__(self):
        self.queue = Queue()
        self.event_stop_clients = Event()
        self.screen_buffer = {'request_count': 0, 'F_status_count': 0, 'clients': {}, 'max': 0, 'min': 255}
        self.server_object = {'name': ['Test async', 'Flask'], 'select': 0, 'run': False}
        self.set_windows()
        self.loop()

    def set_windows(self):
        self.screen = curses.initscr()
        curses.start_color()
        curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_GREEN)
        curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_CYAN)
        curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.curs_set(False)
        self.screen.nodelay(True)
        self.create_windiws()

        self.f_mesage = 'stcepseR yaP ot F sserP'

    def create_windiws(self):
        self.servers = curses.newwin(len(self.server_object['name'])+2, 31, 5, 37)
        self.servers.bkgd(' ', curses.color_pair(6) | curses.A_BOLD)
        self.win = curses.newwin(5, 30, 5, 7)
        self.win.bkgd(' ', curses.color_pair(4) | curses.A_BOLD)
        self.clients = curses.newwin(14, 42, 1, 1)
        self.clients.bkgd(' ', curses.color_pair(0) | curses.A_BOLD)

    def select_server(self):
        length = ' ' * 26
        self.servers.border()
        self.servers.addstr(0, 8, ' Select server ', curses.color_pair(6))

        for i, server in enumerate(self.server_object['name']):
            line = f'{server}'
            if self.server_object['select'] == i:
                self.servers.addstr(1+i, 2, f' {line}{length[len(line):]}', curses.color_pair(7))
            else:
                self.servers.addstr(1+i, 2, f' {line}{length[len(line):]}', curses.color_pair(6))
        self.servers.noutrefresh()

    def start_server(self, srv):
        srv.run()

    def start_thread(self):
        if self.server_object['select'] == 0:
            from server_async import Server
            srv = Server(HOST, PORT, self.queue)
        elif self.server_object['select'] == 1:
            from server_flask import Server_Flask
            srv = Server_Flask(HOST, PORT, self.queue)

        # run server
        thread = Thread(target=self.start_server, args=(srv, ), daemon=True)
        thread.start()

        # run clients
        for name in range(0, 32):
            thread = AutomatThread(name, HOST, PORT, self.event_stop_clients)
            thread.start()
        self.screen.clear()

    def loop(self):
        curses.update_lines_cols()
        line, cols = curses.LINES, curses.COLS
        char = 0
        exit_symbol = [81, 113, 176, 208, 70, 102, 192, 340]
        while char not in exit_symbol:
            char = self.screen.getch()

            if not self.queue.empty():
                self.screen_buffer = self.queue.get()

            try:
                self.main_window()
                self.clients_window()

                if not self.server_object['run']:
                    if char == curses.KEY_DOWN:
                        self.server_object['select'] += 1
                    elif char == curses.KEY_UP:
                        self.server_object['select'] -= 1
                    self.server_object['select'] %= len(self.server_object['name'])

                    if char == 10:
                        self.server_object['run'] = True
                        self.start_thread()
                    self.select_server()

                # All threads completed, close
                if self.screen_buffer['F_status_count'] == 32:
                    self.f_window()
                elif self.screen_buffer['F_status_count'] > 32:
                    break
            except curses.error as e:
                logger.error(str(e))

            curses.update_lines_cols()
            if curses.COLS != cols or curses.LINES != line:
                line, cols = curses.LINES, curses.COLS
                self.create_windiws()
                self.screen.clear()
                self.clients.clear()
                self.win.clear()
            else:
                curses.doupdate()

            time.sleep(.1)

        # Exit
        self.event_stop_clients.set()
        handler()

    def f_window(self, ):
        self.win.addstr(2, 4, self.f_mesage[::-1], curses.color_pair(4))
        self.win.border()
        self.win.noutrefresh()

    def clients_window(self):
        next_pos, next_row = 0, 0
        for i, clnt in enumerate(self.screen_buffer['clients']):
            X = 0 if self.screen_buffer['clients'][clnt]['count'] > 99 else 1
            if self.screen_buffer['clients'][clnt]['status'] == 'F':
                self.clients.addstr(1 + next_row, 1 + next_pos, " X_X ", curses.color_pair(1))
                self.clients.addstr(2 + next_row, 1 + next_pos,
                                    f"  {self.screen_buffer['clients'][clnt]['status']}  ",
                                    curses.color_pair(1))
                self.clients.addstr(3 + next_row, X + next_pos,
                                    f"  {self.screen_buffer['clients'][clnt]['count']}  ",
                                    curses.color_pair(1))
            else:
                self.clients.addstr(1 + next_row, 1 + next_pos, " O_O ", curses.color_pair(2))
                self.clients.addstr(2 + next_row, 1 + next_pos,
                                    f"  {self.screen_buffer['clients'][clnt]['status']}  ",
                                    curses.color_pair(2))
                self.clients.addstr(3 + next_row, X + next_pos,
                                    f"  {self.screen_buffer['clients'][clnt]['count']}  ",
                                    curses.color_pair(2))

            if (i+1) % 8 == 0:
                next_pos = 0
                next_row += 3
            else:
                next_pos += 5
        self.clients.border()
        self.clients.noutrefresh()

    def draw_line(self):
        pass

    def main_window(self):
        self.screen.keypad(True)

        # server statistics
        self.screen.vline(1, 42, curses.ACS_VLINE, 12)
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

        self.screen.addstr(6, 45, f"Exit: { 32 - self.screen_buffer['F_status_count']} ")

        # diagram
        self.screen.vline(2, 62, curses.ACS_VLINE, 12)
        self.screen.hline(13, 63, curses.ACS_HLINE, 32)
        self.screen.hline(13, 62, curses.ACS_PLUS, 1)

        height = 12
        for i, clnt in enumerate(self.screen_buffer['clients']):
            value = round(self.screen_buffer['clients'][clnt]['count'] / height)
            # FIXME use draw_line()
            if sys.platform != 'linux':
                self.screen.addstr(height - value, 63+i, " ", curses.color_pair(5))
            else:
                self.screen.vline(1 + height - value, 63+i, curses.ACS_BOARD, value)

        self.screen.border()
        # Show [Quit]
        self.screen.addstr(curses.LINES-1, 1, "Q", curses.color_pair(3) | curses.A_UNDERLINE)
        self.screen.addstr(curses.LINES-1, 2, "uit", curses.color_pair(3))

        self.screen.move(curses.LINES-1, 1)
        self.screen.noutrefresh()


def handler(signum=None, frame=None):
    print('Signal handler called with signal', signum)
    curses.endwin()
    sys.exit()


if __name__ == '__main__':
    signal.signal(signal.SIGINT, handler)
    MainWindow()
