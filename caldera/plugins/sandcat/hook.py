from plugins.sandcat.app.sand_gui_api import SandGuiApi
from plugins.sandcat.app.sand_svc import SandService

name = 'Sandcat'
description = 'A custom multi-platform RAT'
address = '/plugin/sandcat/gui'


async def enable(services):
    app = services.get('app_svc').application
    file_svc = services.get('file_svc')
    sand_svc = SandService(services)
    await file_svc.add_special_payload('sandcat.go', sand_svc.dynamically_compile_executable)
    await file_svc.add_special_payload('shared.go', sand_svc.dynamically_compile_library)
    cat_gui_api = SandGuiApi(services=services)
    app.router.add_static('/sandcat', 'plugins/sandcat/static', append_version=True)
    app.router.add_route('GET', '/plugin/sandcat/gui', cat_gui_api.splash)
    await sand_svc.load_sandcat_extension_modules()
