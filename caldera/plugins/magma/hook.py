from app.utility.base_world import BaseWorld
from plugins.magma.app.magma_api import MagmaAPI

name = 'Magma'
description = 'Caldera\'s user interface plugin powered by VueJS'
address = '/plugin/magma/gui'
access = BaseWorld.Access.APP

async def enable(services):
    app = services.get('app_svc').application
    magma_api = MagmaAPI(services)
