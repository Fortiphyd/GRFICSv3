from plugins.training.app.c_flag import Flag


class DevelopersFlag1(Flag):
    name = 'Write a new planner'
    challenge = 'Write a planner called "think_hard" that runs each ability in alphabetical order, ' \
                'by the ability name. Then run a new operation using this planner, ' \
                'any group of agents and any profile. At least 10 abilities should run in the operation.'
    extra_info = ''

    async def verify(self, services):
        for op in await services.get('data_svc').locate('operations'):
            if op.finish and op.planner.name == 'think_hard' and len(op.chain) >= 10:
                alphabetical_op = []
                for abilities in op.adversary.atomic_ordering:
                    ability_names = [link.ability.name for link in op.chain if link.ability.ability_id in [a.ability_id for a in abilities]]
                    alphabetical_op.append(all(ability_names[i] <= ability_names[i + 1] for i in range(len(ability_names) - 1)))
                return all(alphabetical_op)
        return False
