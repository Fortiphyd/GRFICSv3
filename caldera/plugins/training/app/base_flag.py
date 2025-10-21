from app.utility.base_world import BaseWorld


class BaseFlag:
    """
    A collection of static functions to be used by training flags.
    """

    @staticmethod
    async def does_agent_exist(services, group):
        return len(await services.get('data_svc').locate('agents', match=dict(group=group)))

    @staticmethod
    async def is_operation_started(services, op_name):
        return len(await services.get('data_svc').locate('operations', match=dict(name=op_name)))

    @staticmethod
    async def start_operation(services, op_name, group, adv_id):
        access = dict(access=[BaseWorld.Access.HIDDEN])
        data = dict(name=op_name, group=group, adversary_id=adv_id,
                    planner='batch', auto_close=True)
        await services.get('rest_svc').create_operation(access=access, data=data)

    @staticmethod
    async def is_operation_successful(services, op_name, traits=[], num_links=1):
        operation = (await services.get('data_svc').locate('operations', match=dict(name=op_name)))[0]
        if len(operation.chain) == num_links and \
                all(trait in [f.trait for f in await operation.all_facts()] for trait in traits):
            return True
        return False

    @staticmethod
    async def cleanup_operation(services, op_name):
        await services.get('rest_svc').delete_operation(data=dict(name=op_name))

    @staticmethod
    async def verify_attack_flag(services, technique, adv_name):
        adversaries = await services.get('data_svc').locate('adversaries', match=dict(name=adv_name))
        for adv in adversaries:
            match = await BaseFlag.does_technique_match(services, technique, adv)
            await services.get('rest_svc').delete_adversary(dict(adversary_id=adv.adversary_id))
            if match:
                return True
        return False

    @staticmethod
    async def does_technique_match(services, technique, adversary):
        techniques = set()
        for ab_id in adversary.atomic_ordering:
            techniques.add((await services.get('rest_svc').display_objects('abilities',
                                                                           data=dict(ability_id=ab_id)))[0][
                               'technique_id'])
        return technique in techniques and len(techniques) == 1

    @staticmethod
    async def standard_verify_with_operation(services, operation_name, adversary_id, agent_group, is_flag_satisfied):
        if await BaseFlag.does_agent_exist(services, agent_group):
            if not (await BaseFlag.is_operation_started(services, operation_name)):
                await BaseFlag.start_operation(services, operation_name, agent_group, adversary_id)
            if await BaseFlag.is_operation_successful(services, operation_name) and await is_flag_satisfied():
                await BaseFlag.cleanup_operation(services, operation_name)
                return True
        return False

    @staticmethod
    async def reset(services, operation_name, verify):
        await BaseFlag.cleanup_operation(services, operation_name)
        await verify(services)
