import logging

from aiohttp_jinja2 import template

from app.service.auth_svc import for_all_public_methods, check_authorization
from app.utility.base_world import BaseWorld


@for_all_public_methods(check_authorization)
class EmuGUI(BaseWorld):

    def __init__(self, services, name, description):
        self.auth_svc = services.get('auth_svc')
        self.data_svc = services.get('data_svc')
        self.name = name
        self.description = description

        self.log = logging.getLogger('emu_gui')

    @template('emu.html')
    async def splash(self, request):
        return dict()
