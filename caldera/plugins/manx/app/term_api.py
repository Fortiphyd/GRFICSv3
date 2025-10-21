import os
import pathlib
from shutil import which

from aiohttp import web
from aiohttp_jinja2 import template

from app.utility.base_service import BaseService
from plugins.manx.app.term_svc import TermService


class TermApi(BaseService):

    def __init__(self, services):
        self.auth_svc = services.get('auth_svc')
        self.file_svc = services.get('file_svc')
        self.data_svc = services.get('data_svc')
        self.contact_svc = services.get('contact_svc')
        self.app_svc = services.get('app_svc')
        self.rest_svc = services.get('rest_svc')
        self.term_svc = TermService(services)

    @template('manx.html')
    async def splash(self, request):
        await self.term_svc.socket_conn.tcp_handler.refresh()
        try:
            sessions = [dict(id=s.id, info=a.paw, platform=a.platform, executors=a.executors)
                        for s in self.term_svc.socket_conn.tcp_handler.sessions
                        for a in await self.data_svc.locate('agents', match=dict(paw=s.paw))]
            return dict(sessions=sessions, websocket=self.get_config('app.contact.websocket'))
        except Exception as e:
            print(e)

    async def get_sessions(self, request):
        await self.term_svc.socket_conn.tcp_handler.refresh()
        sessions = [dict(id=s.id, info=a.paw, platform=a.platform, executors=a.executors)
                    for s in self.term_svc.socket_conn.tcp_handler.sessions
                    for a in await self.data_svc.locate('agents', match=dict(paw=s.paw))]
        return web.json_response(dict(sessions=sessions))

    async def sessions(self, request):
        await self.term_svc.socket_conn.tcp_handler.refresh()
        sessions = [dict(id=s.id, info=s.paw) for s in self.term_svc.socket_conn.tcp_handler.sessions]
        return web.json_response(sessions)

    async def get_history(self, request):
        data = dict(await request.json())
        history = [entry for entry in self.contact_svc.report['websocket'] if entry['paw'] == data.get('paw')]
        return web.json_response(history)

    async def get_abilities(self, request):
        data = dict(await request.json())
        abilities = await self.rest_svc.find_abilities(paw=data['paw'])
        return web.json_response(dict(abilities=[a.display for a in abilities]))

    async def dynamically_compile(self, headers):
        name, platform = headers.get('file'), headers.get('platform')
        if which('go') is not None:
            plugin, file_path = await self.file_svc.find_file_path(name)
            ldflags = ['-s', '-w', '-X main.key=%s' % (self.generate_name(size=30),)]
            for param in ['contact', 'socket', 'http']:
                if param in headers:
                    sanitized = self.file_svc.sanitize_ldflag_value(param, headers[param])
                    ldflags.append('-X main.%s=%s' % (param, sanitized))
            output = str(pathlib.Path('plugins/%s/payloads' % plugin).resolve() / ('%s-%s' % (name, platform)))
            build_path, build_file = os.path.split(file_path)
            await self.file_svc.compile_go(platform, output, build_file, ldflags=' '.join(ldflags), build_dir=build_path)
        return await self.app_svc.retrieve_compiled_file(name, platform)
