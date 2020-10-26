import asyncio
import curses
import json
import os
import random
import signal
import sys
from threading import Thread
import time
import urllib.request

from utils import Http


screen_bofer = {
    'request_count': 0,
    'clients': {},
    'max': 0,
    'min': 255
}

count_F_status = 0


class Server:
    def __init__(self, server_address, server_port):
        self.server_address = server_address
        self.server_port = server_port
        self.counter = 0

    async def start(self):
        server = await asyncio.start_server(self.server_client, self.server_address, self.server_port)
        # print('Server is started')
        await server.serve_forever()

    async def server_client(self, reader, writer):
        cid = self.counter
        self.counter += 1
        screen_bofer['request_count'] = self.counter

        request = await self.read_request(reader)
        response = await self.handle_request(request)
        await self.write_response(writer, response, cid)

    async def read_request(self, reader, delimiter=b'\r\n'):
        while True:
            chunk = await reader.readline()
            if not chunk:
                break

            match = Http.http_re.match(chunk.decode("utf-8"))
            if not match:
                return "E400"

            if match[1] == 'GET':
                return 'GET'
            elif match[1] != 'POST':
                print(match[0], file=sys.stderr)
                return 'E400'  # "E4xx"

            # reading headers
            headers = dict()
            while True:
                chunk = await reader.readuntil(separator=delimiter)
                if chunk == b'\r\n':
                    break
                header = chunk.decode("utf-8").split(":")
                headers[header[0]] = header[1].strip(' \n\r')

            if 'Content-Length' not in headers or headers['Content-Length'] == '0':
                return "E400"

            # reading body
            length_body = int(headers['Content-Length'])
            body = b''
            while length_body:
                chunk = await reader.read(100)
                if not chunk:
                    break

                body += chunk
                length_body -= len(chunk)
                if length_body < 0:
                    return "E400"

            return {'headers': headers, 'body': body}

        return None

    async def handle_request(self, request):
        global count_F_status
        if request == 'E400':
            return Http.E400()
        elif request == 'GET':
            return Http.R200({'msg': 'Only POST'})

        try:
            data = json.loads(request['body'])
        except json.JSONDecodeError as e:
            print(e, file=sys.stderr)
            return Http.E400('Bad Request (body)')

        if 'x' not in data and 'status' in data and 'id' in data:
            return Http.E400('Bad Request (status or x)')

        count = 1
        if data['id'] in screen_bofer['clients']:
            count = screen_bofer['clients'][data['id']]['count'] + 1
        screen_bofer['clients'][data['id']] = {'status': data['status'], 'count': count}

        x = int(data['x'])
        y = x % random.randint(1, 255)
        screen_bofer['max'] = max(screen_bofer['max'], count)

        if screen_bofer['clients'][data['id']]['status'] == 'F':
            screen_bofer['min'] = min(screen_bofer['min'], count)
            count_F_status += 1

        return Http.R200({'x': x, 'y': y})

    async def write_response(self, writer, response, cid):
        writer.write(response)
        await writer.drain()
        writer.close()


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

            with urllib.request.urlopen("http://127.0.0.1:8001", rsp) as f:
                try:
                    response = json.load(f)
                except Exception as e:
                    print(e)
                    break

            answer_y = int(response['message']['y'])
            if self.update_status(answer_y):
                break


class MainWindow:
    def __init__(self):
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
            self.paint()
            time.sleep(.1)

            # All threads completed, close
            if count_F_status == 32:
                break
        signal.alarm(1)
        time.sleep(1)

    def paint(self):
        global count_F_status
        self.screen.clear()
        self.screen.keypad(1)
        self.screen.border()

        # satatus processes
        next_pos = 0
        next_row = 0
        for i, clnt in enumerate(screen_bofer['clients']):
            if screen_bofer['clients'][clnt]['status'] == 'F':
                self.screen.addstr(1 + next_row, 1 + next_pos, " X_X ", curses.color_pair(1))
                self.screen.addstr(2 + next_row, 1 + next_pos, f"  {screen_bofer['clients'][clnt]['status']}  ", curses.color_pair(1))
                self.screen.addstr(3 + next_row, 1 + next_pos, f"  {screen_bofer['clients'][clnt]['count']}  ", curses.color_pair(1))
            else:
                self.screen.addstr(1 + next_row, 1 + next_pos, " O_O ", curses.color_pair(2))
                self.screen.addstr(2 + next_row, 1 + next_pos, f"  {screen_bofer['clients'][clnt]['status']}  ", curses.color_pair(2))
                self.screen.addstr(3 + next_row, 1 + next_pos, f"  {screen_bofer['clients'][clnt]['count']}  ", curses.color_pair(2))

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
        self.screen.addstr(2, 45, f"request: {screen_bofer['request_count']}")
        if screen_bofer['min'] == 255:
            self.screen.addstr(3, 45, "min: -")
        else:
            self.screen.addstr(3, 45, f"min: {screen_bofer['min']}")

        if screen_bofer['max'] == 0:
            self.screen.addstr(4, 45, "max: -")
        else:
            self.screen.addstr(4, 45, f"max: {screen_bofer['max']}")

        self.screen.hline(5, 42, curses.ACS_LTEE, 1)
        self.screen.hline(5, 43, curses.ACS_HLINE, 16)

        self.screen.addstr(6, 45, f"Exit: { 32 - count_F_status}")

        # diagram
        self.screen.vline(2, 62, curses.ACS_VLINE, 11)
        self.screen.hline(13, 63, curses.ACS_HLINE, 33)
        self.screen.hline(13, 62, curses.ACS_PLUS, 1)

        height = 12
        for i, clnt in enumerate(screen_bofer['clients']):
            value = round(screen_bofer['clients'][clnt]['count'] / height)
            self.screen.vline(1 + height - value, 63+i, curses.ACS_BOARD, value)

        # Show [Quit]
        curses.update_lines_cols()
        self.screen.addstr(curses.LINES-1, 1 + next_pos, "Q", curses.color_pair(3) | curses.A_UNDERLINE)
        self.screen.addstr(curses.LINES-1, 2 + next_pos, "uit", curses.color_pair(3))

        self.screen.move(curses.LINES-1, 1)


def start_clients():
    for th in range(0, 32):
        thread = AutomatThread(th)
        thread.start()


def start_server():
    srv = Server('127.0.0.1', 8001)
    asyncio.run(srv.start())


def handler(signum, frame):
    print('Signal handler called with signal', signum)
    curses.endwin()
    sys.exit()


if __name__ == '__main__':
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGALRM, handler)
    print("PID:", os.getpid())
    thread = Thread(target=start_server, daemon=True)
    thread.start()
    start_clients()
    win = MainWindow()
