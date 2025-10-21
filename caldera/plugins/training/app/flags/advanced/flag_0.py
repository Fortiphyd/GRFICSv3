import re
from urllib.parse import urlparse

from plugins.training.app.c_flag import Flag


class AdvancedFlag0(Flag):
    name = 'Update configs'
    challenge = 'Update the app.contact.http configuration property to a URL with an externally-facing IPv4 address ' \
                '(not 0.0.0.0). Examples may include http://10.10.10.10:8888, https://192.168.138.10:443.'
    extra_info = (
        'C2 servers need to be made accessible to agents, either through agent-network-facing interfaces or proxies. '
        'Changing the app.contact.http configuration value sets the URL that agents will connect to with the HTTP  '
        'contact.'
    )
    ipv4_regex = r'^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])\.){3}' \
                 r'(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])$'

    async def verify(self, services):
        http_contact = services.get('app_svc').get_config('app.contact.http')
        return http_contact and AdvancedFlag0.valid_external_http_contact(http_contact)

    @staticmethod
    def valid_external_http_contact(http_str):
        url = urlparse(http_str)
        if url.scheme.lower() in ('http', 'https'):
            try:
                if url.port:
                    # Will throw ValueError if not within valid port range.
                    pass
            except ValueError:
                return False
            return bool(re.match(AdvancedFlag0.ipv4_regex, url.hostname)) and AdvancedFlag0.external_facing_ip(url.hostname)
        return False

    @staticmethod
    def external_facing_ip(ip_addr):
        return not (ip_addr.startswith('127.') or ip_addr == '0.0.0.0')
