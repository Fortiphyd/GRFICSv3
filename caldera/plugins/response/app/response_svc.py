import asyncio
import json
import uuid
import yaml

from aiohttp import web
from aiohttp_jinja2 import template
from copy import deepcopy

from app.objects.secondclass.c_fact import Fact
from app.objects.c_operation import Operation
from app.objects.c_source import Source
from app.objects.secondclass.c_result import Result
from app.utility.base_service import BaseService
from plugins.response.app.c_processtree import ProcessTree


async def process_elasticsearch_result(data, services):
    operation = await services.get('app_svc').find_op_with_link(data['link_id'])
    if hasattr(operation, 'chain'):
        link = next(filter(lambda l: l.id == data['link_id'], operation.chain))
        if link.executor.name == 'elasticsearch':
            await services.get('response_svc').process_elasticsearch_results(operation, link)


async def handle_link_completed(socket, path, services):
    data = json.loads(await socket.recv())
    paw = data['agent']['paw']
    data_svc = services.get('data_svc')

    await process_elasticsearch_result(data, services)

    agent = await data_svc.locate('agents', match=dict(paw=paw, access=data_svc.Access.RED))
    if agent:
        pid = data['pid']
        op_type = 'hidden' if BaseService.Access(data.get('access')) == BaseService.Access.HIDDEN else 'visible'
        return await services.get('response_svc').respond_to_pid(pid, agent[0], op_type)


