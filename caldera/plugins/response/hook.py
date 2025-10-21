from app.utility.base_world import BaseWorld
from plugins.response.app.response_svc import ResponseService

name = 'Response'
description = 'An automated incident response plugin'
address = '/plugin/responder/gui'
access = BaseWorld.Access.BLUE


async def enable(services):
    BaseWorld.apply_config('response', BaseWorld.strip_yml('plugins/response/conf/response.yml')[0])
    response_svc = ResponseService(services)
    await services.get('data_svc').apply('processtrees')
    app = services.get('app_svc').application
    app.router.add_route('GET', '/plugin/responder/gui', response_svc.splash)
    app.router.add_route('POST', '/plugin/responder/update', response_svc.update_responder)
    app.router.add_route('GET', '/plugin/responder/adversaries', response_svc.response_adversaries)
    app.router.add_route('GET', '/plugin/responder/abilities', response_svc.response_abilities)

    _register_agent('1837b43e-4fff-46b2-a604-a602f7540469')  # Elasticat agent

    if BaseWorld.get_config('auto_operation_enable', 'response'):
        await response_svc.register_handler(services.get('event_svc'))


async def expansion(services):
    response_svc = services.get('response_svc')
    await response_svc.apply_adversary_config()


def _register_agent(ability_id):
    """
    Registers an agent with caldera -- the agent's launch commands and variations
     will be displayed in the 'Deploy Agent' modal of the web interface.
    """
    agents = set(BaseWorld.get_config(name='agents', prop='deployments'))
    agents.add(ability_id)
    BaseWorld.set_config(name='agents', prop='deployments', value=list(agents))
