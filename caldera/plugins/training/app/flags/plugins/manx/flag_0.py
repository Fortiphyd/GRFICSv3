from plugins.training.app.c_flag import Flag


class PluginsManxFlag0(Flag):
    name = 'Manx plugin'

    challenge = (
        'Start a new Manx agent on your localhost. Then send at least 2 commands to it through the '
        'reverse-shell session. Then run a normal operation against the agent using the Check profile.'
    )

    extra_info = (
        'One of the most common activities a red-team operator will attempt to do is gain a reverse-shell '
        'on a compromised host. This type of shell is a persistent (usually via TCP) connection which gives '
        'the operator a terminal experience that is as-if they are sitting behind the keyboard on the remote host.'
    )

    async def verify(self, services):
        check1, check2 = False, False
        for agent in await services.get('data_svc').locate('agents', dict(contact='tcp')):
            history = [entry for entry in services.get('contact_svc').report['websocket'] if entry['paw'] == agent.paw]
            if len(history) > 1:
                check1 = True
            for op in await services.get('data_svc').locate('operations'):
                if op.adversary.adversary_id != '01d77744-2515-401a-a497-d9f7241aac3c':
                    continue
                for op_agent in op.agents:
                    if op_agent.paw == agent.paw and op.finish:
                        check2 = True
                        break
        return all([check1, check2])
