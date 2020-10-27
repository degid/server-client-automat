import curses
from multiprocessing import Queue
import signal
import sys
from threading import Thread
import time

from clients_urllib import AutomatThread
from server_async import Server

HOST, PORT = '127.0.0.1', 8001


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
        curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.curs_set(False)
        self.screen.nodelay(True)
        self.createwin()

        from base64 import b64decode
        self.f_mesage = b64decode("UHJlc3MgRiB0byBQYXkgUmVzcGVjdHM=")

    def createwin(self):
        self.win = curses.newwin(5, 30, 5, 7)
        self.win.bkgd(' ', curses.color_pair(4) | curses.A_BOLD)
        self.clients = curses.newwin(14, 42, 1, 1)
        self.clients.bkgd(' ', curses.color_pair(0) | curses.A_BOLD)

    def start(self):
        curses.update_lines_cols()
        line, cols = curses.LINES, curses.COLS
        char = 0
        exit_symbol = [81, 113, 176, 208, 70, 102, 192, 340]
        while char not in exit_symbol:
            char = self.screen.getch()

            if not self.queue.empty():
                self.screen_buffer = self.queue.get()

            try:
                self.paint()
                self.clients_window()
                # All threads completed, close
                if self.screen_buffer['F_status_count'] == 32:
                    self.f_window()
            except curses.error:
                pass

            curses.update_lines_cols()
            if curses.COLS != cols or curses.LINES != line:
                line, cols = curses.LINES, curses.COLS
                self.createwin()
                self.screen.clear()
                self.clients.clear()
                self.win.clear()
            else:
                curses.doupdate()

            time.sleep(.1)

        signal.alarm(1)
        time.sleep(1)

    def f_window(self, ):
        self.win.addstr(2, 4, self.f_mesage, curses.color_pair(4))
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

    def paint(self):
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

        self.screen.addstr(6, 45, f"Exit: { 32 - self.screen_buffer['F_status_count']}")

        # diagram
        self.screen.vline(2, 62, curses.ACS_VLINE, 11)
        self.screen.hline(13, 63, curses.ACS_HLINE, 33)
        self.screen.hline(13, 62, curses.ACS_PLUS, 1)

        height = 12
        for i, clnt in enumerate(self.screen_buffer['clients']):
            value = round(self.screen_buffer['clients'][clnt]['count'] / height)
            self.screen.vline(1 + height - value, 63+i, curses.ACS_BOARD, value)

        self.screen.border()
        # Show [Quit]
        self.screen.addstr(curses.LINES-1, 1, "Q", curses.color_pair(3) | curses.A_UNDERLINE)
        self.screen.addstr(curses.LINES-1, 2, "uit", curses.color_pair(3))

        self.screen.move(curses.LINES-1, 1)
        self.screen.noutrefresh()


def start_clients():
    for th in range(0, 32):
        thread = AutomatThread(th, HOST, PORT)
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

    queue = Queue()
    thread = Thread(target=start_server, args=(queue, ), daemon=True)
    thread.start()
    start_clients()
    win = MainWindow(queue)
