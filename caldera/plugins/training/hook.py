import os
import glob
from importlib import import_module


from app.utility.base_world import BaseWorld
from plugins.training.app.c_badge import Badge
from plugins.training.app.c_certification import Certification
from plugins.training.app.c_exam import Exam
from plugins.training.app.training_api import TrainingApi

name = 'Training'
description = 'A certification course to become a Caldera SME'
address = '/plugin/training/gui'


async def enable(services):
    data_svc = services.get('data_svc')
    await data_svc.apply('certifications')
    await _load_flags(data_svc)

    training_api = TrainingApi(services)
    app = services.get('app_svc').application
    app.router.add_static('/plugin/training/assets', 'plugins/training/static/', append_version=True)
    app.router.add_route('GET', '/plugin/training/gui', training_api.splash)
    app.router.add_route('GET', '/plugin/training/certs', training_api.retrieve_certs)
    app.router.add_route('POST', '/plugin/training/flags', training_api.retrieve_flags)
    app.router.add_route('POST', '/plugin/training/reset_flag', training_api.reset_flag)

    app.router.add_route(
        'GET',
        '/plugin/training/solution-guides/certificates/{cert_name}/badges/{badge_name}/flags/{flag_name}',
        training_api.flag_solution_guide
    )

    app.router.add_route(
        'GET',
        '/plugin/training/solution-guides/certificates/{cert_name}',
        training_api.certificate_solution_guide
    )


async def expansion(services):
    data_svc = services.get('data_svc')
    await _apply_hidden_access_to_loaded_files(data_svc)


async def _apply_hidden_access_to_loaded_files(data_svc):
    object_types = ['abilities', 'adversaries']
    for obj_typ in object_types:
        for filename in glob.iglob('plugins/training/data/'+obj_typ+'/**/*.yml', recursive=True):
            obj_id = os.path.splitext(os.path.basename(filename))[0]
            if obj_typ == 'abilities':
                match = dict(ability_id=obj_id)
            else:
                match = dict(adversary_id=obj_id)
            objects = await data_svc.locate(obj_typ, match=match)
            for obj in objects:
                obj.access = BaseWorld.Access.HIDDEN


async def _load_flags(data_svc):
    for filename in glob.iglob('plugins/training/data/certifications/**/*.yml', recursive=True):
        for cert in BaseWorld.strip_yml(filename):
            if cert.get('cert_type') and cert.get('cert_type') == 'exam':
                certification = Exam(identifier=cert['id'], name=cert['name'],
                                     description=cert.get('description', 'No description provided'),
                                     access=BaseWorld.Access.APP)
            else:
                certification = Certification(identifier=cert['id'], name=cert['name'],
                                              description=cert.get('description', 'No description provided'),
                                              access=BaseWorld.Access.APP)
            flag_number = 1
            for badge, flags in cert['badges'].items():
                badge = Badge(name=badge)
                for number, module in enumerate(flags):
                    module_name, cls_name = ('plugins.training.app.%s' % module).rsplit('.', 1)
                    flag_subclass = getattr(import_module(module_name), cls_name)
                    badge.flags.append(flag_subclass(number=flag_number))
                    flag_number += 1
                certification.badges.append(badge)
            await data_svc.store(certification)
