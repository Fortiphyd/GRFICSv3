import re

from plugins.sandcat.app.utility.base_extension import Extension
from app.utility.base_world import BaseWorld

GOCAT_PLUGIN = 'gocat'
PACKAGE_NAME = 'contact'
FILE_NAME = 'slack.go'
CHANNEL_CONFIG = 'app.contact.slack.channel_id'
TEXT_TO_REPLACE = r'{SLACK_C2_CHANNEL_ID}'


def load():
    return Slack()


class Slack(Extension):

    def __init__(self):
        super().__init__([(FILE_NAME, PACKAGE_NAME), ('util.go', PACKAGE_NAME)],
                         dependencies=[],
                         file_hooks={FILE_NAME: self.hook_set_custom_channel})

    async def hook_set_custom_channel(self, original_data):
        """Will replace the C2 channel variable with the Slack channel in the C2 configuration."""
        channel_name = BaseWorld.get_config(prop=CHANNEL_CONFIG)
        if channel_name:
            return re.sub(TEXT_TO_REPLACE, channel_name, original_data, count=1)
        else:
            raise Exception('No Slack channel ID specified in C2 configuration file under app.contact.slack.channel_id')
