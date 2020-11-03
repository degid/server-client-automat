import json
import re
from string import Template
import sys
from time import gmtime, strftime

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
        'message': '',
        'data': strftime("%a, %d %b %Y %H:%M:%S GMT", gmtime())
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
    Status_400 = 'E400'
    POST = 'POST'
    GET = 'GET'

    def HTTP_Response(tmp, data, json_message):
        HTTP = Template(tmp)
        jsdmp = json.dumps(json_message)
        data['length'] = len(jsdmp)
        return HTTP.substitute(data) + jsdmp

    @classmethod
    def date_time_string(self):
        return strftime("%a, %d %b %Y %H:%M:%S GMT", gmtime())

    @classmethod
    def headers(self, code, message, data_time):
        response = responseXXX.copy()
        response['code'] = code
        response['message'] = message
        response['data'] = data_time
        return response

    @classmethod
    def json_body(self, message, data_time):
        body = json_response.copy()
        body['message'] = message
        body['meta']['data'] = data_time
        return body

    @classmethod
    def json_error(self, code, message, data_time=None):
        error = json_errorXXX.copy()
        error['error']['code'] = 400
        error['error']['message'] = message
        error['error']['data'] = Http.date_time_string() if data_time is None else data_time
        return error

    @classmethod
    def E400(self, message=None):
        message = 'Bad Request' if message is None else message
        data_time = Http.date_time_string()

        headers = Http.headers(400, message, data_time)
        json_error = Http.json_error(400, message, data_time)

        return self.HTTP_Response(tmpl, headers, json_error).encode('utf-8')

    @classmethod
    def R200(self, message=None):
        message = 'OK' if message is None else message
        data_time = Http.date_time_string()

        headers = Http.headers(200, 'OK', data_time)
        json_body = Http.json_body(message, data_time)

        return self.HTTP_Response(tmpl, headers, json_body).encode('utf-8')
