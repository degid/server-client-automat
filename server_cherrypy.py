import cherrypy
import os
import random
from utils import Http

HOST = os.environ.get('HOST')
PORT = os.environ.get('PORT')


class _Cherypy(object):
    def __init__(self, host, port, queue=None):
        cherrypy.server.socket_host = host
        cherrypy.server.socket_port = port

        access_log = cherrypy.log.access_log
        for handler in tuple(access_log.handlers):
            access_log.removeHandler(handler)

        self.queue = queue
        self.screen_buffer = {'request_count': 0, 'F_status_count': 0, 'clients': {}, 'max': 0, 'min': 255}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @cherrypy.tools.json_in()
    def index(self):
        self.screen_buffer['request_count'] += 1

        try:
            data = cherrypy.request.json
        except AttributeError:
            return Http.json_error(400, 'Bad Request')

        if 'x' not in data or 'status' not in data or 'id' not in data:
            return Http.json_error(400, 'Bad Request (status or x)')

        count = 1
        if data['id'] in self.screen_buffer['clients']:
            count = self.screen_buffer['clients'][data['id']]['count'] + 1
        self.screen_buffer['clients'][data['id']] = {'status': data['status'], 'count': count}

        r = random.randint(1, 255)
        y = data['x'] % r
        self.screen_buffer['max'] = max(self.screen_buffer['max'], count)

        if self.screen_buffer['clients'][data['id']]['status'] == 'F':
            self.screen_buffer['min'] = min(self.screen_buffer['min'], count)
            self.screen_buffer['F_status_count'] += 1

        if self.queue is not None:
            self.queue.put(self.screen_buffer)

        json_response = {'message': {'x': data['x'], 'y': y}}
        return json_response


class Server_Cherypy:
    def __init__(self, host, port, queue=None):
        self.host = host
        self.port = port
        self.queue = queue

    def run(self):
        cherrypy.quickstart(_Cherypy(self.host, self.port, self.queue))


if __name__ == '__main__':
    cherrypy.quickstart(_Cherypy(HOST, PORT))
