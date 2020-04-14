#-*- encoding: utf-8 -*-

"""
About : Code to run as a linux daemon service, interface with it via REST POST
"""

__author__ = "Eduard Florea"
__email__ = "viper6277@gmail.com"
__company__ = ""
__copyright__ = "Copyright (C) 2020 {a}".format(a=__author__)
__credits__ = ""
__license__ = "MIT"
__version__ = 0.03
__lastdate__ = "2020-04-13"

# ----------------------------------------------------------------------------------------------------------------------
#
# Supporting libraries
#

import json
import os
import sqlite3
import time
import threading
import uuid

from http.server import HTTPServer, BaseHTTPRequestHandler
from io import BytesIO
from queue import Queue
from pprint import pprint


# ----------------------------------------------------------------------------------------------------------------------
#
# Support Classes
#

class LocalData(object):

    records = Queue()

    @staticmethod
    def put(data):
        LocalData.records.put(data)

    @staticmethod
    def get():
        return LocalData.records.get()

    @staticmethod
    def empty():
        return LocalData.records.empty()

    @staticmethod
    def qsize():
        return LocalData.records.qsize()


class WebServerConfig(object):

    config = {}

    @staticmethod
    def set_static_directory(directory):
        WebServerConfig.config['Static Files Root'] = directory


class WebServerRoutes(object):

    @staticmethod
    def index():

        """
<!DOCTYPE html>
<html>

<head>
  <title>SLM Process</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="https://www.w3schools.com/w3css/4/w3.css">
</head>

<body>

  <div class="w3-container">

    <h2>Rounded Images</h2>
    <p>The w3-round classes add rounded corners to an image:</p>

    <p>w3-round-small:</p>
    <img src="/images/img_lights.jpg" class="w3-round-small" alt="Norway" style="width:30%">

  </div>

</body>
</html>

        """

        page = '''
<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset='utf-8'>
	<meta name='viewport' content='width=device-width,initial-scale=1'>
	<link rel="stylesheet" href="https://www.w3schools.com/w3css/4/w3.css">

	<title>SLM Process App</title>

	<link rel='icon' type='image/png' href='/images/favicon.png'>
	<link rel='stylesheet' href='/css/global.css'>
	<link rel='stylesheet' href='/app/build/bundle.css'>

	<script defer src='/app/build/bundle.js'></script>
</head>

<body></body>
</html>'''

        return page


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def file_check(self, path):

        allowed_file_types = WebServerConfig.config['Allowed File Types']

        file_found = None

        for aft in allowed_file_types:
            if path.find(aft) != -1:
                # print('found {ff} file !'.format(ff=aft))
                file_found = path
                break

        return file_found

    def get_file(self, file_found):

        sfr = WebServerConfig.config['Static Files Root']

        full_file_path = '{r}{f}'.format(r=sfr, f=file_found)

        file_bytes = False

        try:
            with open(full_file_path, "rb") as f:
                file_bytes = f.read()

        except IOError as error:
            #print(error)
            pass

        finally:
            return file_bytes

    def do_GET(self):

        file_found = self.file_check(self.path)

        if file_found:

            file_bytes = self.get_file(file_found)

            if file_bytes is False:
                self.handle_404()

            else:

                self.send_response(200)
                self.end_headers()
                self.wfile.write(file_bytes)

        else:

            url_list = WebServerConfig.config['URL List']

            if self.path in url_list:



                if 'GET' in url_list[self.path]:

                    self.send_response(200)
                    self.end_headers()

                    page = WebServerRoutes.index()

                    self.wfile.write(page.encode('utf-8'))
                else:
                    self.handle_405()

            else:
                self.handle_404()

    def do_POST(self):

        content_length = int(self.headers['Content-Length'])

        body = self.rfile.read(content_length)

        url_list = WebServerConfig.config['URL List']

        if self.path in url_list:

            if 'POST' in url_list[self.path]:

                if self.headers['Content-Type'] == 'application/json':

                    raw_json = body.decode('utf-8')

                    # Uncomment for testing only
                    # print(raw_json)

                    data_dict = json.loads(raw_json)

                    if 'API Key' in data_dict:

                        received_key = data_dict['API Key']

                        if received_key == WebServerConfig.config['API Key']:
                            record_id = str(uuid.uuid4())

                            data_dict['API Key'] = 'Pass'

                            LocalData.put(
                                {'Timestamp': time.time(),
                                 'Record ID': record_id,
                                 'Data': data_dict})

                self.send_response(200)

                self.end_headers()

                response = BytesIO()

                response.write(b'Your POST request was received, thank you !')

                # response.write(b'Received: ')

                # response.write(body)

                self.wfile.write(response.getvalue())

            else:
                self.handle_405()

        else:
            self.handle_404()

    def handle_404(self):

        self.send_response(404)

        self.end_headers()

        response = BytesIO()

        response.write(b'Page Not Found')

        self.wfile.write(response.getvalue())

    def handle_405(self):

        self.send_response(405)

        self.end_headers()

        response = BytesIO()

        response.write(b'Invalid Method')

        self.wfile.write(response.getvalue())

