import re

from app.utility.base_world import BaseWorld
from plugins.sandcat.app.utility.base_extension import Extension, ConfigFileException

GOCAT_PLUGIN = 'gocat'
PACKAGE_NAME = 'contact'
FILE_NAME = 'ftp.go'
FTP_CONFIG_VARIABLES = ['app.contact.ftp.user', 'app.contact.ftp.pword', 'app.contact.ftp.server.dir']
TEXT_TO_REPLACE = [r'{FTP_C2_USER}', r'{FTP_C2_PASSWORD}', r'{FTP_C2_DIRECTORY}']


def load():
    return FTP()


class FTP(Extension):
    def __init__(self):
        super().__init__([(FILE_NAME, PACKAGE_NAME)],
                         dependencies=['github.com/jlaffaye/ftp'],
                         file_hooks={FILE_NAME: self.hook_set_custom_values})

    async def hook_set_custom_values(self, original_data):
        """Will replace the ftp variables with the variables in the C2 configuration."""
        for var, text in zip(FTP_CONFIG_VARIABLES, TEXT_TO_REPLACE):
            replace_name = BaseWorld.get_config(prop=var)
            if replace_name:
                data = re.sub(text, replace_name, original_data, count=1)
            else:
                raise ConfigFileException('No variable specified in C2 configuration file under ' + var)
            original_data = data

        return original_data
