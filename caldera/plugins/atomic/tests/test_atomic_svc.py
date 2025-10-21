import hashlib
import os
import pytest

from plugins.atomic.app.atomic_svc import AtomicService

DUMMY_PAYLOAD_PATH = '/tmp/dummyatomicpayload'
DUMMY_PAYLOAD_CONTENT = 'Dummy payload content.'
PREFIX_HASH_LENGTH = 6


@pytest.fixture
def atomic_svc():
    return AtomicService()


@pytest.fixture
def generate_dummy_payload():
    with open(DUMMY_PAYLOAD_PATH, 'w') as f:
        f.write(DUMMY_PAYLOAD_CONTENT)
    yield DUMMY_PAYLOAD_PATH
    os.remove(DUMMY_PAYLOAD_PATH)


@pytest.fixture
def multiline_command():
    return '\n'.join([
        'command1',
        'command2',
        'command3',
    ])


@pytest.fixture
def atomic_test():
    return {
        'name': 'Qakbot Recon',
        'auto_generated_guid': '121de5c6-5818-4868-b8a7-8fd07c455c1b',
        'description': 'A list of commands known to be performed by Qakbot',
        'supported_platforms': ['windows'],
        'input_arguments': {
            'recon_commands': {
                'description': 'File that houses commands to be executed',
                'type': 'Path',
                'default': 'PathToAtomicsFolder\\T1016\\src\\qakbot.bat'
                }
            },
        'executor': {
            'command': '#{recon_commands}\n',
            'name':
            'command_prompt'
            }
        }


