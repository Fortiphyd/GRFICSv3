import logging
import asyncio
import os.path
from subprocess import Popen
from ssl import get_server_certificate

from plugins.ssl.app.ssl_gui_api import SslGuiApi

name = 'SSL'
description = 'Run an SSL proxy in front of the server'
address = 'plugin/ssl/gui'


def _read_default_cert():
    default_cert = ''
    with open('plugins/ssl/conf/insecure_certificate.pem', 'r') as f:
        for line in f:
            if 'PRIVATE KEY' in line:
                break
            default_cert += line
    return default_cert


async def _check_using_default_cert():
    await asyncio.sleep(5)
    server_cert = get_server_certificate(('127.0.0.1', 8443))
    default_cert = _read_default_cert()
    if server_cert == default_cert:
        logging.warn('Insecure SSL private key and certificate in use. Consider generating and using your own '
                     'to improve security. Please see documentation.')


async def enable(services):
    app = services.get('app_svc').application
    haproxy_conf = 'plugins/ssl/templates/haproxy.conf'
    user_conf = 'plugins/ssl/conf/haproxy.conf'
    if os.path.isfile(user_conf):
        haproxy_conf = user_conf
    Popen(['haproxy', '-q', '-f', haproxy_conf])
    ssl_gui_api = SslGuiApi(services=services)
    app.router.add_route('GET', '/plugin/ssl/gui', ssl_gui_api.splash)
    loop = asyncio.get_event_loop()
    loop.create_task(_check_using_default_cert())
