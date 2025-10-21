
import random
import string
import getpass

name = 'gohide'


async def check_dependencies(app_svc):
    return True


class Packer:
    def __init__(self, file_svc):
        self.file_svc = file_svc
        self.paths = ['mitre', 'caldera', 'sandcat', 'gocat']
        self.strings = ['github.com']

    async def pack(self, filename, contents):
        try:
            # Obfuscate "Go build ID" string
            id_extension = self.get_random_replacement('Go build ID: ')
            contents = contents.replace(b'Go build ID: "', b'"%s' % id_extension)

            # Replace folder names, adding the current user
            self.paths.append(getpass.getuser())
            for path in self.paths:
                replace = self.get_random_replacement(path)
                contents = contents.replace(b'/%s/' % path.encode('utf-8'), b'/%s/' % replace)

            # Replace certain strings
            for old_string in self.strings:
                replace = self.get_random_replacement(old_string)
                contents = contents.replace(old_string.encode('utf-8'), replace)

            self.file_svc.log.debug('packed %s with %s packer' % (filename, name))
            return filename, contents
        except Exception as e:
            raise Exception('Error encountered packing %s with %s packer: %s' % (filename, name, e.message))

    @staticmethod
    def get_random_replacement(old_string):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=len(old_string))).encode('utf-8')
