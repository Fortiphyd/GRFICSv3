import pathlib
import shutil

# Directory in plugin to pull documentation from
PLUGIN_DOCS_DIR = 'docs'


def import_plugin_docs(caldera_root_dir, sphinx_root_dir):
    """Copy docs from plugins to sphinx-docs/plugins/{plugin_name}/

    Deletes the existing contents of sphinx-docs/plugins to ensure
    all documentation is reset on Caldera startup.

    :param caldera_root_dir: Path to Caldera base directory
    :param sphinx_root_dir: Path to sphinx directory
    :return: List of copied Markdown and reStructuredText files
    """

    sphinx_plugins_dir = pathlib.Path(sphinx_root_dir).resolve() / 'plugins'
    caldera_plugins_dir = pathlib.Path(caldera_root_dir).resolve() / 'plugins'

    # Clear sphinx plugin documentation directory
    for f in sphinx_plugins_dir.iterdir():
        if not f.is_dir():
            continue
        shutil.rmtree(f, ignore_errors=True)

    for f in caldera_plugins_dir.iterdir():
        if not f.is_dir():
            continue

        plugin_docs_dir = f / PLUGIN_DOCS_DIR
        if not plugin_docs_dir.is_dir():
            continue

        sphinx_plugin_dir = sphinx_plugins_dir / f.name
        shutil.copytree(plugin_docs_dir, sphinx_plugin_dir, dirs_exist_ok=True)
