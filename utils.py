import json
from string import Template
import sys
from time import gmtime, strftime
import re

tmpl = (
    'HTTP/1.1 $code $message\r\n'
    'Date: $data\r\n'
    'Server: TestSetver/1.0 ($platform)\r\n'
    'Content-Type: application/json\r\n'
    'Content-Length: $length\r\n'
    '\r\n'
)

responseXXX = {
    'code': 0,
    'message': '',
    'data': strftime("%a, %d %b %Y %H:%M:%S GMT", gmtime()),
    'platform': sys.platform.title(),
    'length': 0
}

json_errorXXX = {
    'error': {
        'code': 0,
        'message': ''
    }
}

json_response = {
    'message': {
        'x': 0,
        'y': 0
    },
    'meta': {
        'data': strftime("%a, %d %b %Y %H:%M:%S GMT", gmtime()),
    }
}


class Http:
    http_re = re.compile(r"^(\w+)\s(.*)\sHTTP\/1.1")

    def HTTP_Response(tmp, data, json_message):
        HTTP = Template(tmp)
        jsdmp = json.dumps(json_message)
        data['length'] = len(jsdmp)
        return HTTP.substitute(data) + jsdmp

    @classmethod
    def E400(self, message=None):
        message = 'Bad Request' if message is None else message

        response = responseXXX.copy()
        response['code'] = 400
        response['message'] = message

        json_error = json_errorXXX.copy()
        json_error['error']['code'] = 400
        json_error['error']['message'] = message

        return self.HTTP_Response(tmpl, response, json_error).encode('utf-8')

    @classmethod
    def R200(self, message=None):
        message = 'OK' if message is None else message

        response = responseXXX.copy()
        response['code'] = 200
        response['message'] = 'OK'

        json_body = json_response.copy()
        json_body['message'] = message

        return self.HTTP_Response(tmpl, response, json_body).encode('utf-8')
