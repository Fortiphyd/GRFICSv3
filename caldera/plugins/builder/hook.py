from plugins.builder.app.build_svc import BuildService
from app.utility.base_world import BaseWorld
from plugins.builder.app.builder_gui import BuilderGUI

name = 'builder'
description = 'Dynamically compile ability code via docker containers'
address = '/plugin/builder/gui'
access = BaseWorld.Access.RED


async def enable(services):
    environments = BaseWorld.strip_yml('plugins/builder/conf/environments.yml')[0]
    BaseWorld.apply_config('build', environments)
    build_svc = BuildService(services)
    await build_svc.stage_enabled_dockers()

    envs = environments['enabled']
    builder_gui = BuilderGUI(services, name, description, envs)
    app = services.get('app_svc').application
    app.router.add_route('GET', '/plugin/builder/gui', builder_gui.splash)
    app.router.add_route('GET', '/plugin/builder/environment', builder_gui.get_environments)


async def expansion(services):
    await services.get('build_svc').initialize_code_hook_functions()
