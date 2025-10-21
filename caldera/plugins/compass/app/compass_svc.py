import json
import uuid

from aiohttp import web
from aiohttp_jinja2 import template

from app.service.auth_svc import for_all_public_methods, check_authorization


@for_all_public_methods(check_authorization)
class CompassService:

    def __init__(self, services):
        self.services = services
        self.auth_svc = self.services.get('auth_svc')
        self.data_svc = self.services.get('data_svc')
        self.rest_svc = self.services.get('rest_svc')

    @template('compass.html')
    async def splash(self, request):
        adversaries = [a.display for a in await self.data_svc.locate('adversaries')]
        return dict(adversaries=sorted(adversaries, key=lambda a: a['name']))

    @staticmethod
    def _get_layer_boilerplate(name, description):
        return dict(
            version='3.0',
            name=name,
            description=description,
            domain='mitre-enterprise',
            techniques=[],
            legendItems=[],
            showTacticRowBackground=True,
            tacticRowBackground='#205b8f',
            selectTechniquesAcrossTactics=True,
            selectSubtechniquesWithParent=True,
            gradient=dict(
                colors=[
                    '#ffffff',
                    '#66ff66'
                ],
                minValue=0,
                maxValue=1
            )
        )

    async def _get_all_abilities(self):
        return 'All-Abilities', 'full set of techniques available', [ability.display for ability in await self.services.get('data_svc').locate('abilities')]

    async def _get_adversary_abilities(self, request_body):
        adversary = (await self.rest_svc.display_objects(object_name='adversaries', data=dict(adversary_id=request_body.get('adversary_id'))))[0]
        return adversary['name'], adversary['description'], adversary['atomic_ordering']

    async def generate_layer(self, request):
        request_body = json.loads(await request.read())

        ability_functions = dict(
            adversary=lambda d: self._get_adversary_abilities(d),
            all=lambda d: self._get_all_abilities()
        )
        display_name, description, abilities = await ability_functions[request_body['index']](request_body)

        layer = self._get_layer_boilerplate(name=display_name, description=description)
        for ability in abilities:
            technique = dict(
                techniqueID=ability['technique_id'],
                tactic=ability['tactic'],
                score=1,
                color='',
                comment='',
                enabled=True,
                showSubtechniques=False
            )
            layer['techniques'].append(technique)

        return web.json_response(layer)

    @staticmethod
    def _extract_techniques(request_body):
        techniques = request_body.get('techniques')
        adversary_techniques = set()
        for technique in techniques:
            if technique.get('score', 0) > 0:
                adversary_techniques.add((technique.get('techniqueID'), technique.get('tactic')))
        return adversary_techniques

    async def _build_adversary(self, adversary_techniques):
        atomic_order = []
        unmatched_techniques = []
        for technique_id, tactic in adversary_techniques:
            if tactic:
                abilities = await self.data_svc.locate('abilities', match=dict(technique_id=technique_id,
                                                                               tactic=tactic))
            else:
                abilities = await self.data_svc.locate('abilities', match=dict(technique_id=technique_id))

            if not abilities:
                unmatched_techniques.append(dict(technique_id=technique_id, tactic=tactic))
            for ab in abilities:
                ability = dict(id=ab.ability_id)
                if ability not in atomic_order:
                    atomic_order.append(ability)
        return atomic_order, unmatched_techniques

    @staticmethod
    async def _read_layer(request):
        body = bytes()
        reader = await request.multipart()
        while True:
            field = await reader.next()
            if not field:
                break
            while True:
                chunk = await field.read_chunk()
                if not chunk:
                    break
                body += chunk
        return json.loads(body)

    async def create_adversary_from_layer(self, request):
        """
        Takes a layer file and generates an adversary that matches the selected tactics and techniques.
        Adversary will be constructed into a single atomic list of techniques
        :param request:
        :return:
        """
        try:
            request_body = await self._read_layer(request)
        except json.decoder.JSONDecodeError:
            return web.HTTPBadRequest()
        try:
            adversary_data = dict(id=str(uuid.uuid4()),
                                  name=request_body.get('name'),
                                  description=request_body.get('description', '') + ' (created by compass)')
            adversary_techniques = self._extract_techniques(request_body)
            adversary_data['atomic_ordering'], unmatched_techniques = await self._build_adversary(adversary_techniques)
            adversary = await self.rest_svc.persist_adversary(dict(access=[self.rest_svc.Access.RED]), adversary_data)
            if adversary:
                return web.json_response(dict(unmatched_techniques=sorted(unmatched_techniques, key=lambda x: x['tactic']),
                                              name=request_body.get('name'),
                                              description=request_body.get('description')))
        except Exception as e:
            print(e)
            raise web.HTTPBadRequest()
