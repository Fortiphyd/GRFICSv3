from plugins.training.app.c_flag import Flag


class AdvancedFlag2(Flag):
    name = 'Add new user'
    challenge = 'Add new red-team user credentials, using "test" as both the username and password.'
    extra_info = (
        'During an adversary emulation operation, multiple users may need access to the Caldera server.\n'
        'This flag requires making direct changes to the configuration file at conf/local.yml. Make sure the server is '
        'turned off before editing this file, or else changes will be overwritten.'
    )

    async def verify(self, services):
        user = services.get('auth_svc').user_map.get('test')
        return user and user.password == 'test' and 'red' in user.permissions
