from datetime import datetime

from app.objects.c_agent import Agent
from app.objects.c_operation import Operation
from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_link import Link
from app.utility.base_service import BaseService


class GameboardService(BaseService):

    def __init__(self, services):
        self.data_svc = services.get('data_svc')
        self.file_svc = services.get('file_svc')
        self.log = self.add_service('gameboard_svc', self)
        self.blue_op_name_modifier = '_manual_detections'

    async def does_verify_info_match_any_run_link(self, host, technique_id, verify_type, verify_info):
        agents = await self.data_svc.locate('agents', match=dict(host=host, access=BaseService.Access.RED))
        operations = set()
        op_access = BaseService.Access.RED
        operations.update([op for op in (await self.data_svc.locate('operations', match=dict(access=op_access)))
                           if any(agt in op.agents for agt in agents)])
        links_matching_technique_host = [link for op in operations for link in op.chain if
                                         link.ability.technique_id == technique_id and
                                         link.paw in [agent.paw for agent in agents]]
        if verify_type == 'pid':
            link_id = await self._does_pid_match_any_run_link(links_matching_technique_host, verify_info)
        elif verify_type == 'guid':
            link_id = await self._does_guid_match_any_run_link(links_matching_technique_host, verify_info)
        else:
            return None
        return link_id

    async def add_detection(self, verify_type, link_id, blue_op_id):
        red_op, link = await self._find_op_and_link(link_id)
        if blue_op_id:
            blue_op = await self.data_svc.locate('operations', match=dict(id=blue_op_id))
        else:
            blue_op = await self.data_svc.locate('operations',
                                                 dict(name=red_op.name+'_'+str(red_op.id)+self.blue_op_name_modifier))
            if not blue_op:
                blue_op = await self._create_detection_operation(red_op_name=red_op.name, red_op_id=red_op.id,
                                                                 red_op_access=red_op.access)
        if not self._detection_exists(blue_op[0], verify_type, link):
            await self._add_detection_to_operation(op=blue_op[0], link_pid=link.pid, verify_type=verify_type)
            message = 'Detection successfully added for link in operation: '+red_op.name+' - '+str(red_op.start)+'.'
            return red_op.display, blue_op[0].display, message
        message = 'Detection already exists for link in operation: '+red_op.name+' - '+str(red_op.start)+'.'
        return None, None, message

    async def is_link_verified(self, verify_type, link_id):
        blue_ops = await self.data_svc.locate('operations', dict(access=self.Access.BLUE))
        _, link = await self._find_op_and_link(link_id)
        for blue_op in blue_ops:
            if self._detection_exists(blue_op[0], verify_type, link):
                return True
        return False

    """PRIVATE"""

    async def _find_op_and_link(self, link_id):
        operations = await self.get_service('data_svc').locate('operations')
        for op in operations:
            for link in op.chain:
                if link_id == link.id:
                    return op, link
        return None, None

    @staticmethod
    async def _does_pid_match_any_run_link(links, pid):
        for link in links:
            if link.pid == int(pid):
                return link.id
        return False

    async def _does_guid_match_any_run_link(self, links, guid):
        pids = [str(link.pid) for link in links]
        blue_op_name = self.get_config(prop='op_name', name='response')
        auto_collect_ops = await self.data_svc.locate('operations', match=dict(name=blue_op_name))
        for auto_collect in auto_collect_ops:
            for link in auto_collect.chain:
                link_pid = await self._is_guid_found_by_link(link, guid, pids)
                if link_pid:
                    return await self._does_pid_match_any_run_link(links, link_pid)
        return False

    @staticmethod
    async def _is_guid_found_by_link(link, guid, pids):
        for rel in link.relationships:
            if rel.source.trait == 'host.process.id' and rel.source.value in pids and rel.target and \
                    rel.target.trait == 'host.process.guid' and rel.target.value == guid:
                return rel.source.value
        return False

    async def _create_detection_operation(self, red_op_name, red_op_id, red_op_access):
        planner = (await self.get_service('data_svc').locate('planners', match=dict(name='atomic')))[0]
        adversary_id = self.get_config(prop='adversary', name='gameboard')
        adversary = (await self.data_svc.locate('adversaries', match=dict(adversary_id=adversary_id)))[0]
        obj = (await self.data_svc.locate('objectives', match=dict(name='default')))[0]
        agent = Agent(0, 0, 0, paw='gameboard_detection')
        access = self.Access.BLUE
        detection_operation = Operation(name=red_op_name+'_'+str(red_op_id)+self.blue_op_name_modifier, agents=[agent],
                                        adversary=adversary, access=access, planner=planner, group='blue')
        detection_operation.objective = obj
        detection_operation.set_start_details()
        return [await self.data_svc.store(detection_operation)]

    def _detection_exists(self, op, verify_type, red_link):
        detection_ability_id = self.get_config(prop=verify_type + '_ability', name='gameboard')
        for link in op.chain:
            if link.ability.ability_id == detection_ability_id and link.facts and link.facts[0].value == red_link.pid:
                return True
        return False

    async def _add_detection_to_operation(self, op, link_pid, verify_type):
        ability_id = self.get_config(prop=verify_type+'_ability', name='gameboard')
        ability = (await self.data_svc.locate('abilities', match=dict(ability_id=ability_id)))[0]
        link = self._create_and_setup_verification_link(ability, link_pid)
        op.add_link(link)
        self.file_svc.write_result_file(str(link.id), self.encode_string(str(link_pid)))

    def _create_and_setup_verification_link(self, ability, link_pid):
        link = Link(command=None, paw='gameboard_detection', ability=ability, executor=next(ability.executors))
        fact = Fact(trait='host.process.id', value=link_pid)
        link.used.append(fact)
        link.facts.append(fact)
        link.command = self.encode_string('The link with the PID shown below was successfully detected.')
        link.collect = datetime.now()
        link.finish = self.data_svc.get_current_timestamp()
        link.output = True
        link.status = 0
        link.id = link.generate_number()
        link.pin = link_pid
        return link
