from plugins.training.app.c_flag import Flag


class AdversariesFlag0(Flag):
    name = 'Create adversary'
    challenge = 'Create a new adversary named "Certifiable" with at least 3 abilities'
    extra_info = """An adversary usually executes their attack in a specific order, one technique at a time. It's
     common to start with discovery - or recon - of what is on the compromised host. Then moving to collection,
     persistence or lateral-movement, an adversary continues on."""

    async def verify(self, services):
        for a in await services.get('data_svc').locate('adversaries', dict(name='Certifiable')):
            return len(a.atomic_ordering) >= 3
        return False
