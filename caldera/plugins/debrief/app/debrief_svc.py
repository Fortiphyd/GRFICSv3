import logging

from app.utility.base_service import BaseService


class DebriefService(BaseService):
    def __init__(self, services):
        self.services = services
        self.app_svc = services.get('app_svc')
        self.file_svc = services.get('file_svc')
        self.data_svc = services.get('data_svc')
        self.log = logging.getLogger('debrief_svc')

    async def build_steps_d3(self, operation_ids):
        graph_output = dict(nodes=[], links=[])
        id_store = dict(c2=0)
        graph_output['nodes'].append(dict(name="C2 Server", type='c2', label='server', id=0, img='server',
                                          attrs={k: v for k, v in self.get_config().items() if k.startswith('app.')}))

        operations = []
        for op_id in operation_ids:
            operations.append((await self.data_svc.locate('operations', match=dict(id=op_id)))[0])

        agents = [x for xs in map(lambda o: o.agents, operations) for x in xs]
        self._add_agents_to_d3(agents, id_store, graph_output)

        for operation in operations:
            graph_output['nodes'].append(dict(name=operation.name, type='operation', id=op_id, img='operation',
                                              timestamp=self._format_timestamp(operation.created)))
            previous_link_graph_id = None
            for link in operation.chain:
                link_graph_id = id_store['link' + link.unique] = max(id_store.values()) + 1
                graph_output['nodes'].append(dict(type='link', name='link:'+link.unique, id=link_graph_id,
                                                  status=link.status, operation=op_id, img=link.ability.tactic,
                                                  attrs=dict(status=link.status, name=link.ability.name),
                                                  timestamp=self._format_timestamp(link.created)))

                if not previous_link_graph_id:
                    graph_output['links'].append(dict(source=op_id, target=link_graph_id, type='next_link'))
                else:
                    graph_output['links'].append(dict(source=previous_link_graph_id, target=link_graph_id,
                                                      type='next_link'))
                previous_link_graph_id = link_graph_id
                
                agent = next((a for a in agents), None)
                if 'agent' + agent.paw not in id_store.keys():
                    id_store['agent' + agent.paw] = max(id_store.values()) + 1
                graph_output['links'].append(dict(source=id_store['agent' + agent.paw], target=link_graph_id,
                                                  type='next_link'))

            for agent in operation.agents:
                graph_output['links'].append(dict(source=op_id,
                                                  target=id_store['agent' + agent.paw],
                                                  type='has_agent'))
        return graph_output

    async def build_attackpath_d3(self, operation_ids):
        graph_output = dict(nodes=[], links=[])
        id_store = dict(c2=0)
        graph_output['nodes'].append(dict(name="C2 Server", type='c2', label='server', id=0, img='server',
                                          attrs={config: value for config, value in self.get_config().items() if
                                                 config.startswith('app.')}))

        operations = [op for op_id in operation_ids for op in await self.data_svc.locate('operations',
                                                                                         match=dict(id=op_id))]

        agents = [x for xs in map(lambda o: o.agents, operations) for x in xs]
        self._add_agents_to_d3(agents, id_store, graph_output)

        for agent in agents:
            if agent.origin_link_id:
                operation = await self.app_svc.find_op_with_link(agent.origin_link_id)
                if operation in operations:
                    link = next(lnk for lnk in operation.chain if lnk.id == agent.origin_link_id)
                    link_graph_id = id_store['link' + link.unique] = max(id_store.values()) + 1
                    graph_output['nodes'].append(dict(type='link', name=link.ability.technique_name, id=link_graph_id,
                                                      status=link.status, operation=operation.id,
                                                      img=link.ability.tactic,
                                                      attrs=dict(status=link.status, name=link.ability.name),
                                                      timestamp=self._format_timestamp(link.created)))
                    graph_output['links'].append(dict(source=id_store['agent' + link.paw], target=link_graph_id,
                                                      type='next_link'))
                    graph_output['links'].append(dict(source=link_graph_id, target=id_store['agent' + agent.paw],
                                                      type='next_link'))
        return graph_output

    async def build_fact_d3(self, operation_ids):
        graph_output = dict(nodes=[], links=[])
        id_store = dict(default=0)

        for op_id in operation_ids:
            operation = (await self.data_svc.locate('operations', match=dict(id=op_id)))[0]
            graph_output['nodes'].append(dict(name=operation.name, type='operation', id=op_id, img='operation',
                                              timestamp=self._format_timestamp(operation.created)))
            op_nodes, op_links = [], []
            all_facts = await operation.all_facts()
            for fact in all_facts:
                id_store['fact' + fact.unique] = node_id = max(id_store.values()) + 1
                node = dict(name=fact.trait, id=node_id, type='fact', operation=op_id,
                            attrs=self._get_pub_attrs(fact), img='fact',
                            timestamp=fact.created.strftime('%Y-%m-%dT%H:%M:%S'))
                op_nodes.append(node)

                if fact in operation.source.facts:
                    d3_link = dict(source=op_id, target=node_id, type='relationship')
                    op_links.append(d3_link)

            all_relationships = await operation.all_relationships()
            for relationship in all_relationships:
                if relationship.edge and relationship.target.value:
                    d3_link = dict(source=id_store.get('fact' + relationship.source.unique),
                                   target=id_store.get('fact' + relationship.target.unique),
                                   type='relationship')
                    op_links.append(d3_link)

            self._link_nontargeted_facts(op_nodes, op_links, op_id)

            graph_output['nodes'].extend([n for n in op_nodes if n not in graph_output['nodes']])
            graph_output['links'].extend([lnk for lnk in op_links if lnk not in graph_output['links']])

        return graph_output

    async def build_tactic_d3(self, operation_ids):
        return await self._build_prop_d3(operation_ids, 'tactic')

    async def build_technique_d3(self, operation_ids):
        return await self._build_prop_d3(operation_ids, 'technique_name')

    async def _build_prop_d3(self, operation_ids, prop):
        graph_output = dict(nodes=[], links=[])
        id_store = dict(default=0)

        for op_id in operation_ids:
            operation = (await self.data_svc.locate('operations', match=dict(id=op_id)))[0]
            graph_output['nodes'].append(dict(name=operation.name, type='operation', id=op_id, img='operation',
                                              timestamp=self._format_timestamp(operation.created)))
            previous_prop_graph_id = None
            if len(operation.chain) > 0:
                for p, lnks in self._get_by_prop_order(operation.chain, prop):
                    i = max(id_store.values()) + 1
                    prop_graph_id = id_store[prop + p + str(i)] = i
                    p_attrs = {prop: p}
                    p_attrs.update({lnk.unique: lnk.ability.name for lnk in lnks})
                    graph_output['nodes'].append(dict(type=prop, name=p, id=prop_graph_id, operation=op_id,
                                                      attrs=p_attrs, img=p,
                                                      timestamp=self._format_timestamp(lnks[0].created)))

                    if not previous_prop_graph_id:
                        graph_output['links'].append(dict(source=op_id, target=prop_graph_id, type='next_link'))
                    else:
                        graph_output['links'].append(
                            dict(source=previous_prop_graph_id, target=prop_graph_id, type='next_link'))
                    previous_prop_graph_id = prop_graph_id
        return graph_output

    @staticmethod
    def _add_agents_to_d3(agents, id_store, graph_output):
        for agent in agents:
            if 'agent' + agent.unique not in id_store.keys():
                id_store['agent' + agent.unique] = max(id_store.values()) + 1
                node = dict(name=agent.display_name, id=id_store['agent' + agent.unique], group=agent.group,
                            type='agent', img=agent.platform, timestamp=agent.created.strftime('%Y-%m-%dT%H:%M:%S'),
                            attrs=dict(host=agent.host, group=agent.group, platform=agent.platform))
                graph_output['nodes'].append(node)

                link = dict(source=0, target=id_store['agent' + agent.unique], type='agent_contact')
                graph_output['links'].append(link)

    @staticmethod
    def generate_ttps(operations):
        ttps = dict()
        for op in operations:
            for link in op.chain:
                if not link.cleanup:
                    tactic_name = link.ability.tactic
                    if tactic_name not in ttps.keys():
                        ttps[tactic_name] = DebriefService._generate_new_tactic_entry(op, tactic_name, link)
                    else:
                        DebriefService._update_tactic_entry(ttps[tactic_name], op.name, link)
        return dict(sorted(ttps.items()))

    @staticmethod
    def _generate_new_tactic_entry(operation, tactic_name, link):
        return dict(
            name=tactic_name,
            techniques={link.ability.technique_name: link.ability.technique_id},
            steps={operation.name: [link.ability.name]}
        )

    @staticmethod
    def _update_tactic_entry(tactic_entry_dict, op_name, link):
        technique_info = tactic_entry_dict['techniques']
        step_info = tactic_entry_dict['steps']
        if link.ability.technique_name not in technique_info.keys():
            technique_info[link.ability.technique_name] = link.ability.technique_id
        if op_name not in step_info.keys():
            step_info[op_name] = [link.ability.name]
        elif link.ability.name not in step_info[op_name]:
            step_info[op_name].append(link.ability.name)

    @staticmethod
    def _get_pub_attrs(fact):
        filtered_fact = {k: v for k, v in vars(fact).items() if not k.startswith('_')}
        filtered_fact['origin_type'] = filtered_fact['origin_type'].name
        temp = []
        for lnk in filtered_fact['links']:
            temp.append(lnk)
        filtered_fact['links'] = temp
        return filtered_fact

    @staticmethod
    def _get_by_prop_order(chain, prop):
        current = getattr(chain[0].ability, prop)
        ordered = [(current, [chain[0]])]
        for lnk in chain[1:]:
            if getattr(lnk.ability, prop) != current and lnk.cleanup == 0:
                current = getattr(lnk.ability, prop)
                ordered.append((current, [lnk]))
            else:
                next(p for p in ordered if p[0] == current)[1].append(lnk)
        return ordered

    @staticmethod
    def _format_timestamp(timestamp):
        return timestamp.replace(" ", "T")

    @staticmethod
    def _link_nontargeted_facts(op_nodes, op_links, op_id):
        for n in op_nodes:
            target_links = [lnk for lnk in op_links if lnk['target'] == n['id']]
            if not target_links:
                d3_link = dict(source=op_id, target=n['id'], type='relationship')
                op_links.append(d3_link)
