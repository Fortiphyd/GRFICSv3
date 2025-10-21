import glob
import yaml
import shutil

import asyncio
import pytest

from pathlib import Path, PosixPath
from unittest.mock import patch, call

from app.utility.base_world import BaseWorld
from plugins.emu.app.emu_svc import EmuService


def async_mock_return(to_return):
    mock_future = asyncio.Future()
    mock_future.set_result(to_return)
    return mock_future


@pytest.fixture
def emu_svc():
    return EmuService()


@pytest.fixture
def planner_yaml():
    return [yaml.safe_load('''
---
id: testid
name: Test Planner
description: |
  Test planner
module: plugins.emu.app.test_planner_module
params:
  param_name:
    key1:
      - value1
    key2:
      - value2
ignore_enforcement_modules: []
allow_repeatable_abilities: False
''')]


@pytest.fixture
def not_planner_yaml():
    return [yaml.safe_load('''
---
name: I am a yaml file
value: But I am not a planner
description: something
''')]


@pytest.fixture
def sample_emu_plan():
    return yaml.safe_load('''
- emulation_plan_details:
    id: planid123
    adversary_name: Adversary APTXY
    adversary_description: Adversary description
    attack_version: 8
    format_version: 1.0

# two payloads, 1 input arg
- id: 1-2-3
  name: Ability 1
  description: Desc 1
  tactic: tactic1
  technique:
    attack_id: technique1
    name: technique 1
  cti_source: source1
  procedure_group: procedure1
  procedure_step: step1
  platforms:
    linux:
      sh:
        command: test command
        payloads:
          - payload1A
          - payload1B

  input_arguments:
    arg1:
      description: argdesc1
      type: string
      default: default1

# 1 payload, 2 input arguments, 2 executors
- id: 2-3-4
  name: Ability 2
  description: Desc 2
  tactic: tactic2
  technique:
    attack_id: technique2
    name: technique 2
  cti_source: source2
  procedure_group: procedure2
  procedure_step: step2
  platforms:
    linux:
      sh:
        command: test command
        payloads:
          - payload2A
    windows:
      cmd:
        command: test command

  input_arguments:
    arg1:
      description: argdesc1
      type: string
      default: default1
    arg2:
      description: argdesc2
      type: string
      default: default2

# 0 payloads, 0 input arguments, 2 uploads, cleanup
- id: 3-4-5
  name: Ability 3
  description: Desc 3
  tactic: tactic3
  technique:
    attack_id: technique3
    name: technique 3
  cti_source: source3
  procedure_group: procedure3
  procedure_step: step3
  platforms:
    linux:
      sh:
        command: test command
        uploads:
          - upload1A
          - upload1B
        cleanup: cleanup command
''')


