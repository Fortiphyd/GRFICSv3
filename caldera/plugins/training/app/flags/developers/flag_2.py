from plugins.training.app.c_flag import Flag


class DevelopersFlag2(Flag):
    name = 'Bypass authentication'
    challenge = 'Ensure that logging in to Caldera is not required if the browser address is 127.0.0.1'
    extra_info = ''

    async def verify(self, services):
        return '127.0.0.1' in services.get('auth_svc').bypass
