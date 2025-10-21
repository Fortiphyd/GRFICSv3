from plugins.compass.app.compass_svc import CompassService

name = 'Compass'
description = 'Use the compass to Navigate Caldera'
address = '/plugin/compass/gui'


async def enable(services):
    app = services.get('app_svc').application
    compass_svc = CompassService(services)
    app.router.add_route('POST', '/plugin/compass/layer', compass_svc.generate_layer)
    app.router.add_route('POST', '/plugin/compass/adversary', compass_svc.create_adversary_from_layer)
    app.router.add_route('GET', '/plugin/compass/gui', compass_svc.splash)
