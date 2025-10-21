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
        link.command = link.command.replace('=', '')
        return super().run(link)

    def sh(self, link, **kwargs):
        return 'eval "$(echo %s=== | base64 --decode 2>/dev/null)"' % link.command

    def psh(self, link, **kwargs):
        return '$string="%s";' % link.command +\
            'while($string.Length %4 -ne 0) {$string="$string="};' +\
            'Invoke-Expression $ExecutionContext.InvokeCommand.ExpandString(' +\
            '[System.Text.Encoding]::UTF8.GetString([convert]::FromBase64String($string)))'
