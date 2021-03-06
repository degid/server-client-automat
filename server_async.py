import asyncio
import json
import logging
import os
import random

from utils import Http

HOST = os.environ.get('HOST')
PORT = os.environ.get('PORT')


class Server:
    def __init__(self, server_address, server_port, queue=None):
        self.server_address = server_address
        self.server_port = server_port
        self.queue = queue
        self.screen_buffer = {'request_count': 0, 'F_status_count': 0, 'clients': {}, 'max': 0, 'min': 255}

        self.logger = logging.getLogger("TestAutomat.Server")

    def run(self):
        asyncio.run(self.start())

    async def start(self):
        try:
            server = await asyncio.start_server(self.server_client, self.server_address, self.server_port)
            await server.serve_forever()
        except Exception as e:
            self.logger.error(str(e))

    async def server_client(self, reader, writer):
        cid = self.screen_buffer['request_count']
        self.screen_buffer['request_count'] += 1

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
                self.logger.error(f"405. Method Not Allowed - {match[0]}")
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
                self.logger.error("Content-Length error")
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
            self.logger.error(str(e))
            return Http.E400('Bad Request (body)')
        except Exception as e:
            self.logger.error(str(e))
            return Http.E400('Bad Request')

        if 'x' not in data or 'status' not in data or 'id' not in data:
            return Http.E400('Bad Request (status or x)')

        count = 1
        if data['id'] in self.screen_buffer['clients']:
            count = self.screen_buffer['clients'][data['id']]['count'] + 1
        self.screen_buffer['clients'][data['id']] = {'status': data['status'], 'count': count}

        x = int(data['x'])
        y = x % random.randint(1, 255)
        self.screen_buffer['max'] = max(self.screen_buffer['max'], count)

        if self.screen_buffer['clients'][data['id']]['status'] == 'F':
            self.screen_buffer['min'] = min(self.screen_buffer['min'], count)
            self.screen_buffer['F_status_count'] += 1

        return Http.R200({'x': x, 'y': y})

    async def write_response(self, writer, response, cid):
        if self.queue is not None:
            self.queue.put(self.screen_buffer)

        writer.write(response)
        await writer.drain()
        writer.close()


if __name__ == "__main__":
    srv = Server(HOST, PORT)
    srv.run()
