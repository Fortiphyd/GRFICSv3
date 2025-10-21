import os

from app.utility.base_world import BaseWorld
from plugins.atomic.app.atomic_svc import AtomicService
from plugins.atomic.app.atomic_gui import AtomicGUI

name = 'Atomic'
description = 'The collection of abilities in the Red Canary Atomic test project'
address = '/plugin/atomic/gui'
access = BaseWorld.Access.RED
data_dir = os.path.join('plugins', 'atomic', 'data')


async def enable(services):
    atomic_gui = AtomicGUI(services, name, description)
    app = services.get('app_svc').application

    # we only ingest data once, and save new abilities in the data/ folder of the plugin
    if "abilities" not in os.listdir(data_dir):
        atomic_svc = AtomicService()
        await atomic_svc.clone_atomic_red_team_repo()
        await atomic_svc.populate_data_directory()
