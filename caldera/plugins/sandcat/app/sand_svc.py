import base64
import json
import os
import pathlib
import random
import string
from collections import defaultdict
from importlib import import_module
from shutil import which

from app.utility.base_service import BaseService

default_flag_params = ('server', 'group', 'listenP2P', 'c2', 'includeProxyPeers')
gocat_variants = dict(
    basic=set(),
    red=set(['gist', 'shared', 'shells', 'shellcode'])
)
default_gocat_variant = 'basic'


class SandService(BaseService):

    def __init__(self, services):
        self.file_svc = services.get('file_svc')
        self.data_svc = services.get('data_svc')
        self.contact_svc = services.get('contact_svc')
        self.app_svc = services.get('app_svc')
        self.log = self.create_logger('sand_svc')
        self.sandcat_dir = os.path.relpath(os.path.join('plugins', 'sandcat'))
        self.sandcat_extensions = dict()

    async def dynamically_compile_executable(self, headers):
        # HTTP headers will specify the file name, platform, and comma-separated list of extension modules to include.
        name, platform = headers.get('file'), headers.get('platform')
        extension_names = await self._obtain_extensions_from_headers(headers)
        if which('go') is not None:
            await self._compile_new_agent(platform=platform,
                                          headers=headers,
                                          compile_target_name=name,
                                          cflags='CGO_ENABLED=0',
                                          output_name=name,
                                          extension_names=extension_names,
                                          compile_target_dir='gocat')
        return await self.app_svc.retrieve_compiled_file(name, platform, location='payloads')

    async def dynamically_compile_library(self, headers):
        # HTTP headers will specify the file name, platform, and comma-separated list of extension modules to include.
        name, platform = headers.get('file'), headers.get('platform')
        extension_names = await self._obtain_extensions_from_headers(headers)
        extension_names.add('shared')  # Make sure we include shared extension since we're compiling shared.go.
        compile_options = dict(
            windows=dict(
                CC='x86_64-w64-mingw32-gcc',
                cflags='CGO_ENABLED=1',
                extldflags='-extldflags "-Wl,--nxcompat -Wl,--dynamicbase -Wl,--high-entropy-va"',
            ),
            linux=dict(
                cflags='CGO_ENABLED=1'
            )
        )
        if which('go') is not None:
            if platform in compile_options.keys():
                if 'CC' in compile_options[platform].keys():
                    if which(compile_options[platform]['CC']) is not None:
                        compile_options[platform]['cflags'] += ' CC=%s' % compile_options[platform]['CC']
                    else:
                        raise Exception('Missing dependency for cross compilation: %s' % compile_options[platform]['CC'])
                    # key is deleted from compile_options to use dict as kwargs for called function.
                    del compile_options[platform]['CC']
                await self._compile_new_agent(platform=platform,
                                              headers=headers,
                                              compile_target_name='shared.go',
                                              output_name=name,
                                              buildmode='--buildmode=c-shared',
                                              **compile_options[platform],
                                              flag_params=default_flag_params,
                                              extension_names=extension_names,
                                              compile_target_dir='gocat/shared')
        return await self.app_svc.retrieve_compiled_file(name, platform, location='payloads')

    async def load_sandcat_extension_modules(self):
        """
        Recursively searches the app/extensions folder for valid extension modules.
        """
        gocat_dir = os.path.join(self.sandcat_dir, 'gocat')
        for root, dirs, files in os.walk(os.path.join(self.sandcat_dir, 'app', 'extensions')):
            files = [f for f in files if not f[0] == '.' and not f[0] == "_"]
            dirs[:] = [d for d in dirs if not d[0] == '.' and not d[0] == "_"]
            for file in files:
                module = await self._load_extension_module(root, file)
                if module and (module.check_go_dependencies(gocat_dir) or module.install_dependencies()):
                    module_name = file.split('.')[0]
                    self.sandcat_extensions[module_name] = module
                    self.log.debug('Loaded gocat extension module: %s' % module_name)

    """ PRIVATE """

    @staticmethod
    def _generate_key(size=30):
        return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(size))

    async def _get_c2_config(self, c2_type):
        for c2 in self.contact_svc.contacts:
            if c2_type == c2.name:
                return 'c2Key', c2.retrieve_config()
        return '', ''

    async def _compile_new_agent(self, platform, headers, compile_target_name, output_name, buildmode='',
                                 extldflags='', cflags='', flag_params=default_flag_params, extension_names=None,
                                 compile_target_dir=''):
        """
        Compile sandcat agent using specified parameters. Will also include any requested extension modules.
        If a gocat variant is specified along with additional extensions, the extensions will be added to the
        base extensions for the variant.
        """
        architecture = headers.get('architecture', 'amd64')
        ldflags = ['-s', '-w', '-X main.key=%s' % (self._generate_key(),)]
        for param in flag_params:
            if param in headers:
                value = headers[param]
                if param == 'c2':
                    ldflags.append('-X main.%s=%s' % (await self._get_c2_config(value)))
                elif param == 'includeProxyPeers':
                    self.log.debug('Available peer-to-peer proxy receivers requested.')
                    encoded_info, xor_key = await self._get_encoded_proxy_peer_info(value)
                    if encoded_info and xor_key:
                        ldflags.append('-X github.com/mitre/gocat/proxy.%s=%s' % ('encodedReceivers', encoded_info))
                        ldflags.append('-X github.com/mitre/gocat/proxy.%s=%s' % ('receiverKey', xor_key))
                else:
                    sanitized = self.file_svc.sanitize_ldflag_value(param, value)
                    ldflags.append('-X main.%s=%s' % (param, sanitized))
        ldflags.append(extldflags)

        output = str(pathlib.Path('plugins/sandcat/payloads').resolve() / ('%s-%s' % (output_name, platform)))

        # Load extensions and compile. Extensions need to be loaded before searching for target file.
        installed_extensions = await self._install_gocat_extensions(extension_names)
        _, file_path = await self.file_svc.find_file_path(compile_target_name, location=compile_target_dir)
        self.file_svc.log.debug('Dynamically compiling %s' % compile_target_name)
        build_path, build_file = os.path.split(file_path)
        await self.file_svc.compile_go(platform, output, build_file, arch=architecture, buildmode=buildmode,
                                       ldflags=' '.join(ldflags), cflags=cflags, build_dir=build_path)

        # Remove extension files.
        await self._uninstall_gocat_extensions(installed_extensions)

    async def _get_available_proxy_peer_info(self, specified_protocols, exclude=False):
        """Returns JSON-marshalled dict that maps proxy protocol (string) to a de-duped list of receiver addresses
        (string) for trusted agents who are running proxy receivers. specified_protocols must be an iterable
        of proxy protocol strings to include/exclude. Setting it to empty with 'exclude' set to False will
        include all available proxy protocols. Setting exclude to True will exclude any protocol included in
        specified_protocols
        """
        deduped_receivers = defaultdict(list)
        for agent in await self.data_svc.locate('agents', match=dict(trusted=True)):
            for protocol, addressList in agent.proxy_receivers.items():
                if not specified_protocols \
                        or (not exclude and protocol in specified_protocols) \
                        or (exclude and protocol not in specified_protocols):
                    deduped_receivers[protocol] += addressList
        for protocol in deduped_receivers:
            deduped_receivers[protocol] = list(set(deduped_receivers[protocol]))
        self.log.debug('Found peer-to-peer proxy receivers for protocols: %s' % (', '.join(deduped_receivers.keys())))
        return json.dumps(deduped_receivers)

    async def _get_encoded_proxy_peer_info(self, filter_string):
        """XORs JSON-dumped available proxy receiver information with the given key string
        and returns the base64-encoded output along with the XOR key string.
        filter_string should be one of these formats:
            'all' : include all available proxy protocols
            'comma,separated,list,to,include' : only include these protocols
            '!comma,separated,list,to,exclude' : exclude these protocols
        """
        exclude = False
        specified_protocols = set()
        if filter_string and filter_string.lower() != 'all':
            if filter_string.startswith('!'):
                filter_string = filter_string[1:]
                exclude = True
            specified_protocols = set(filter_string.split(','))
        receiver_info_json = await self._get_available_proxy_peer_info(specified_protocols, exclude)
        if receiver_info_json:
            result = []
            key = self._generate_key()
            key_length = len(key)
            for index in range(0, len(receiver_info_json)):
                result.append(ord(receiver_info_json[index]) ^ ord(key[index % key_length]))
            return base64.b64encode(bytes(result)).decode('ascii'), key
        return '', ''

    async def _install_gocat_extensions(self, extension_names):
        """
        Given a list of extension names, copies the required files for each extension from the gocat-extensions
        subdirectory into the gocat subdirectory.
        """
        if which('go') is not None and extension_names:
            self.log.debug('Installing gocat extension modules: %s' % ', '.join(extension_names))
            return [name for name in extension_names if await self._attempt_module_copy(name=name)]
        return []

    async def _uninstall_gocat_extensions(self, extension_names):
        """
        Given a list of extension names, removes the required files for each extension from the gocat
        subdirectory.
        """
        if which('go') is not None and extension_names:
            self.log.debug('Cleaning up files for gocat extension modules %s' % ', '.join(extension_names))
            for extension_name in extension_names:
                self.sandcat_extensions[extension_name].remove_module_files(base_dir=self.sandcat_dir)

    async def _load_extension_module(self, root, file):
        """
        Given the file path and file name for the extension module file, returns the extension
        module object.
        """
        module = os.path.join(root, file.split('.')[0]).replace(os.path.sep, '.')
        try:
            # Module's "load" method will return the extension module object.
            return getattr(import_module(module), 'load')()
        except Exception as e:
            self.log.error('Error loading extension=%s, %s' % (module, e))

    async def _attempt_module_copy(self, name):
        """
        Attempts to copy the module files. Returns True upon success, False otherwise.
        """
        module = self.sandcat_extensions.get(name)
        if module:
            try:
                return await module.copy_module_files(base_dir=self.sandcat_dir)
            except Exception as e:
                self.log.error('Error copying files for module %s: %s', name, e)
        else:
            self.log.error('Module %s not found' % name)
        return False

    async def _obtain_extensions_from_headers(self, headers):
        """
        Given the headers dict, extracts the requested extensions and gocat variant and returns a combined set of
        required extensions.
        """
        requested_extensions = [ext_name for ext_name in headers.get('gocat-extensions', '').split(',') if ext_name]
        agent_variant = headers.get('gocat-variant', default_gocat_variant)
        variant_extensions = gocat_variants.get(agent_variant, set())
        self.log.debug('Using gocat variant: %s' % agent_variant)
        return variant_extensions.union(set(requested_extensions))
