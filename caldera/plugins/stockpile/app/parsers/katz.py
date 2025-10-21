import logging
import re
from collections import defaultdict

from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
from app.utility.base_parser import BaseParser


class MimikatzBlock(object):
    def __init__(self):
        self.session = ''
        self.username = ''
        self.domain = ''
        self.logon_server = ''
        self.logon_time = ''
        self.sid = ''
        self.providers = defaultdict(list)


class Parser(BaseParser):

    def __init__(self, parser_info):
        self.mappers = parser_info['mappers']
        self.used_facts = parser_info['used_facts']
        self.providers = ['wdigest', 'credman', 'msv', 'kerberos', 'ssp']
        self.log = logging.getLogger('parsing_svc')
        self.hash_check = r'([0-9a-fA-F][0-9a-fA-F] ){3}'
        self.target_mapping = {'password': 'Password',
                               'ntlm': 'NTLM',
                               'sha1': 'SHA1',
                               '_default': 'Password'
                               }

    def parse_katz(self, output):
        """
        Parses mimikatz output with the logonpasswords command and returns a list of dicts of the credentials.
        Args:
            output: stdout of "mimikatz.exe privilege::debug sekurlsa::logonpasswords exit"
        Returns:
            A list of Mimikatzsession objects
        """
        sessions = output.split('Authentication Id')  # split sessions using "Authentication Id" as separator
        creds = []
        for session in sessions:
            logon_session = MimikatzBlock()
            provider = {}
            provider_name = ''
            in_header = True
            provider_state = False
            for line in session.splitlines():
                line = line.strip()
                if in_header:
                    in_header = self._parse_header(line, logon_session)
                    if in_header:
                        continue  # avoid excess parsing work
                provider_state, provider_name = self._process_provider(line, provider, provider_name, logon_session)
                if provider_state:
                    provider_state = False
                    provider = {}
            self._provider_extend(provider, provider_name, logon_session)  # save the current ssp if necessary
            if logon_session.providers:  # save this session
                creds.append(logon_session)
        return creds

    def parse(self, blob):
        relationships = []
        try:
            logon_sessions = self.parse_katz(blob)
            valid_sessions = [logon_session for logon_session in logon_sessions
                              if logon_session.logon_server != '(null)' or 'credman' in logon_session.providers]
            for logon_session in valid_sessions:
                provider_names = [provider for provider in logon_session.providers if provider in self.providers]
                for provider_name in provider_names:
                    for provider in logon_session.providers[provider_name]:
                        if not re.match(self.hash_check, provider.get('Password', '')):
                            if provider_name == 'credman':
                                username = provider['Username'].lower()
                            else:
                                username = '{}\\{}'.format(provider['Domain'], provider['Username']).lower()
                            for mp in self.mappers:
                                target_key = self.target_mapping.get(mp.target.split('.')[-1],
                                                                     self.target_mapping['_default'])
                                if target_key in provider and not (target_key == 'Password'
                                                                   and provider[target_key] == '(null)'):
                                    relationships.append(
                                        Relationship(source=Fact(mp.source, username),
                                                     edge=mp.edge,
                                                     target=Fact(mp.target, provider[target_key]))
                                    )
        except Exception as error:
            self.log.warning('Mimikatz parser encountered an error - {}. Continuing...'.format(error))
        return relationships

    """    PRIVATE FUNCTION     """

    @staticmethod
    def _parse_header(line, logon_session):
        if line.startswith('msv'):
            return False
        session = re.match(r'^\s*Session\s*:\s*([^\r\n]*)', line)
        if session:
            logon_session.session = session.group(1)
        username = re.match(r'^\s*User Name\s*:\s*([^\r\n]*)', line)
        if username:
            logon_session.username = username.group(1)
        domain = re.match(r'^\s*Domain\s*:\s*([^\r\n]*)', line)
        if domain:
            logon_session.domain = domain.group(1)
        logon_server = re.match(r'^\s*Logon Server\s*:\s*([^\r\n]*)', line)
        if logon_server:
            logon_session.logon_server = logon_server.group(1)
        logon_time = re.match(r'^\s*Logon Time\s*:\s*([^\r\n]*)', line)
        if logon_time:
            logon_session.logon_time = logon_time.group(1)
        sid = re.match(r'^\s*SID\s*:\s*([^\r\n]*)', line)
        if sid:
            logon_session.sid = sid.group(1)
        return True

    def _process_provider(self, line, provider, provider_name, logon_session):
        if line.startswith('['):
            self._provider_extend(provider, provider_name, logon_session)  # indicates the start of a new account
            return True, provider_name  # reset the provider
        elif line.startswith('*'):
            m = re.match(r'\s*\* (.*?)\s*: (.*)', line)
            if m:
                provider[m.group(1)] = m.group(2)
        elif line:
            match_group = re.match(r'([a-z]+) :', line)  # parse out the new session name
            if match_group:  # this is the start of a new ssp
                self._provider_extend(provider, provider_name, logon_session)  # save the current ssp if necessary
                return True, match_group.group(1)  # reset the provider
        return False, provider_name

    def _provider_extend(self, provider, provider_name, logon_session):
        if 'Username' in provider and provider['Username'] != '(null)' and \
                any([cred for cred in self.target_mapping.values() if cred in provider]):
            logon_session.providers[provider_name].append(provider)
