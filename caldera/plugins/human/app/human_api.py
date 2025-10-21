import traceback

from aiohttp_jinja2 import template, web

from app.service.auth_svc import for_all_public_methods, check_authorization


@for_all_public_methods(check_authorization)
class HumanApi:

    def __init__(self, services, human_svc):
        self.auth_svc = services.get('auth_svc')
        self.data_svc = services.get('data_svc')
        self.human_svc = human_svc

    @template('human.html')
    async def splash(self, request):
        return dict()

    async def human_workflows(self, request):
        return web.json_response([w.display for w in await self.data_svc.locate('workflows')])

    async def human_humans(self, request):
        return web.json_response([h.display for h in await self.data_svc.locate('humans')])

    async def rest_api(self, request):
        try:
            data = dict(await request.json())
            index = data.pop('index')
            options = dict(
                POST=dict(
                    build_human=lambda d: self.human_svc.build_human(d),
                    load_human=lambda d: self.human_svc.load_humans(d),
                )
            )
            return web.json_response(await options[request.method][index](data))
        except Exception:
            traceback.print_exc()
