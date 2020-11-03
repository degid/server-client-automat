from flask import Flask, jsonify
from flask import request
import random
import logging
import os

HOST = os.environ.get('HOST')
PORT = os.environ.get('PORT')


class Server_Flask:
    def __init__(self, host, port, queue=None):
        self.host = host
        self.port = port
        self.queue = queue
        self.screen_buffer = {'request_count': 0, 'F_status_count': 0, 'clients': {}, 'max': 0, 'min': 255}

        self.logger = logging.getLogger("TestAutomat.Flask_Server")

        log = logging.getLogger('werkzeug')
        log.disabled = True

    def run(self):
        app = Flask(__name__)

        @app.route("/", methods=['GET', 'POST'])
        def index():
            self.screen_buffer['request_count'] += 1
            if request.method == 'GET':
                msg = {'error': {'code': 400, 'message': 'Only POST'}}
                return jsonify(msg)
            elif request.method == 'POST':
                ct = request.headers.get('Content-Type')
                if ct.find('application/json') != 0:
                    print(ct.find('application/json'))
                    msg = {'error': {'code': 400, 'message': 'Only json'}}
                    return jsonify(msg)
            else:
                msg = {'error': {'code': 405, 'message': 'Method Not Allowed'}}
                return jsonify(msg)

            data = request.get_json(silent=True)
            if data is None:
                msg = {'error': {'code': 400, 'message': 'Bad json'}}
                return jsonify(msg)

            if 'x' not in data or 'status' not in data or 'id' not in data:
                msg = {'error': {'code': 400, 'message': 'Bad Request (status or x)'}}
                return jsonify(msg)

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
            return jsonify(json_response)

        app.run(host=self.host, port=self.port, debug=False)


if __name__ == "__main__":
    srv = Server_Flask(HOST, PORT)
    srv.run()
