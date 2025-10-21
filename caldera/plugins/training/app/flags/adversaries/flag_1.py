from plugins.training.app.c_flag import Flag


class AdversariesFlag1(Flag):
    name = 'Combine adversaries'
    challenge = 'Add the Nosy Neighbor adversary to the Certifiable adversary and save it'
    extra_info = """A TTP is often connected to a series of other TTPs to form an attack. For example, an adversary may
     have a procedure for locating all PDF files on a host. This may be followed by a procedure to exfiltrate all the
     found files. In Caldera, this chain of TTPs being used is considered an adversary."""

    async def verify(self, services):
        for a in await services.get('data_svc').locate('adversaries', dict(name='Certifiable')):
            for ability in a.atomic_ordering:
                if ability == '2fe2d5e6-7b06-4fc0-bf71-6966a1226731':
                    return True
        return False
