from plugins.training.app.base_flag import BaseFlag
from plugins.training.app.c_flag import Flag


class AttackBlue0(Flag):
    name = 'ATT&CK Quiz 1'
    challenge = 'This badge tests your knowledge of ATT&CK techniques. Look on the back of this card for ' \
                'instructions on how to complete the challenge. Each of the following challenges in this badge will ' \
                'follow the same process. Ensure the uploaded adversary layer is named exactly \'blue_quiz_1\'.\n\n' \
                'The adversary procedure is:\nwhoami'
    extra_info = 'Complete the challenge by determining the ONE ATT&CK technique that best matches the procedure on ' \
                 'the front of this card. Select this technique in the Compass plugin and give it a positive score. ' \
                 'Rename the layer as indicated on the front of this card, and then download the layer. Upload the ' \
                 'downloaded layer to the server by selecting \'Upload Adversary Layer\'. Use the help button on the ' \
                 'Compass plugin modal for reference.'

    async def verify(self, services):
        technique = 'T1033'  # System Owner User Discovery
        adv_name = 'blue_quiz_1'
        return await BaseFlag.verify_attack_flag(services, technique, adv_name)
