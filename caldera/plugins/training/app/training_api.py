import logging

from aiohttp import web
from aiohttp_jinja2 import template

from app.utility.base_service import BaseService
from app.service.auth_svc import for_all_public_methods, check_authorization
from plugins.training.app import errors
from plugins.training.app.base_flag import BaseFlag


@for_all_public_methods(check_authorization)
class TrainingApi(BaseService):

    def __init__(self, services):
        self.auth_svc = services.get('auth_svc')
        self.data_svc = services.get('data_svc')
        self.services = services

    @template('training.html')
    async def splash(self, request):
        access = dict(access=tuple(await self.auth_svc.get_permissions(request)))
        certifications = await self.data_svc.locate('certifications', match=access)
        return dict(certificates=[cert.display for cert in certifications])

    @template('flag_solution_guide.html')
    async def flag_solution_guide(self, request):
        cert_name = request.match_info['cert_name']
        badge_name = request.match_info['badge_name']
        flag_name = request.match_info['flag_name']

        certificate_list = await self.data_svc.locate('certifications', match={'name': cert_name})

        if not certificate_list:
            raise web.HTTPNotFound(text='Certificate does not exist')

        certificate = certificate_list[0]

        try:
            flag = certificate.get_flag(badge_name, flag_name)
        except errors.BadgeDoesNotExist:
            raise web.HTTPNotFound(text='Badge does not exist')
        except errors.FlagDoesNotExist:
            raise web.HTTPNotFound(text='Flag does not exist')

        if not flag.has_solution_guide:
            raise web.HTTPNotFound(text='No solution guide exists for flag')

        return dict(flag=flag)

    @template('certificate_solution_guide.html')
    async def certificate_solution_guide(self, request):
        cert_name = request.match_info['cert_name']
        certificate_list = await self.data_svc.locate('certifications', match={'name': cert_name})

        if not certificate_list:
            raise web.HTTPNotFound(text='Certificate does not exist')

        return dict(certificate=certificate_list[0])

    async def retrieve_flags(self, request):
        data = dict(await request.json())
        answers = {}
        if 'answers' in data.keys():
            answers = data.pop('answers')
        cert = next(c for c in await self.data_svc.locate('certifications', data))
        badges = [badge for badge in cert.badges]
        for flag in [flag for b in badges for flag in b.flags]:
            try:
                if not flag.completed:
                    flag.activate()
                    if hasattr(flag, 'answer'):
                        answer = answers.get(str(flag.number), None)
                        if answer:
                            flag.completed = flag.verify(answer)
                    else:
                        flag.completed = await flag.verify(self.services)
                    if not hasattr(cert, 'cert_type'):
                        break
            except Exception as e:
                logging.error(e)
        return web.json_response(dict(badges=[b.display for b in badges]))

    async def retrieve_certs(self, request):
        access = dict(access=tuple(await self.auth_svc.get_permissions(request)))
        certifications = await self.data_svc.locate('certifications', match=access)
        return web.json_response(dict(certificates=[cert.display for cert in certifications]))

    async def reset_flag(self, request):
        """
        Allows cert takers to reset the latest flag if something went wrong with running the automatic operation.
        We know a flag has a reset capability if it has a field called 'adversary_id'.
        """
        data = await request.json()
        badges = [badge for c in await self.data_svc.locate('certifications', data) for badge in c.badges]
        reset = 0
        for flag in [flag for b in badges for flag in b.flags]:
            try:
                if not flag.completed:
                    if all(field in flag.additional_fields for field in ['adversary_id', 'operation_name']):
                        await BaseFlag.reset(self.services, flag.additional_fields['operation_name'], flag.verify)
                        reset = 1
                    break
            except Exception as e:
                logging.error(e)
        return web.json_response(dict(reset=reset))