class ResponseService(BaseService):

    def __init__(self, services):
        self.log = self.add_service('response_svc', self)
        self.data_svc = services.get('data_svc')
        self.rest_svc = services.get('rest_svc')
        self.agents = []
        self.adversary = None
        self.child_process_ability_id = None
        self.collect_guid_ability_id = None
        self.abilities = []
        self.search_time_range = 600000
        self.ops = dict()

    @template('response.html')
    async def splash(self, request):
        await self.apply_adversary_config()
        return dict(auto_response=self.adversary)

    async def update_responder(self, request):
        data = dict(await request.json())
        self.set_config(name='response', prop='adversary', value=data['adversary_id'])
        await self.apply_adversary_config()
        await self._save_configurations()
        return web.json_response('complete')

    async def response_adversaries(self, request):
        adversaries = [a for a in await self.data_svc.locate('adversaries') if await a.which_plugin() == 'response']
        await self.apply_adversary_config()
        adversaries = [dict(adversary_id=adv.adversary_id, name=adv.name) for adv in adversaries]
        res = dict(adversaries=adversaries, auto_response=self.adversary.adversary_id if self.adversary else None)
        return web.json_response(res)

    async def response_abilities(self, request):
        abilities = [a for a in await self.data_svc.locate('abilities') if await a.which_plugin() == 'response']
        await self.apply_adversary_config()
        res = []
        for ability in abilities:
            res.append(dict(ability_id=ability.ability_id, name=ability.name))
        return web.json_response(res)

    @staticmethod
    async def register_handler(event_svc):
        await event_svc.observe_event(handle_link_completed, exchange='link', queue='completed')

    async def respond_to_pid(self, pid, red_agent, op_type):
        available_agents = await self.get_available_agents(red_agent)
        if not available_agents:
            return

        if op_type not in self.ops or await self.ops[op_type].is_finished():
            source = await self.create_fact_source()
            await self.create_operation(source=source, op_type=op_type)

        total_facts = []
        total_links = []

        for blue_agent in available_agents:
            agent_facts, agent_links = await self.run_abilities_on_agent(blue_agent, str(red_agent.pid), pid, op_type)
            total_facts.extend(agent_facts)
            total_links.extend(agent_links)

    async def process_elasticsearch_results(self, operation, link):
        file_svc = self.get_service('file_svc')
        contact_svc = self.get_service('contact_svc')
        link_output = BaseService.decode_bytes(file_svc.read_result_file(link.id))
        loaded_output = json.loads(link_output)
        for result in loaded_output:

            # Add link
            new_link = deepcopy(link)
            new_link.facts = []
            new_link.relationships = []
            new_link.apply_id(new_link.host)
            operation.chain.append(new_link)
            await self.data_svc.store(operation)

            # Add result for new link
            new_result = Result(
                id=new_link.id,
                output=BaseService.encode_string(json.dumps(result, indent=4)),
                pid=str(link.pid),
                status=str(link.status)
            )
            await contact_svc._save(new_result)

    async def get_available_agents(self, agent_to_match):
        await self.refresh_blue_agents_abilities()
        available_agents = [a for a in self.agents if a.host == agent_to_match.host]

        if not available_agents:
            self.log.debug('No available blue agents to respond to red action')
            return []

        return available_agents

    async def refresh_blue_agents_abilities(self):
        self.agents = await self.data_svc.locate('agents', match=dict(access=self.Access.BLUE))
        await self.apply_adversary_config()
        self.abilities = []
        for a in self.adversary.atomic_ordering:
            if a not in self.abilities:
                self.abilities.append(a)

    async def run_abilities_on_agent(self, blue_agent, red_agent_pid, original_pid, op_type):
        facts = [Fact(trait='host.process.id', value=original_pid),
                 Fact(trait='sysmon.time.range', value=self.search_time_range)]
        links = []
        relationships = []
        for ability_id in self.abilities:
            if ability_id == self.child_process_ability_id:
                depth = self.get_config(prop='child_process_recursion_depth', name='response')
                if not depth:
                    depth = 5
                ability_facts, ability_links, ability_relationships = \
                    await self.find_child_processes(blue_agent, ability_id, original_pid, relationships, op_type, depth)
            else:
                ability_facts, ability_links, ability_relationships = \
                    await self.run_ability_on_agent(blue_agent, red_agent_pid, ability_id, facts, original_pid,
                                                    relationships, op_type)
                if ability_id == self.collect_guid_ability_id:
                    for link in ability_links:
                        await self.add_link_to_process_tree(link, top_level=True)
            links.extend(ability_links)
            facts.extend(ability_facts)
            relationships.extend(ability_relationships)
        return facts, links

    async def find_child_processes(self, blue_agent, ability_id, original_pid, relationships, op_type, depth=5):
        process_tree_links = []
        ability_facts = []
        ability_relationships = []
        parent_guids = [await self._get_original_guid(original_pid, relationships)]
        child_guids = []
        count = 1
        while parent_guids and count <= depth:
            for pguid in parent_guids:
                facts = [Fact(trait='host.process.guid', value=pguid),
                         Fact(trait='sysmon.time.range', value=self.search_time_range)]
                links = await self.rest_svc.task_agent_with_ability(paw=blue_agent.paw, ability_id=ability_id,
                                                                    obfuscator='plain-text', facts=facts)
                await self.save_to_operation(links, op_type)
                await self.wait_for_link_completion(links, blue_agent)
                for link in links:
                    ability_facts.extend(link.facts)
                    ability_relationships.extend(link.relationships)
                    link.pin = int(original_pid)
                child_guids.extend(await self.process_child_process_links(links))
                process_tree_links.extend(links)
            parent_guids = child_guids
            child_guids = []
            count += 1
        return ability_facts, process_tree_links, ability_relationships

    async def process_child_process_links(self, links):
        child_guids = []
        for link in links:
            for rel in link.relationships:
                if rel.edge == 'has_childprocess_guid' and rel.target and rel.target.trait == 'host.process.guid':
                    child_guids.append(rel.target.value)
                    await self.add_link_to_process_tree(link)
                    return child_guids
        return child_guids

    async def add_link_to_process_tree(self, link, top_level=False):
        if top_level:
            pid, guid, parent_guid = await self.get_info_from_top_level_process_link(link)
        else:
            pid, guid, parent_guid = await self.get_info_from_child_process_link(link)
        processtree = await self.data_svc.locate('processtrees', match=dict(host=link.host))
        if not processtree:
            processtree = ProcessTree(link.host)
            await self.data_svc.store(processtree)
        else:
            # we expect only 1 processtree per host
            processtree = processtree[0]
        await processtree.add_processnode(guid, pid, link, parent_guid)

    @staticmethod
    async def get_info_from_top_level_process_link(link):
        parent_guid = None
        pid = None
        guid = None
        for rel in link.relationships:
            if rel.source.trait == 'host.process.id' and rel.edge == 'has_guid' and \
                    rel.target and rel.target.trait == 'host.process.guid':
                pid = int(rel.source.value.strip())
                guid = rel.target.value
        return pid, guid, parent_guid

    @staticmethod
    async def get_info_from_child_process_link(link):
        parent_guid = None
        pid = None
        guid = None
        for rel in link.relationships:
            if rel.source.trait == 'host.process.guid' and rel.edge == 'has_childprocess_id' and \
                    rel.target and rel.target.trait == 'host.process.id':
                if not parent_guid:
                    parent_guid = rel.source.value
                pid = int(rel.target.value.strip())
            elif rel.source.trait == 'host.process.guid' and rel.edge == 'has_childprocess_guid' and \
                    rel.target and rel.target.trait == 'host.process.guid':
                if not parent_guid:
                    parent_guid = rel.source.value
                guid = rel.target.value
        return pid, guid, parent_guid

    async def run_ability_on_agent(self, blue_agent, red_agent_pid, ability_id, agent_facts, original_pid, relationships, op_type):
        links = await self.rest_svc.task_agent_with_ability(paw=blue_agent.paw, ability_id=ability_id,
                                                            obfuscator='plain-text', facts=agent_facts)
        await self.save_to_operation(links, op_type)
        await self.wait_for_link_completion(links, blue_agent)
        ability_facts = []
        ability_relationships = []
        for link in links:
            ability_relationships.extend(link.relationships)
            link.pin = int(original_pid)
            unique_facts = link.facts[1:]
            ability_facts.extend(self._filter_ability_facts(unique_facts, relationships + ability_relationships,
                                                            red_agent_pid, original_pid))
        return ability_facts, links, ability_relationships

    @staticmethod
    async def wait_for_link_completion(links, agent):
        for link in links:
            while not link.finish or link.can_ignore():
                await asyncio.sleep(3)
                if not agent.trusted:
                    break

    @staticmethod
    async def create_fact_source():
        source_id = str(uuid.uuid4())
        source_name = 'blue-pid-{}'.format(source_id)
        return Source(id=source_id, name=source_name, facts=[])

    async def save_to_operation(self, links, op_type):
        await self.update_operation(links, op_type)
        await self.get_service('data_svc').store(self.ops[op_type])

    async def create_operation(self, source, op_type):
        planner = (await self.get_service('data_svc').locate('planners', match=dict(name='batch')))[0]
        await self.get_service('data_svc').store(source)
        blue_op_name = self.get_config(prop='op_name', name='response')
        access = self.Access.BLUE if op_type == 'visible' else self.Access.HIDDEN
        self.ops[op_type] = Operation(name=blue_op_name, agents=self.agents, adversary=self.adversary,
                                      source=source, access=access, planner=planner, state='running',
                                      auto_close=False, jitter='1/4')
        obj = await self.get_service('data_svc').locate('objectives', match=dict(name='default'))
        self.ops[op_type].objective = deepcopy(obj[0])
        self.ops[op_type].set_start_details()

    async def update_operation(self, links, op_type):
        for link in links:
            link.operation = self.ops[op_type].id
            self.ops[op_type].add_link(link)

    async def apply_adversary_config(self):
        blue_adversary = self.get_config(prop='adversary', name='response')
        self.adversary = (await self.data_svc.locate('adversaries', match=dict(adversary_id=blue_adversary)))[0]
        self.search_time_range = self.get_config(prop='search_time_range_msecs', name='response')
        self.child_process_ability_id = self.get_config(prop='child_process_ability', name='response')
        self.collect_guid_ability_id = self.get_config(prop='collect_guid_ability', name='response')

    async def _save_configurations(self):
        with open('plugins/response/conf/response.yml', 'w') as config:
            config.write(yaml.dump(self.get_config(name='response')))

    def _filter_ability_facts(self, unique_facts, relationships, red_pid, original_pid):
        ability_facts = []
        for fact in unique_facts:
            if fact.trait == 'host.process.guid':
                if self._is_child_guid(relationships, red_pid, original_pid, fact):
                    ability_facts.append(fact)
            elif fact.trait == 'host.process.parentguid':
                if self._is_red_agent_guid(relationships, red_pid, fact):
                    ability_facts.append(fact)
            else:
                ability_facts.append(fact)
        return ability_facts

    @staticmethod
    def _is_child_guid(relationships, red_pid, original_pid, fact):
        for r in relationships:
            if r.edge == 'has_parentid' and \
                    (r.target.value.strip() == red_pid or r.target.value.strip() == original_pid) \
                    and r.source.value == fact.value:
                return True
        return False

    @staticmethod
    def _is_red_agent_guid(relationships, red_pid, fact):
        red_guid = [r.target.value for r in relationships if r.source.value.strip() == red_pid].pop()
        return fact.value == red_guid

    @staticmethod
    async def _get_original_guid(original_pid, relationships):
        source_trait = 'host.process.id'
        edge = 'has_guid'
        target_trait = 'host.process.guid'
        for rel in relationships:
            if rel.source.trait == source_trait and rel.source.value == original_pid and \
                    rel.edge and rel.edge == edge and rel.target and rel.target.trait == target_trait:
                return rel.target.value
        return None
