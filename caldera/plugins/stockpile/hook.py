from app.objects.c_obfuscator import Obfuscator
from app.utility.base_world import BaseWorld
from plugins.stockpile.app.stockpile_svc import StockpileService

name = 'Stockpile'
description = 'A stockpile of abilities, adversaries, payloads and planners'
address = '/plugin/stockpile/gui'
access = BaseWorld.Access.APP


async def enable(services):
    stockpile_svc = StockpileService(services)
    services.get('app_svc').application.router.add_route('GET', '/plugin/stockpile/gui', stockpile_svc.splash)
    await services.get('file_svc').add_special_payload('.donut', 'plugins.stockpile.app.donut.donut_handler')
    await stockpile_svc.data_svc.store(
        Obfuscator(name='plain-text',
                   description='Does no obfuscation to any command, instead running it in plain text',
                   module='plugins.stockpile.app.obfuscators.plain_text')
    )
    await stockpile_svc.data_svc.store(
        Obfuscator(name='base64',
                   description='Obfuscates commands in base64',
                   module='plugins.stockpile.app.obfuscators.base64_basic')
    )
    await stockpile_svc.data_svc.store(
        Obfuscator(name='base64jumble',
                   description='Obfuscates commands in base64, then adds characters to evade base64 detection. '
                               'Disclaimer: this may cause duplicate links to run.',
                   module='plugins.stockpile.app.obfuscators.base64_jumble')
    )
    await stockpile_svc.data_svc.store(
        Obfuscator(name='caesar cipher',
                   description='Obfuscates commands through a caesar cipher algorithm, which uses a randomly selected '
                               'shift value.',
                   module='plugins.stockpile.app.obfuscators.caesar_cipher')
    )
    await stockpile_svc.data_svc.store(
        Obfuscator(name='base64noPadding',
                   description='Obfuscates commands in base64, then removes padding',
                   module='plugins.stockpile.app.obfuscators.base64_no_padding')
    )
    await stockpile_svc.data_svc.store(
        Obfuscator(name='steganography',
                   description='Obfuscates commands through image-based steganography',
                   module='plugins.stockpile.app.obfuscators.steganography')
    )
