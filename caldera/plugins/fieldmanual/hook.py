import asyncio
import logging
import pathlib

import concurrent.futures
from aiohttp import web

from app.utility.base_world import BaseWorld


name = 'fieldmanual'
description = 'Holds and serves Caldera documentation'
address = f'/plugin/{name}/gui'
access = BaseWorld.Access.APP

plugin_root = pathlib.Path('plugins') / name
plugin_root = plugin_root.absolute()
sphinx_docs_root = plugin_root / 'sphinx-docs'
sphinx_build_dir = sphinx_docs_root / '_build' 
html_docs_root = sphinx_build_dir / 'html'

logger = logging.getLogger('fieldmanual')


async def landing(_):
    return web.FileResponse(plugin_root / 'static' / 'opener.html')


def _run_sphinx_build():
    import sys
    import io

    import sphinx.cmd.build

    out = io.StringIO()
    err = io.StringIO()
    sys.stdout = out
    sys.stderr = err

    argv = ['-M', 'html', str(sphinx_docs_root), str(sphinx_build_dir)]

    sphinx.cmd.build.main(argv)

    out.seek(0)
    err.seek(0)
    return out.read(), err.read()


async def build_docs(loop=None):
    loop = loop or asyncio.get_event_loop()
    with concurrent.futures.ProcessPoolExecutor() as pool:
        try:
            out, err = await loop.run_in_executor(pool, _run_sphinx_build)
        except Exception:
            logger.warning('Encountered problem while building documentation.', exc_info=True)

        if 'build succeeded' in out and err:
            logger.info(f'Docs built successfully with the following warnings\n{err}')
        elif 'build succeeded' in out:
            logger.info('Docs built successfully.')
        else:
            logger.warning(f'Unable to build docs:\n{err}')


async def enable(services, loop=None):
    loop = loop if loop else asyncio.get_event_loop()
    html_docs_root.mkdir(parents=True, exist_ok=True)
    loop.create_task(build_docs(loop=loop))
    app_svc = services.get('app_svc')
    app_svc.application.router.add_route('GET', address, landing)
    app_svc.application.router.add_static('/docs/', str(html_docs_root.resolve()), append_version=True)
