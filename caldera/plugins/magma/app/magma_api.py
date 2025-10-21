import json
from aiohttp import web

from app.service.auth_svc import for_all_public_methods, check_authorization


@for_all_public_methods(check_authorization)
class MagmaAPI:

    def __init__(self, services):
        self.services = services
        self.auth_svc = self.services.get('auth_svc')
        self.data_svc = self.services.get('data_svc')

    async def mirror(self, request):
        """
        This sample endpoint mirrors the request body in its response
        """
        request_body = json.loads(await request.read())
        return web.json_response(request_body)
