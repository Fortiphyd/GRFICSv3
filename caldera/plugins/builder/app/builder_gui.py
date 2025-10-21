import logging

from aiohttp_jinja2 import template
from aiohttp import web

from app.service.auth_svc import for_all_public_methods, check_authorization
from app.utility.base_world import BaseWorld


@for_all_public_methods(check_authorization)
class BuilderGUI(BaseWorld):

    def __init__(self, services, name, description, envs):
        self.auth_svc = services.get('auth_svc')
        self.data_svc = services.get('data_svc')
        self.name = name
        self.description = description
        self.envs = envs

        self.log = logging.getLogger('builder_gui')

    @template('builder.html')
    async def splash(self, request):
        return dict(name=self.name, description=self.description, envs=self.envs)
    
    async def get_environments(self, request):
        # Return a json response of environments
        return web.json_response(self.envs)
