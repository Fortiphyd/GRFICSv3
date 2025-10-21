import glob
import json
import os
import uuid
import yaml
from aiohttp import web
from pathlib import Path
import shutil
from subprocess import DEVNULL, PIPE, STDOUT, check_call, Popen, CalledProcessError
import sys

from app.utility.base_service import BaseService
from app.utility.base_world import BaseWorld


class EmuService(BaseService):
    _dynamicically_compiled_payloads = {'sandcat.go-linux', 'sandcat.go-darwin', 'sandcat.go-windows'}
    _emu_config_path = "conf/default.yml"

    def __init__(self):
        self.log = self.add_service('emu_svc', self)
        self.emu_dir = os.path.join('plugins', 'emu')
        self.repo_dir = os.path.join(self.emu_dir, 'data/adversary-emulation-plans')
        self.data_dir = os.path.join(self.emu_dir, 'data')
        self.payloads_dir = os.path.join(self.emu_dir, 'payloads')
        self.required_payloads = set()
        BaseWorld.apply_config('emu', BaseWorld.strip_yml(self._emu_config_path)[0])
        self.evals_c2_host = self.get_config(name='emu', prop='evals_c2_host')
        self.evals_c2_port = self.get_config(name='emu', prop='evals_c2_port')
        self.app_svc = self.get_service('app_svc')
        self.contact_svc = self.get_service('contact_svc')
        if not self.app_svc:
            self.log.error('App svc not found.')
        else:
            self.app_svc.application.router.add_route('POST', '/plugins/emu/beacons', self.handle_forwarded_beacon)

    async def handle_forwarded_beacon(self, request):
        try:
            forwarded_profile = json.loads(await request.read())
            profile = dict()
            profile['paw'] = forwarded_profile.get('guid')
            profile['contact'] = 'http'
            profile['group'] = 'evals'
            if 'platform' in forwarded_profile:
                profile['platform'] = forwarded_profile.get('platform')
            else:
                profile['platform'] = 'evals'
            if 'hostName' in forwarded_profile:
                profile['host'] = forwarded_profile.get('hostName')
            if 'user' in forwarded_profile:
                profile['username'] = forwarded_profile.get('user')
            if 'pid' in forwarded_profile:
                profile['pid'] = forwarded_profile.get('pid')
            if 'ppid' in forwarded_profile:
                profile['ppid'] = forwarded_profile.get('ppid')
            await self.contact_svc.handle_heartbeat(**profile)
            response = 'Successfully processed forwarded beacon with session ID %s' % profile['paw']
            return web.Response(text=response)
        except Exception as e:
            error_msg = 'Server error when processing forwarded beacon: %s' % e
            self.log.error(error_msg)
            raise web.HTTPBadRequest(error_msg)

    async def clone_repo(self, repo_url=None):
        """
        Clone the Adversary Emulation Library repository. You can use a specific url via
        the `repo_url` parameter (eg. if you want to use a fork).
        """
        if not repo_url:
            repo_url = 'https://github.com/center-for-threat-informed-defense/adversary_emulation_library'

        if not os.path.exists(self.repo_dir) or not os.listdir(self.repo_dir):
            self.log.debug('cloning repo %s' % repo_url)
            check_call(['git', 'clone', '--depth', '1', repo_url, self.repo_dir], stdout=DEVNULL, stderr=STDOUT)
            self.log.debug('clone complete')

    async def populate_data_directory(self, library_path=None):
        """
        Populate the 'data' directory with the Adversary Emulation Library abilities.
        """
        if not library_path:
            library_path = os.path.join(self.repo_dir, '*')
        await self._load_adversaries_and_abilities(library_path)
        await self._load_planners(library_path)

    async def decrypt_payloads(self):
        path_crypt_script = os.path.join(self.repo_dir, '*', 'Resources', 'utilities', 'crypt_executables.py')
        for crypt_script in glob.iglob(path_crypt_script):
            plan_path = crypt_script[:crypt_script.rindex('Resources') + len('Resources')]
            self.log.debug('attempting to decrypt plan payloads from %s using %s with the password "malware"',
                           plan_path, crypt_script)
            process = Popen([sys.executable, crypt_script, '-i', plan_path, '-p', 'malware', '--decrypt'], stdout=PIPE)
            with process.stdout:
                for line in iter(process.stdout.readline, b''):
                    if b'[-]' in line:
                        self.log.error(line.decode('UTF-8').rstrip())
                    else:
                        self.log.debug(line.decode('UTF-8').rstrip())
            exit_code = process.wait()
            if exit_code != 0:
                self.log.error(process.stderr)
                raise CalledProcessError(
                    returncode=exit_code,
                    cmd=process.args,
                    stderr=process.stderr
                )

    @staticmethod
    def get_adversary_from_filename(filename):
        base = os.path.basename(filename)
        return os.path.splitext(base)[0]

    """ PRIVATE """

    async def _load_adversaries_and_abilities(self, library_path):
        adv_emu_plan_path = os.path.join(library_path, 'Emulation_Plan', 'yaml', '*.yaml')
        await self._load_object(adv_emu_plan_path, 'abilities', self._ingest_emulation_plan)
        self._store_required_payloads()

    async def _load_planners(self, library_path):
        planner_path = os.path.join(library_path, 'Emulation_Plan', 'yaml', 'planners', '*.yml')
        await self._load_object(planner_path, 'planners', self._ingest_planner)

    async def _load_object(self, search_path, object_name, ingestion_func):
        total, ingested, errors = 0, 0, 0
        for filename in glob.iglob(search_path):
            total_obj, ingested_obj, num_errors = await ingestion_func(filename)
            total += total_obj
            ingested += ingested_obj
            errors += num_errors
        errors_output = f' and ran into {errors} errors' if errors else ''
        self.log.debug(f'Ingested {ingested} {object_name} (out of {total}) from emu plugin{errors_output}')

    async def _ingest_planner(self, filename):
        num_planners, num_ingested, num_errors = 0, 0, 0
        self.log.debug('Ingesting planner at %s', filename)
        try:
            planner_contents = self.strip_yml(filename)[0]
            if self._is_planner(planner_contents):
                num_planners += 1
                planner_id = planner_contents['id']
                target_filename = '%s.yml' % planner_id
                try:
                    self._copy_planner(filename, target_filename)
                    num_ingested += 1
                except IOError as e:
                    self.log.error('Error copying planner file to %s', target_filename, e)
                    num_errors += 1
            else:
                self.log.error('Yaml file %s located in planner directory but does not contain a planner.', filename)
                num_errors += 1
        except Exception as e:
            self.log.error('Error parsing yaml file %s: %s', filename, e)
            num_errors += 1
        return num_planners, num_ingested, num_errors

    def _copy_planner(self, source_path, target_filename):
        planner_dir = os.path.join(self.data_dir, 'planners')
        if not os.path.exists(planner_dir):
            os.makedirs(planner_dir)
        target_path = os.path.join(planner_dir, target_filename)
        shutil.copyfile(source_path, target_path)
        self.log.debug('Copied planner to %s', target_path)

    @staticmethod
    def _is_planner(data):
        return {'id', 'module'}.issubset(set(data.keys()))

    async def _ingest_emulation_plan(self, filename):
        self.log.debug('Ingesting emulation plan at %s', filename)
        emulation_plan = self.strip_yml(filename)[0]
        details = dict()
        for entry in emulation_plan:
            if 'emulation_plan_details' in entry:
                details = entry['emulation_plan_details']
                if not self._is_valid_format_version(entry['emulation_plan_details']):
                    self.log.error('Yaml file %s does not contain emulation plan details', filename)
                    return 0, 0, 1

        if 'adversary_name' not in details:
            self.log.error('Yaml file %s does not contain adversary info', filename)
            return 0, 0, 1

        abilities, adversary_facts, at_total, at_ingested, errors = await self._ingest_abilities(emulation_plan)
        await self._save_adversary(id=details.get('id', str(uuid.uuid4())),
                                   name=details.get('adversary_name', filename),
                                   description=details.get('adversary_description', filename),
                                   abilities=abilities)
        await self._save_source(details.get('adversary_name', filename), adversary_facts)
        return at_total, at_ingested, errors

    async def _ingest_abilities(self, emulation_plan):
        """Ingests the abilities in the emulation plan and returns a tuple representing the following:
            - list of ingested ability IDs to add to the adversary profile
            - list of facts required for the adversary profile
            - total number of abilities from the emulation plan
            - total number of abilities that were successfully ingested
            - number of errors"""
        at_total, at_ingested, errors = 0, 0, 0
        abilities = []
        adversary_facts = []
        for entry in emulation_plan:
            if await self._is_ability(entry):
                at_total += 1
                try:
                    ability_id, ability_facts = await self._save_ability(entry)
                    adversary_facts.extend(ability_facts)
                    abilities.append(ability_id)
                    at_ingested += 1
                except Exception as e:
                    self.log.error(e)
                    errors += 1
        return abilities, adversary_facts, at_total, at_ingested, errors

    @staticmethod
    def _is_valid_format_version(details):
        try:
            return float(details['format_version']) >= 1.0
        except Exception:
            return False

    async def _write_adversary(self, data):
        d = os.path.join(self.data_dir, 'adversaries')

        if not os.path.exists(d):
            os.makedirs(d)

        file_path = os.path.join(d, '%s.yml' % data['id'])
        with open(file_path, 'w') as f:
            f.write(yaml.dump(data))

    async def _save_adversary(self, id, name, description, abilities):
        adversary = dict(
            id=id,
            name=name,
            description='%s (Emu)' % description,
            atomic_ordering=abilities
        )
        await self._write_adversary(adversary)

    @staticmethod
    async def _is_ability(data):
        if {'id', 'platforms'}.issubset(set(data.keys())):
            return True
        return False

    async def _write_ability(self, data):
        d = os.path.join(self.data_dir, 'abilities', data['tactic'])
        if not os.path.exists(d):
            os.makedirs(d)
        file_path = os.path.join(d, '%s.yml' % data['id'])
        with open(file_path, 'w') as f:
            f.write(yaml.dump([data]))

    @staticmethod
    def get_privilege(executors):
        try:
            for ex in executors:
                if 'elevation_required' in ex:
                    return 'Elevated'
                return False
        except Exception:
            return False

    async def _save_ability(self, ab):
        """
        Return True iif an ability was saved.
        """

        ability = dict(
            id=ab.pop('id', str(uuid.uuid4())),
            name=ab.pop('name', ''),
            description=ab.pop('description', ''),
            tactic='-'.join(ab.pop('tactic', '').lower().split(' ')),
            technique=dict(name=ab.get('technique', dict()).get('name'),
                           attack_id=ab.pop('technique', dict()).get('attack_id')),
            repeatable=ab.pop('repeatable', False),
            requirements=ab.pop('requirements', []),
            platforms=ab.pop('platforms')
        )

        privilege = self.get_privilege(ab.get('executors'))
        if privilege:
            ability['privilege'] = privilege
        facts = []

        for platform in ability.get('platforms', dict()).values():
            for executor_details in platform.values():
                self._register_required_payloads(executor_details.get('payloads', []))

        for fact, details in ab.get('input_arguments', dict()).items():
            if details.get('default'):
                facts.append(dict(trait=fact, value=details.get('default')))

        await self._write_ability(ability)
        return ability['id'], facts

    def _register_required_payloads(self, payloads):
        self.required_payloads.update(
            [payload for payload in payloads if payload not in self._dynamicically_compiled_payloads]
        )

    def _store_required_payloads(self):
        self.log.debug('Searching for and storing required payloads.')
        for payload in self.required_payloads:
            copied = False
            found = False
            if os.path.exists(os.path.join(self.payloads_dir, payload)):
                continue
            for path in Path(self.repo_dir).rglob(payload):
                found = True
                target_path = os.path.join(self.payloads_dir, path.name)
                try:
                    shutil.copyfile(path, target_path)
                    copied = True
                    break
                except Exception as e:
                    self.log.error('Failed to copy payload %s to %s: %s.', payload, target_path, e)
            if not found:
                self.log.warn('Could not find payload %s within %s.', payload, self.repo_dir)
            elif not copied:
                self.log.warn('Found payload %s, but could not copy it to the payloads directory.', payload)

    async def _save_source(self, name, facts):
        source = dict(
            id=str(uuid.uuid5(uuid.NAMESPACE_OID, name)),
            name='%s (Emu)' % name,
            facts=await self._unique_facts(facts)
        )
        await self._write_source(source)

    @staticmethod
    async def _unique_facts(facts):
        unique_facts = []
        for fact in facts:
            if fact not in unique_facts:
                unique_facts.append(fact)
        return unique_facts

    async def _write_source(self, data):
        d = os.path.join(self.data_dir, 'sources')

        if not os.path.exists(d):
            os.makedirs(d)

        file_path = os.path.join(d, '%s.yml' % data['id'])
        with open(file_path, 'w') as f:
            f.write(yaml.dump(data))