# ----------------------------------------------------------------------------------------------------------------------
#
# Main Class
#


class SLM_Process(object):

    def __init__(self, config, verbose=False):

        self.verbose = verbose

        if 'Service Run' in config:
            self.service_run = config['Service Run']

        else:
            self.service_run = True

        self.service_state = 'Running'

        self.service_pause_time = 0

        if 'Process Delay' in config:
            self.process_delay = config['Process Delay']
        else:
            # Default is 5 seconds on main loop delay
            self.process_delay = 5

        self.httpd = None

        if 'Agent Port' in config:
            self.agent_port = config['Agent Port']
        else:
            self.agent_port = 12080

        self.start_time = time.time()

        if self.agent_run() is True:
            self.run()

    def set_state(self, state, pause_time=0):

        if state == 'Pause':
            self.service_state = 'Paused'
            self.service_pause_time = pause_time

        elif state == 'Stop':
            self.service_state = 'Stopped'

        elif state == 'Kill':
            self.service_state = 'Stopped'
            self.service_run = False

        elif state == 'Resume':
            self.service_state = 'Running'

        if self.verbose is True:
            print('Service just entered a "{s}" state '.format(s=state))

    # ------------------------------------------------------------------------------------------------------------------

    def agent(self):

        self.httpd = HTTPServer(('localhost', self.agent_port), SimpleHTTPRequestHandler)

        self.httpd.serve_forever()

    def agent_run(self):

        try:

            t = threading.Thread(name="Service_Interface", target=self.agent)

            t.start()

        except Exception as error:
            print(error)
            return False

        else:
            return True

    # ------------------------------------------------------------------------------------------------------------------
    #
    # Application Methods
    #

    def api_cmd(self, request):

        # Uncomment for testing only
        #print(request)

        if 'Data' in request:
            request_data = request['Data']

            operation = request_data['Operation']

            if operation == 'Set State':

                if 'Pause Time' in request_data:
                    self.set_state(request_data['State'], request_data['Pause Time'])
                else:
                    self.set_state(request_data['State'])

            else:
                pass

    # ------------------------------------------------------------------------------------------------------------------

    def run(self):

        while self.service_run is True:

            if self.service_state == 'Running':
                while not LocalData.empty():
                    self.api_cmd(LocalData.get())

            elif self.service_state == 'Paused':
                time.sleep(self.service_pause_time)

            time.sleep(self.process_delay)


# ----------------------------------------------------------------------------------------------------------------------
#
# Main Declaration
#

def main():

    api_key = str(uuid.uuid5(uuid.NAMESPACE_URL, 'Top Secret'))

    # Uncomment for testing only.
    #print(api_key)

    # ------------------------------------------------------------------------------------------------------------------
    #
    # Set the Web Server configuration
    #

    WebServerConfig.config['API Key'] = api_key

    url_list = {
        '/': ['GET'],
        '/api': ['GET', 'POST']
    }

    WebServerConfig.config['URL List'] = url_list

    allowed_file_types = [
        '.css',
        '.gif',
        '.ico',
        '.jpeg',
        '.jpg',
        '.js',
        '.json',
        '.jsp',
        '.map',
        '.png',
        '.webp',
        '.woff2',
    ]

    WebServerConfig.config['Allowed File Types'] = allowed_file_types

    WebServerConfig.set_static_directory('/home/eddief/PycharmProjects/signals_test_code/static')

    # ------------------------------------------------------------------------------------------------------------------

    config = {
        'Service Run': True,
        'Process Delay': 5,
        'Agent Port': 12080,
        'API Key': api_key
    }

    x = SLM_Process(config, verbose=True)


# ----------------------------------------------------------------------------------------------------------------------
#
# Supporting libraries
#

if __name__ == '__main__':
    main()

