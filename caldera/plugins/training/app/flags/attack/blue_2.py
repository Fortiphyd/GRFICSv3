from plugins.training.app.base_flag import BaseFlag
from plugins.training.app.c_flag import Flag


class AttackBlue2(Flag):
    name = 'ATT&CK Quiz 3'
    challenge = 'Refer to \'ATT&CK Quiz 1\' for instructions. Name the uploaded adversary layer exactly ' \
                '\'blue_quiz_3\'. Ensure that you\'re starting from a fresh layer on the Compass plugin.\n\n' \
                'The adversary procedure is:\nGet-Clipboard -raw'
    extra_info = ''

    async def verify(self, services):
        technique = 'T1115'  # Clipboard Data
        adv_name = 'blue_quiz_3'
        return await BaseFlag.verify_attack_flag(services, technique, adv_name)