class TestEmuSvc:
    LIBRARY_GLOB_PATH = 'plugins/emu/data/adversary-emulation-plans/*'
    PLANNER_GLOB_PATH = 'plugins/emu/data/adversary-emulation-plans/*/Emulation_Plan/yaml/planners/*.yml'
    PLANNER_PATH = 'plugins/emu/data/adversary-emulation-plans/library1/Emulation_Plan/yaml/planners/test_planner.yml'
    DEST_PLANNER_PATH = 'plugins/emu/data/planners/testid.yml'

    def test_general_svc_creation(self, emu_svc):
        assert emu_svc.emu_dir == 'plugins/emu'
        assert emu_svc.repo_dir == 'plugins/emu/data/adversary-emulation-plans'
        assert emu_svc.data_dir == 'plugins/emu/data'
        assert emu_svc.payloads_dir == 'plugins/emu/payloads'

    async def test_ingest_planner(self, emu_svc, planner_yaml):

        with patch.object(BaseWorld, 'strip_yml', return_value=planner_yaml) as new_strip_yml:
            with patch.object(shutil, 'copyfile', return_value=None) as new_copyfile:
                await emu_svc._ingest_planner(TestEmuSvc.PLANNER_PATH)
        new_strip_yml.assert_called_once_with(TestEmuSvc.PLANNER_PATH)
        new_copyfile.assert_called_once_with(TestEmuSvc.PLANNER_PATH, TestEmuSvc.DEST_PLANNER_PATH)

    async def test_ingest_bad_planner(self, emu_svc, not_planner_yaml):
        with patch.object(BaseWorld, 'strip_yml', return_value=not_planner_yaml) as new_strip_yml:
            with patch.object(shutil, 'copyfile', return_value=None) as new_copyfile:
                await emu_svc._ingest_planner(TestEmuSvc.PLANNER_PATH)
        new_strip_yml.assert_called_once_with(TestEmuSvc.PLANNER_PATH)
        new_copyfile.assert_not_called()

    async def test_load_planners(self, emu_svc, planner_yaml):
        with patch.object(BaseWorld, 'strip_yml', return_value=planner_yaml) as new_strip_yml:
            with patch.object(shutil, 'copyfile', return_value=None) as new_copyfile:
                with patch.object(glob, 'iglob', return_value=[TestEmuSvc.PLANNER_PATH]) as new_iglob:
                    await emu_svc._load_planners(TestEmuSvc.LIBRARY_GLOB_PATH)
        new_iglob.assert_called_once_with(TestEmuSvc.PLANNER_GLOB_PATH)
        new_strip_yml.assert_called_once_with(TestEmuSvc.PLANNER_PATH)
        new_copyfile.assert_called_once_with(TestEmuSvc.PLANNER_PATH, TestEmuSvc.DEST_PLANNER_PATH)

    async def test_load_bad_planners(self, emu_svc, not_planner_yaml):
        with patch.object(BaseWorld, 'strip_yml', return_value=not_planner_yaml) as new_strip_yml:
            with patch.object(shutil, 'copyfile', return_value=None) as new_copyfile:
                with patch.object(glob, 'iglob', return_value=[TestEmuSvc.PLANNER_PATH]) as new_iglob:
                    await emu_svc._load_planners(TestEmuSvc.LIBRARY_GLOB_PATH)
        new_iglob.assert_called_once_with(TestEmuSvc.PLANNER_GLOB_PATH)
        new_strip_yml.assert_called_once_with(TestEmuSvc.PLANNER_PATH)
        new_copyfile.assert_not_called()

    async def test_ingest_abilities(self, emu_svc, sample_emu_plan):
        with patch.object(EmuService, '_write_ability', return_value=async_mock_return(None)) as write_ability:
            abilities, facts, at_total, at_ingested, errors = await emu_svc._ingest_abilities(sample_emu_plan)
        assert write_ability.call_count == 3
        assert abilities == ['1-2-3', '2-3-4', '3-4-5']
        assert facts == [
            dict(trait='arg1', value='default1'),
            dict(trait='arg1', value='default1'),
            dict(trait='arg2', value='default2'),
        ]
        assert at_total == 3
        assert at_ingested == 3
        assert errors == 0
        assert {'payload1A', 'payload1B', 'payload2A'} == emu_svc.required_payloads
        write_ability.assert_has_calls([
            call(dict(
                id='1-2-3', name='Ability 1', description='Desc 1', tactic='tactic1',
                technique=dict(name='technique 1', attack_id='technique1'), repeatable=False, requirements=[],
                platforms=dict(linux=dict(sh=dict(command='test command', payloads=['payload1A', 'payload1B']))),
            )),
            call(dict(
                id='2-3-4', name='Ability 2', description='Desc 2', tactic='tactic2',
                technique=dict(name='technique 2', attack_id='technique2'), repeatable=False, requirements=[],
                platforms=dict(
                    linux=dict(sh=dict(command='test command', payloads=['payload2A'])),
                    windows=dict(cmd=dict(command='test command')),
                ),
            )),
            call(dict(
                id='3-4-5', name='Ability 3', description='Desc 3', tactic='tactic3',
                technique=dict(name='technique 3', attack_id='technique3'), repeatable=False, requirements=[],
                platforms=dict(linux=dict(sh=dict(command='test command', uploads=['upload1A', 'upload1B'],
                                                  cleanup='cleanup command'))),
            )),
        ])

    def test_store_required_payloads(self, emu_svc):
        def _rglob(_, target):
            return [PosixPath('/path/to/' + target), PosixPath('/path2/to/' + target)]

        emu_svc.required_payloads = {'payload1', 'payload2', 'payload3'}
        with patch.object(Path, 'rglob', new=_rglob):
            with patch.object(shutil, 'copyfile', return_value=None) as new_copyfile:
                emu_svc._store_required_payloads()
        assert new_copyfile.call_count == 3
        new_copyfile.assert_has_calls([
            call(PosixPath('/path/to/payload1'), 'plugins/emu/payloads/payload1'),
            call(PosixPath('/path/to/payload2'), 'plugins/emu/payloads/payload2'),
            call(PosixPath('/path/to/payload3'), 'plugins/emu/payloads/payload3'),
        ], any_order=True)

    def test_register_required_payloads(self, emu_svc):
        payloads = ['payload1', 'payload2', 'payload3', 'sandcat.go-darwin', 'sandcat.go-linux', 'sandcat.go-windows']
        want = {'payload1', 'payload2', 'payload3'}
        emu_svc._register_required_payloads(payloads)
        assert emu_svc.required_payloads == want
