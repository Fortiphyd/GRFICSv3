import json
import glob
import hashlib
import os
import re
import shutil
import yaml

from collections import defaultdict
from subprocess import DEVNULL, STDOUT, check_call

from app.utility.base_world import BaseWorld
from app.utility.base_service import BaseService
from app.objects.c_agent import Agent

PLATFORMS = dict(windows='windows', macos='darwin', linux='linux')
EXECUTORS = dict(command_prompt='cmd', sh='sh', powershell='psh', bash='sh')
RE_VARIABLE = re.compile('(#{(.*?)})', re.DOTALL)
PREFIX_HASH_LEN = 6


class ExtractionError(Exception):
    pass


class AtomicService(BaseService):

    def __init__(self):
        self.log = self.add_service('atomic_svc', self)

        # Atomic Red Team attacks don't come with the corresponding tactic (phase name)
        # so we need to create a match between techniques and tactics.
        # This variable is filled by self._populate_dict_techniques_tactics()
        self.technique_to_tactics = defaultdict(list)

        self.atomic_dir = os.path.join('plugins', 'atomic')
        self.repo_dir = os.path.join(self.atomic_dir, 'data/atomic-red-team')
        self.data_dir = os.path.join(self.atomic_dir, 'data')
        self.payloads_dir = os.path.join(self.atomic_dir, 'payloads')
        self.processing_debug = False

    async def clone_atomic_red_team_repo(self, repo_url=None):
        """
        Clone the Atomic Red Team repository. You can use a specific url via
        the `repo_url` parameter (eg. if you want to use a fork).
        """
        if not repo_url:
            repo_url = 'https://github.com/redcanaryco/atomic-red-team.git'

        if not os.path.exists(self.repo_dir) or not os.listdir(self.repo_dir):
            self.log.debug('cloning repo %s' % repo_url)
            check_call(['git', 'clone', '--depth', '1', repo_url, self.repo_dir], stdout=DEVNULL, stderr=STDOUT)
            self.log.debug('clone complete')

    async def populate_data_directory(self, path_yaml=None):
        """
        Populate the 'data' directory with the Atomic Red Team abilities.
        These data will be usable by caldera after importation.
        You can specify where the yaml files to import are located with the `path_yaml` parameter.
        By default, read the yaml files in the atomics/ directory inside the Atomic Red Team repository.
        """
        if not self.technique_to_tactics:
            await self._populate_dict_techniques_tactics()

        if not path_yaml:
            path_yaml = os.path.join(self.repo_dir, 'atomics', '**', 'T*.yaml')

        at_total = 0
        at_ingested = 0
        errors = 0
        for filename in glob.iglob(path_yaml):
            for entries in BaseWorld.strip_yml(filename):
                for test in entries.get('atomic_tests'):
                    at_total += 1
                    try:
                        if await self._save_ability(entries, test):
                            at_ingested += 1
                    except Exception as e:
                        self.log.debug(e)
                        errors += 1

        errors_output = f' and ran into {errors} errors' if errors else ''
        self.log.debug(f'Ingested {at_ingested} abilities (out of {at_total}) from Atomic plugin{errors_output}')

    """ PRIVATE """

    @staticmethod
    def _gen_single_match_tactic_technique(mitre_json):
        """
        Generator parsing the json from 'enterprise-attack.json',
        and returning couples (phase_name, external_id)
        """
        for obj in mitre_json.get('objects', list()):
            if not obj.get('type') == 'attack-pattern':
                continue
            for e in obj.get('external_references', list()):
                if not e.get('source_name') == 'mitre-attack':
                    continue
                external_id = e.get('external_id')
                for kc in obj.get('kill_chain_phases', list()):
                    if not kc.get('kill_chain_name') == 'mitre-attack':
                        continue
                    phase_name = kc.get('phase_name')
                    yield phase_name, external_id

    async def _populate_dict_techniques_tactics(self):
        """
        Populate internal dictionary used to match techniques to corresponding tactics.
        Use the file 'enterprise-attack.json' located in the Atomic Red Team repository.
        """
        enterprise_attack_path = os.path.join(self.repo_dir, 'atomic_red_team', 'enterprise-attack.json')

        with open(enterprise_attack_path, 'r') as f:
            mitre_json = json.load(f)

        for phase_name, external_id in self._gen_single_match_tactic_technique(mitre_json):
            self.technique_to_tactics[external_id].append(phase_name)

    def _handle_attachment(self, attachment_path):
        # attachment_path must be a POSIX path
        payload_name = os.path.basename(attachment_path)
        # to avoid collisions between payloads with the same name
        with open(attachment_path, 'rb') as f:
            h = hashlib.md5(f.read()).hexdigest()
        payload_name = h[:PREFIX_HASH_LEN] + '_' + payload_name
        shutil.copyfile(attachment_path, os.path.join(self.payloads_dir, payload_name), follow_symlinks=False)
        return payload_name

    @staticmethod
    def _normalize_path(path, platform):
        if platform == PLATFORMS['windows']:
            return path.replace('\\', '/')
        return path

    def _catch_path_to_atomics_folder(self, string_to_analyse, platform):
        """
        Catch a path to the atomics/ folder in the `string_to_analyse` variable,
        and handle it in the best way possible. If needed, will import a payload.
        """
        regex = re.compile(r'\$?PathToAtomicsFolder((?:/[^/ \n]+)+|(?:\\[^\\ \n]+)+)')
        payloads = []
        if regex.search(string_to_analyse):
            fullpath, path = regex.search(string_to_analyse).group(0, 1)
            path = self._normalize_path(path, platform)

            # take path from index 1, as it starts with /
            path = os.path.join(self.repo_dir, 'atomics', path[1:])

            if os.path.isfile(path):
                payload_name = self._handle_attachment(path)
                payloads.append(payload_name)
                string_to_analyse = string_to_analyse.replace(fullpath, payload_name)

        return string_to_analyse, payloads

    def _has_reserved_parameter(self, command):
        return any(reserved in command for reserved in Agent.RESERVED)

    def _use_default_inputs(self, test, platform, string_to_analyse):
        """
        Look if variables are used in `string_to_analyse`, and if any variable was given
        a default value, use it.
        """

        payloads = []
        defaults = dict((key, val) for key, val in test.get('input_arguments', dict()).items())
        if self._has_reserved_parameter(string_to_analyse):
            return string_to_analyse, payloads
        while RE_VARIABLE.search(string_to_analyse):
            full_var_str, varname = RE_VARIABLE.search(string_to_analyse).groups()
            default_var = str(defaults.get(varname, dict()).get('default'))

            if default_var is not None:
                default_var, new_payloads = self._catch_path_to_atomics_folder(default_var, platform)
                payloads.extend(new_payloads)
                string_to_analyse = string_to_analyse.replace(full_var_str, default_var)

        return string_to_analyse, payloads

    @staticmethod
    def _handle_multiline_commands(cmd, executor):
        command_lines = cmd.strip().split("\n")
        if executor == 'cmd':
            return ' && '.join(AtomicService._remove_dos_comment_lines(command_lines))
        else:
            return AtomicService._concatenate_shell_commands(AtomicService._remove_shell_comments(command_lines,
                                                                                                  executor))

    @staticmethod
    def _concatenate_shell_commands(command_lines):
        """Concatenate multiple shell command lines. The ; character won't be added at the end of each command if the
        command line ends in "then" or "do" or already ends with a ; character."""
        to_concat = []
        num_lines = len(command_lines)
        for index, cmd in enumerate(command_lines):
            to_concat.append(cmd)
            if re.search(r'do\s*$', cmd) or re.search(r'then\s*$', cmd) or re.search(r';\s*$', cmd):
                if not re.search(r'\s+$', cmd):
                    to_concat.append(' ')
            elif index < num_lines - 1:
                to_concat.append('; ')
        return ''.join(to_concat)

    @staticmethod
    def _remove_dos_comment_lines(command_lines):
        """Remove lines that start with REM or :: comments for Windows DOS cmd. Does not handle trailing comments."""
        def _starts_with_comment(line):
            return re.match(r'^\s*@?\s*rem\s+', line, re.IGNORECASE) or re.match(r'^\s*::\s+', line, re.IGNORECASE)

        return [line for line in command_lines if not _starts_with_comment(line)]

    @staticmethod
    def _remove_shell_comments(command_lines, executor):
        """Remove lines that start with a # comment. Also remove trailing comments."""
        def _starts_with_comment(line):
            return re.match(r'^\s*#', line)

        def _remove_escaped_quotes(line):
            regex = r'`("|\')' if executor == 'psh' else r'\\(\'|")'
            return re.sub(regex, '', line)

        def _index_within_completed_quotes_and_contents(line, index):
            start_index = 0
            while start_index < len(line) and start_index <= index:
                to_process = line[start_index:]
                quote_match = re.search(r'\'|"', to_process)
                if not quote_match:
                    return False
                start_quote_index = quote_match.start()
                first_quote_char = to_process[start_quote_index]
                quote_matches = list(re.finditer(first_quote_char, to_process))
                if len(quote_matches) > 1:
                    closing_quote_index = quote_matches[1].start()
                    if start_quote_index + start_index <= index <= closing_quote_index + start_index:
                        return True
                    else:
                        start_index = closing_quote_index + start_index + 1
                else:
                    # Unbalanced quotes. Since line only goes up to the start of the comment,
                    # the comment must be inside quotes.
                    return True
            return False

        def _remove_trailing_comment(line):
            trailing_comment_regex = r'(;|\s)\s*#'
            for match in re.finditer(trailing_comment_regex, line):
                # Check if the trailing comment is actually part of a closed quote group
                removed_escaped_quotes = _remove_escaped_quotes(line[0:match.end()])
                if not _index_within_completed_quotes_and_contents(removed_escaped_quotes, match.start()):
                    return line[0:match.start()]
            return line

        ret_lines = []
        for command_line in command_lines:
            if not _starts_with_comment(command_line):
                processed = _remove_trailing_comment(command_line)
                if processed:
                    ret_lines.append(processed)
        return ret_lines

    async def _prepare_cmd(self, test, platform, executor, cmd):
        """
        Handle a command or a cleanup (both are formatted the same way), given in `cmd`.
        Return the cmd formatted as needed and payloads we need to take into account.
        """
        payloads = []
        cmd, new_payloads = self._use_default_inputs(test, platform, cmd)
        payloads.extend(new_payloads)
        cmd, new_payloads = self._catch_path_to_atomics_folder(cmd, platform)
        payloads.extend(new_payloads)
        cmd = self._handle_multiline_commands(cmd, executor)
        return cmd, payloads

    async def _prepare_executor(self, test, platform, executor):
        """
        Prepare the command and cleanup, and return them with the needed payloads.
        """
        payloads = []
        dep_construct = ""
        if 'dependencies' in test:
            for dependence in test['dependencies']:
                try:
                    test_exc = test.get('dependency_executor_name', executor)
                    dep_construct = await self._prereq_formater(dependence.get('prereq_command', ''),
                                                                dependence.get('get_prereq_command', ''),
                                                                test_exc,
                                                                executor,
                                                                dep_construct)
                except ExtractionError:
                    self.log.debug(f'Skipping pre-req for "{test["name"]}"')
        precmd = f"{dep_construct} \n {test['executor']['command']}" if dep_construct else test['executor']['command']
        command, payloads_command = await self._prepare_cmd(test, platform, executor, precmd)
        cleanup, payloads_cleanup = await self._prepare_cmd(test, platform, executor,
                                                            test['executor'].get('cleanup_command', ''))
        payloads.extend(payloads_command)
        payloads.extend(payloads_cleanup)

        return command, cleanup, payloads

    async def _save_ability(self, entries, test):
        """
        Return True if an ability was saved.
        """
        ability_id = hashlib.md5(json.dumps(test).encode()).hexdigest()

        tactics_li = self.technique_to_tactics.get(entries['attack_technique'], ['redcanary-unknown'])
        tactic = 'multiple' if len(tactics_li) > 1 else tactics_li[0]

        data = dict(
            id=ability_id,
            name=test['name'],
            description=test['description'],
            tactic=tactic,
            technique=dict(
                attack_id=entries['attack_technique'],
                name=entries['display_name']
            ),
            platforms=dict()
        )
        for p in test['supported_platforms']:
            if test['executor']['name'] != 'manual':
                # manual tests are expected to be run manually by a human, no automation is provided
                executor = EXECUTORS.get(test['executor']['name'], 'unknown')
                platform = PLATFORMS.get(p, 'unknown')

                command, cleanup, payloads = await self._prepare_executor(test, platform, executor)
                data['platforms'][platform] = dict()
                data['platforms'][platform][executor] = dict(command=command, payloads=payloads, cleanup=cleanup)
                if executor == 'psh':
                    data['platforms'][platform][executor]['parsers'] = {'plugins.atomic.app.parsers.atomic_powershell':
                                                                        [{'source': 'validate_me'}]}

        if data['platforms']:  # this might be empty, if so there's nothing useful to save
            d = os.path.join(self.data_dir, 'abilities', tactic)
            if not os.path.exists(d):
                os.makedirs(d)
            file_path = os.path.join(d, '%s.yml' % ability_id)
            with open(file_path, 'w') as f:
                f.write(yaml.dump([data]))
            return True

        return False

    async def _prereq_formater(self, prereq_test, prereq, prereq_type, exec_type, ability_command):
        """
        Format prereqs as a header test block for an ability
        :param prereq_test: Test to see if the ability is required
        :param prereq: Command to install prereq if required
        :param prereq_type: Which executor this prereq should target (psh, sh, cmd)
        :param exec_type: Which executor this ability should target (psh, sh, cmd)
        :param ability_command: Existing commands for this ability
        :return: Full formed, staged command
        """
        output = ""
        prereq = prereq.rstrip()
        if 'exit' not in prereq_test.lower() or prereq.startswith('echo "') or \
                (prereq.startswith('echo ') and ('Run' in prereq or 'Sorry,' in prereq)):
            if self.processing_debug:
                self.log.debug(f'Action ({prereq}) cannot be automated automatically.')
                if prereq.startswith('echo'):
                    self.log.debug(f'Try to satisfy: {prereq.split("echo")[1].split("; exit")[0]}')
                elif prereq.startswith('Write-Host'):
                    self.log.debug(f'Try to satisfy: {prereq.split("Write-Host ")[1]}')
            raise ExtractionError
        if prereq_type == 'sh':
            segments = prereq_test.split(';')
            if 'exit 1' in segments[1]:
                # check is "falsy"
                output += f"{segments[0]}; then {prereq}; fi;"
            else:
                # check is "truthy"
                output += f"{segments[0]}; then : ; else {prereq}; fi;"
        elif prereq_type == 'psh':
            if prereq_test.startswith('Try'):
                temp = f"{prereq_test.replace('exit 1', prereq)}"
                output += f"{temp.replace('exit 0', ' ; ')}"
            else:
                segments = prereq_test.split(')')
                test_outcomes = segments[1].split('}')
                if 'exit 1' in test_outcomes[0]:
                    # check is "falsy"
                    output += f"{segments[0]}) {{{prereq}}}"
                else:
                    # check is "truthy"
                    output += f"{segments[0]}) {{ ; }} else {{{prereq}}}"
        elif prereq_type == 'cmd':
            segments = prereq_test.split('(')
            test_outcomes = segments[1].split('ELSE')
            if 'exit 1' in test_outcomes[0]:
                # check is "falsy"
                output += f"{segments[0]} ({prereq})"
            else:
                # check is "truthy"
                output += f"{segments[0]} ( call ) ELSE ( {prereq} )"
        else:
            return ability_command
        if prereq_type == exec_type:
            output += '\n' + ability_command
        else:
            if prereq_type == "cmd" and exec_type == "psh":
                output += '\n' + ability_command
            elif prereq_type == "psh" and exec_type == "cmd":
                output = f'powershell -command "{output} \n {ability_command}"'
            else:
                self.log.warning(f'Unable to deduce a way to link a {prereq_type} prereq and a {exec_type} ability. '
                                 f'Defaulting to just the ability - this may cause the produced ability to behave '
                                 f'unexpectedly.')
                output = ability_command
        return output
