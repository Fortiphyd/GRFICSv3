import os
import sys
import zipfile
import tarfile

from importlib import import_module

from app.utility.base_service import BaseService
from plugins.human.app.c_human import Human
from plugins.human.app.c_workflow import Workflow


class HumanService(BaseService):

    def __init__(self, services):
        self.file_svc = services.get('file_svc')
        self.data_svc = services.get('data_svc')
        self.log = self.add_service('human_svc', self)
        self.human_dir = os.path.relpath(os.path.join('plugins', 'human'))
        self.pyhuman_path = os.path.join(self.human_dir, 'pyhuman')
        sys.path.insert(0, self.pyhuman_path)  # needed to load relative module paths in pyhuman for workflows

    async def build_human(self, data):
        try:
            _, name = os.path.split(data.pop('name'))
            await self._select_modules_and_compress(modules=data.pop('tasks'), name=name, platform=data.pop('platform'),
                                                    task_interval=data.pop('task_interval'), tasks_per_cluster=data.pop('task_count'),
                                                    task_cluster_interval=data.pop('task_cluster_interval'), extra=data.pop('extra', []))
            return (await self.data_svc.locate('humans', match=dict(name=name)))[0].display
        except Exception as e:
            self.log.error('Error building human. %s' % e)

    async def load_humans(self, data):
        return [h.display for h in await self.data_svc.locate('humans', match=dict(name=data.get('name')))]

    async def load_available_workflows(self):
        root = os.path.join(self.pyhuman_path, 'app', 'workflows')
        for f in os.listdir(root):
            if os.path.isfile(os.path.join(root, f)) and not f[0] == '_':
                await self._load_workflow_module(root, f)

    """ PRIVATE """

    async def _load_workflow_module(self, root, workflow_file):
        module_path = os.path.join(root, workflow_file.split('.')[0]).replace(os.path.sep, '.')
        try:
            module = import_module(module_path)
            workflow_name = getattr(module, 'WORKFLOW_NAME')
            workflow_description = getattr(module, 'WORKFLOW_DESCRIPTION')
            await self.data_svc.store(Workflow(name=workflow_name, description=workflow_description, file=workflow_file))
        except Exception as e:
            self.log.error('Error loading extension=%s, %s' % (module_path, e))

    async def _create_windows_archive(self, payload_path, behaviors, name):
        file_name = name + '.zip'
        win_zip = zipfile.ZipFile(os.path.join(payload_path, file_name), 'w')
        for behavior in behaviors:
            arc_name = os.path.join('app', 'workflows', os.path.basename(behavior))
            win_zip.write(self.pyhuman_path + behavior, arc_name)
        for root, dirs, files in os.walk(os.path.join(self.pyhuman_path, 'data')):
            for file in files:
                arc_name = os.path.join('data', os.path.basename(file))
                win_zip.write(os.path.join(root, file), arc_name)
        for root, dirs, files in os.walk(os.path.join(self.pyhuman_path, 'app', 'utility')):
            for file in files:
                arc_name = os.path.join('app', 'utility', os.path.basename(file))
                win_zip.write(os.path.join(root, file), arc_name)
        win_zip.write(os.path.join(self.pyhuman_path, 'human.py'), 'human.py')
        win_zip.write(os.path.join(self.pyhuman_path, 'requirements.txt'), 'requirements.txt')
        win_zip.close()

    async def _create_unix_archive(self, payload_path, behaviors, name):
        file_name = name + '.tar.gz'
        unix_tar = tarfile.open(os.path.join(payload_path, file_name), 'w:gz')
        unix_tar.add(os.path.join(self.pyhuman_path, 'data'), arcname='data/.')
        unix_tar.add(os.path.join(self.pyhuman_path, 'app', 'utility'), arcname='app/utility/.')
        for behavior in behaviors:
            unix_tar.add(self.pyhuman_path + behavior, arcname=os.path.join('app', 'workflows',
                                                                           os.path.basename(behavior)))
        unix_tar.add(os.path.join(self.pyhuman_path, 'human.py'), arcname='human.py')
        unix_tar.add(os.path.join(self.pyhuman_path, 'requirements.txt'), arcname='requirements.txt')
        unix_tar.close()

    async def _select_modules_and_compress(self, modules, name, platform, task_interval, task_cluster_interval, tasks_per_cluster, extra):
        payload_path = os.path.abspath(os.path.join(self.human_dir, 'payloads'))
        behaviors = []
        behaviors, workflows = await self._append_module_paths(modules, behaviors)
        self.log.debug('Compressing new human: %s' % name)

        if platform == 'windows-psh':
            await self._create_windows_archive(payload_path, behaviors, name)
        else:
            await self._create_unix_archive(payload_path, behaviors, name)

        await self.data_svc.store(Human(name=name, task_interval=task_interval, task_cluster_interval=task_cluster_interval,
                                        tasks_per_cluster=tasks_per_cluster, platform=platform, extra=extra, workflows=workflows))

    async def _append_module_paths(self, modules, behaviors):
        workflows = []
        for sm in modules:
            workflow = await self.data_svc.locate('workflows', match=dict(name=sm))
            behaviors += ['/app/workflows/' + workflow[0].file]
            workflows.append(workflow[0])
        return behaviors, workflows
