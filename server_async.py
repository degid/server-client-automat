import asyncio
import json
import random
import sys

from utils import Http

screen_bofer = {
    'request_count': 0,
    'F_status_count': 0,
    'clients': {},
    'max': 0,
    'min': 255
}


class Server:
    def __init__(self, server_address, server_port, queue):
        self.server_address = server_address
        self.server_port = server_port
        self.queue = queue
        self.request_count = 0

    def run(self):
        asyncio.run(self.start())

    async def start(self):
        server = await asyncio.start_server(self.server_client, self.server_address, self.server_port)
        # print('Server is started')
        await server.serve_forever()

    async def server_client(self, reader, writer):
        cid = self.request_count
        self.request_count += 1
        screen_bofer['request_count'] = self.request_count

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
                return Http.Status_400

            if match[1] == Http.GET:
                return Http.GET
            elif match[1] != Http.POST:
                print(match[0], file=sys.stderr)
                return Http.Status_400  # "E4xx"

            # reading headers
            headers = dict()
            while True:
                chunk = await reader.readuntil(separator=delimiter)
                if chunk == b'\r\n':
                    break
                header = chunk.decode("utf-8").split(":")
                headers[header[0]] = header[1].strip(' \n\r')

            if 'Content-Length' not in headers or headers['Content-Length'] == '0':
                return Http.Status_400

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
                    return Http.Status_400

            return {'headers': headers, 'body': body}

        return None

    async def handle_request(self, request):
        if request == Http.Status_400:
            return Http.E400()
        elif request == Http.GET:
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
            screen_bofer['F_status_count'] += 1

        self.queue.put(screen_bofer)

        return Http.R200({'x': x, 'y': y})

    async def write_response(self, writer, response, cid):
        writer.write(response)
        await writer.drain()
        writer.close()