class TestAtomicSvc:
    def test_svc_config(self, atomic_svc):
        assert atomic_svc.repo_dir == 'plugins/atomic/data/atomic-red-team'
        assert atomic_svc.data_dir == 'plugins/atomic/data'
        assert atomic_svc.payloads_dir == 'plugins/atomic/payloads'

    def test_normalize_windows_path(self):
        assert AtomicService._normalize_path('windows\\test\\path', 'windows') == 'windows/test/path'

    def test_normalize_posix_path(self):
        assert AtomicService._normalize_path('linux/test/path', 'linux') == 'linux/test/path'

    def test_handle_attachment(self, atomic_svc, generate_dummy_payload):
        target_hash = hashlib.md5(DUMMY_PAYLOAD_CONTENT.encode()).hexdigest()
        target_name = target_hash[:PREFIX_HASH_LENGTH] + '_dummyatomicpayload'
        target_path = atomic_svc.payloads_dir + '/' + target_name
        assert atomic_svc._handle_attachment(DUMMY_PAYLOAD_PATH) == target_name
        assert os.path.isfile(target_path)
        with open(target_path, 'r') as f:
            file_data = f.read()
        assert file_data == DUMMY_PAYLOAD_CONTENT

    def test_handle_multiline_command_sh(self, multiline_command):
        target = 'command1; command2; command3'
        assert AtomicService._handle_multiline_commands(multiline_command, 'sh') == target

    def test_handle_multiline_command_cmd(self, multiline_command):
        target = 'command1 && command2 && command3'
        assert AtomicService._handle_multiline_commands(multiline_command, 'cmd') == target

    def test_handle_multiline_command_cmd_comments(self):
        commands = '\n'.join([
            'command1',
            'REM this is a comment',
            ' rem this is another comment',
            'command2',
            ' :: another comment',
            ':: another comment',
            ' @ REM another comment',
            'command3',
            '@rem more comments'
        ])
        want = 'command1 && command2 && command3'
        assert AtomicService._handle_multiline_commands(commands, 'cmd') == want

    def test_handle_multiline_command_shell_comments(self):
        commands = '\n'.join([
            'command1',
            '# comment',
            ' # comment',
            'command2',
            ';# comment',
            '; # comment',
            'echo thisis#notacomment',
            'echo thisis;#a comment',
            'command3 # trailing comment',
            'command4;#trailing comment',
            'command5; #trailing comment',
            'echo "this is # not a comment" # but this is',
            'echo "\'" can you \'"\' handle "complex # quotes" # but still find the comment; #? ##',
        ])
        want = 'command1; command2; echo thisis#notacomment; echo thisis; command3; command4; command5; ' \
            'echo "this is # not a comment"; echo "\'" can you \'"\' handle "complex # quotes"'
        assert AtomicService._handle_multiline_commands(commands, 'sh') == want

    def test_handle_multiline_command_powershell_comments(self):
        commands = '\n'.join([
            'command1',
            '# comment',
            ' # comment',
            'command2',
            ';# comment',
            '; # comment',
            'echo thisis#notacomment',
            'echo thisis;#a comment',
            'command3 # trailing comment',
            'command4;#trailing comment',
            'command5; #trailing comment',
            'echo "this is # not a comment" # but this is',
            'echo "\'" can you \'"\' han`"dle "complex # quotes" # but still find the comment; #? ##',
            'echo `"this is not actually a quote # so this comment should be removed `"',
        ])
        want = 'command1; command2; echo thisis#notacomment; echo thisis; command3; command4; command5; ' \
               'echo "this is # not a comment"; echo "\'" can you \'"\' han`"dle "complex # quotes"; ' \
               'echo `"this is not actually a quote'
        assert AtomicService._handle_multiline_commands(commands, 'psh') == want

    def test_handle_multiline_command_shell_semicolon(self):
        commands = '\n'.join([
            'command1',
            '# comment',
            ' # comment',
            'command2; ',
            'command3 ;',
            'command4;;',
            'command5'
        ])
        want = 'command1; command2; command3 ; command4;; command5'
        assert AtomicService._handle_multiline_commands(commands, 'sh') == want

    def test_handle_multiline_command_shell_loop(self):
        commands = '\n'.join([
            'for port in {1..65535};',
            '# comment',
            ' # comment',
            'do ',
            'innerloopcommand;',
            'innerloopcommand2',
            'done'
        ])
        want = 'for port in {1..65535}; do innerloopcommand; innerloopcommand2; done'
        assert AtomicService._handle_multiline_commands(commands, 'sh') == want

    def test_handle_multiline_command_shell_ifthen(self):
        commands = '\n'.join([
            'if condition; then',
            '# comment',
            ' # comment',
            'innercommand;',
            'innercommand2;',
            'fi'
        ])
        want = 'if condition; then innercommand; innercommand2; fi'
        assert AtomicService._handle_multiline_commands(commands, 'sh') == want

    def test_use_default_inputs(self, atomic_svc, atomic_test):
        platform = 'windows'
        string_to_analyze = '#{recon_commands} -a'
        test = atomic_test
        test['input_arguments']['recon_commands']['default'] = \
            'PathToAtomicsFolder\\T1016\\src\\nonexistent-qakbot.bat'
        got = atomic_svc._use_default_inputs(test=test,
                                                platform=platform,
                                                string_to_analyse=string_to_analyze)
        assert got[0] == 'PathToAtomicsFolder\\T1016\\src\\nonexistent-qakbot.bat -a'
        assert got[1] == []

    def test_use_default_inputs_empty_string(self, atomic_svc, atomic_test):
        platform = 'windows'
        string_to_analyze = ''
        got = atomic_svc._use_default_inputs(test=atomic_test,
                                                platform=platform,
                                                string_to_analyse=string_to_analyze)
        assert got[0] == ''
        assert got[1] == []

    def test_use_default_inputs_nil_valued(self, atomic_svc, atomic_test):
        platform = 'windows'
        string_to_analyze = '#{recon_commands}'
        test = atomic_test
        test['input_arguments']['recon_commands']['default'] = ''
        got = atomic_svc._use_default_inputs(test=test,
                                                platform=platform,
                                                string_to_analyse=string_to_analyze)
        assert got[0] == ''
        assert got[1] == []
