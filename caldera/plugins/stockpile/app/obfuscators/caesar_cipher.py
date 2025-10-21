from random import randint

from app.utility.base_obfuscator import BaseObfuscator


class Obfuscation(BaseObfuscator):

    @property
    def supported_platforms(self):
        return dict(
            windows=['psh'],
            darwin=['sh'],
            linux=['sh']
        )

    """ EXECUTORS """

    def psh(self, link):
        decrypted = self.decode_bytes(link.command)
        encrypted, shift = self._apply_cipher(decrypted)
        return '$encrypted = "' + encrypted + '"; $cmd = "''"; $encrypted = $encrypted.toCharArray(); ' \
               'foreach ($letter in $encrypted) {$letter = [char](([int][char]$letter) - ' + str(shift) + '); ' \
               '$cmd += $letter;} write-output $cmd;'

    def sh(self, link):
        decrypted = self.decode_bytes(link.command)
        encrypted, shift = self._apply_cipher(decrypted)
        return 'cmd=""; chr (){ [ "$1" -lt 256 ] || return 1; printf "\\\\$(printf \'%03o\' "$1")";};' \
               'ord (){ LC_CTYPE=C printf \'%d\' "\'$1";return $LC_CTYPE; }; ' \
               'st="' + encrypted + '"; for i in $(seq 1 ${#st}); do x=$(ord "${st:i-1:1}"); ' \
               'if [[ "$x" =~ [^a-zA-Z] ]]; then x=$((x+ ' + str(-shift) + ')); fi; ' \
               'cmd+="$(echo $(chr $x))";done;echo $cmd;'

    """ PRIVATE """

    @staticmethod
    def _apply_cipher(s, bounds=26):
        """
        Encode a command with a simple caesar cipher
        :param s: the string to encode
        :param bounds: the number of unicode code points to shift
        :return: a tuple containing the encoded command and the shift value
        """
        shift = randint(1, bounds)
        return ''.join([chr(ord(c) + shift) if c.isalpha() else c for c in s]), shift
