from app.utility.base_world import BaseWorld
from plugins.access.app.access_api import AccessApi

name = 'Access'
description = 'A toolkit containing initial access throwing modules'
address = '/plugin/access/gui'
access = BaseWorld.Access.RED


async def enable(services):
    access_api = AccessApi(services=services)
    app = services.get('app_svc').application
    app.router.add_static('/access', 'plugins/access/static', append_version=True)
    app.router.add_route('GET', '/plugin/access/gui', access_api.landing)
    app.router.add_route('POST', '/plugin/access/exploit', access_api.exploit)
    app.router.add_route('POST', '/plugin/access/abilities', access_api.abilities)
    app.router.add_route('POST', '/plugin/access/executor', access_api.executor)
