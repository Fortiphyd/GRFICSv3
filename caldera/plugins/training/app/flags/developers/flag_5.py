import os
from plugins.training.app.c_flag import Flag


class DevelopersFlag5(Flag):
    name = 'Special payloads'
    challenge = 'Add a new Stockpile payload called train.txt with the contents "i am a test". Mark it as a ' \
                'special payload, so when downloaded through the REST api, the payload should return the file with ' \
                'the text inside reversed each time it is downloaded.'
    extra_info = ''

    async def verify(self, services):
        check1, check2 = False, False
        if os.path.isfile('plugins/stockpile/payloads/train.txt'):
            with open('plugins/stockpile/payloads/train.txt', 'r') as train:
                if 'i am a test' in train.read():
                    _, contents, _ = await services.get('file_svc').get_file(dict(file='train.txt'))
                    if contents == reversed('i am a test'):
                        check1 = True
                    _, contents, _ = await services.get('file_svc').get_file(dict(file='train.txt'))
                    if contents == 'i am a test':
                        check2 = True
        return all([check1, check2])
