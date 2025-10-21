import random
import string
import binascii

from base64 import b64encode

from app.utility.base_obfuscator import BaseObfuscator


class Obfuscation(BaseObfuscator):

    @property
    def supported_platforms(self):
        return dict(
            windows=['psh'],
            darwin=['sh'],
            linux=['sh']
        )

    def run(self, link, **kwargs):
        cmd, extra = self._jumble_command(link.command)
        link.command = cmd
        return super().run(link, extra=extra)

    @staticmethod
    def sh(link, **kwargs):
        extra_chars = kwargs.get('extra')
        return 'eval "$(echo %s | rev | cut -c%s- | rev | base64 --decode)"' % (link.command, extra_chars)

    def psh(self, link, **kwargs):
        extra_chars = kwargs.get('extra')
        try:
            recoded = b64encode(self.decode_bytes(link.command).encode('UTF-16LE'))
        except binascii.Error:  # Resolve issue where we can't decode our own mangled command internally
            recoded = b64encode(self.decode_bytes(link.command[:-extra_chars]).encode('UTF-16LE'))
        return 'powershell -Enc %s' % recoded.decode('utf-8')

    """ PRIVATE """

    def _jumble_command(self, s):
        extra = 0
        while self.is_base64(s):
            s = s + self._random_char()
            extra += 1
        return s, extra

    @staticmethod
    def _random_char():
        return random.choice(string.ascii_letters + string.digits)
